"""
test_pipeline.py — pytest suite for the patch-clamp pipeline

Covers each stage in isolation plus the full end-to-end run, using synthetic
data so no real recordings are required. Run with:

    pytest -v
"""

import numpy as np
import h5py
import pytest

from load_data import load_data_nA, save_loaded_data, FSAMPLE
from baseline_filter import tds, baseline_correct, lowpass_filter, process as baseline_process
from chunk_data import chunk_data, save_chunks_hdf5
from pipeline import run_pipeline
from make_synthetic_data import make_synthetic_recording


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def recording(tmp_path):
    """A single-file synthetic recording in a temp directory."""
    return make_synthetic_recording(str(tmp_path / "rec"), channel_num=1,
                                     duration_s=1.0, n_files=1, seed=1)


@pytest.fixture
def recording_multi(tmp_path):
    """A multi-file synthetic recording (tests the cell-array code path)."""
    return make_synthetic_recording(str(tmp_path / "rec_multi"), channel_num=2,
                                    duration_s=1.0, n_files=3, seed=2)


# ── Stage 2 unit tests: tds / baseline / filter ──────────────────────────────

def test_tds_constant_input_returns_constant():
    # A perfectly flat signal has itself as its baseline.
    data = np.full(1000, 3.0)
    bs = tds(1e-3, data - data.mean())  # mean-subtracted, as the pipeline calls it
    assert np.allclose(bs, 0.0, atol=1e-6)


def test_tds_length_preserved():
    data = np.random.default_rng(0).standard_normal(500)
    bs = tds(1e-2, data)
    assert bs.shape == data.shape


def test_baseline_removes_slow_drift():
    n = 25_000
    t = np.arange(n) / FSAMPLE
    drift = 2.0 * np.sin(2 * np.pi * 0.5 * t)   # slow component
    signal = np.zeros(n)
    signal[1000:1500] = 1.0                      # fast event
    data = signal + drift

    corrected, baseline = baseline_correct(data, Rsqrd=1e-5)
    # Baseline should track the drift, so the corrected mean is near zero
    # and far smaller drift remains than in the input.
    assert abs(corrected.mean()) < abs(data.mean()) + 1e-9
    assert np.std(corrected - signal) < np.std(drift)


def test_lowpass_attenuates_high_frequency():
    n = 25_000
    t = np.arange(n) / FSAMPLE
    low = np.sin(2 * np.pi * 50 * t)      # passband
    high = np.sin(2 * np.pi * 8000 * t)   # well above 1 kHz cutoff
    filtered = lowpass_filter(low + high, fcutoff=1000, fsample=FSAMPLE)
    # High-frequency component should be strongly attenuated.
    residual_high = filtered - low
    assert np.std(residual_high) < 0.2


# ── Stage 3 unit tests: chunking ─────────────────────────────────────────────

def test_chunk_data_equal_lengths():
    data = np.arange(100)
    chunks = chunk_data(data, 5)
    assert len(chunks) == 5
    assert all(len(c) == 20 for c in chunks)
    assert np.array_equal(np.concatenate(chunks), data)


def test_chunk_data_truncates_remainder():
    data = np.arange(103)          # not divisible by 5
    chunks = chunk_data(data, 5)
    assert len(chunks) == 5
    assert all(len(c) == 20 for c in chunks)   # 3 trailing samples dropped


# ── Stage 1 tests: loading + conversion ──────────────────────────────────────

def test_load_single_file(recording):
    result = load_data_nA(recording["channel_num"], recording["out_dir"])
    assert isinstance(result["data_nA"], np.ndarray)   # collapsed, not a list
    assert result["data_nA"].shape[0] == recording["n_samples"]
    assert result["fsample"] == FSAMPLE
    assert np.all(np.isfinite(result["data_nA"]))


def test_load_roundtrip_recovers_event(recording):
    # After baseline correction the square event should be recoverable.
    result = load_data_nA(recording["channel_num"], recording["out_dir"])
    corrected, _ = baseline_correct(result["data_nA"], Rsqrd=1e-5)
    clean = recording["clean_signals"][0]
    # Corrected signal should correlate with the injected event pattern.
    corr = np.corrcoef(corrected, clean)[0, 1]
    assert corr > 0.5


def test_load_multi_file_returns_list(recording_multi):
    result = load_data_nA(recording_multi["channel_num"], recording_multi["out_dir"])
    assert isinstance(result["data_nA"], list)
    assert len(result["data_nA"]) == recording_multi["n_files"]


def test_save_loaded_data_npz(recording, tmp_path):
    result = load_data_nA(recording["channel_num"], recording["out_dir"])
    out = tmp_path / "raw.npz"
    save_loaded_data(result, str(out))
    loaded = np.load(str(out))
    assert int(loaded["n_segments"]) == 1
    assert np.array_equal(loaded["data_nA"], result["data_nA"])


# ── End-to-end test ──────────────────────────────────────────────────────────

def test_full_pipeline(recording, tmp_path):
    artefacts = run_pipeline(
        channel_num=recording["channel_num"],
        data_dir=recording["out_dir"],
        Rsqrd=1e-5,
        fcutoff_hz=1000,
        bias_str="0mV",
        num_chunks=5,
        out_dir=str(tmp_path / "out"),
    )

    # All four artefacts should exist.
    for path in artefacts.values():
        assert __import__("os").path.exists(path)

    # The HDF5 final product should be well formed.
    with h5py.File(artefacts["hdf5"], "r") as hf:
        assert hf["metadata"].attrs["num_chunks"] == 5
        assert hf["metadata"].attrs["bias_str"] == "0mV"
        assert hf["metadata"].attrs["fsample"] == FSAMPLE
        chunk_names = list(hf["chunks"].keys())
        assert len(chunk_names) == 5
        for name in chunk_names:
            assert hf["chunks"][name].shape == hf["time"][name].shape
            assert np.all(np.isfinite(hf["chunks"][name][:]))


def test_full_pipeline_multi_file(recording_multi, tmp_path):
    # The multi-file (segmented) path should also run end-to-end.
    artefacts = run_pipeline(
        channel_num=recording_multi["channel_num"],
        data_dir=recording_multi["out_dir"],
        Rsqrd=1e-5,
        fcutoff_hz=1000,
        bias_str="20mV",
        num_chunks=3,
        out_dir=str(tmp_path / "out_multi"),
    )
    with h5py.File(artefacts["hdf5"], "r") as hf:
        assert len(list(hf["chunks"].keys())) == 3
