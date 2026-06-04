"""
baseline_filter.py — Python port of tds.m + SAVE_FULL_baseline_corrected_filtered_data.m

Baseline-corrects patch-clamp data with the tridiagonal smoother (TDS) from
John Pearson's automated maximum-likelihood paper, then applies a 4th-order
zero-phase Butterworth low-pass filter.

Intermediate outputs are saved as .npz files.
"""

import numpy as np
from pathlib import Path
from scipy.signal import butter, filtfilt


def tds(Rsqrd: float, data: np.ndarray) -> np.ndarray:
    """
    Tridiagonal smoother baseline estimator (port of tds.m).

    Solves the banded linear system that minimises a roughness penalty
    weighted by `Rsqrd`, returning the smooth baseline `bs`.

    Parameters
    ----------
    Rsqrd : float
        Noise-to-signal ratio guess (controls smoothness of baseline).
    data  : np.ndarray
        1-D signal array (mean should be subtracted before calling, as in MATLAB).

    Returns
    -------
    bs : np.ndarray
        Estimated baseline, same length as `data`.
    """
    data = data.copy().astype(np.float64)
    n = len(data)

    main_d = (2.0 + Rsqrd) * np.ones(n)
    main_d[0]  = Rsqrd + 1.0
    main_d[-1] = Rsqrd + 1.0

    low_d   = -np.ones(n - 1)
    upper_d = -np.ones(n - 1)

    # Forward sweep
    upper_d[0] = upper_d[0] / main_d[0]
    data[0]    = data[0]    / main_d[0]

    for rk in range(1, n - 1):
        denom      = main_d[rk] - low_d[rk - 1] * upper_d[rk - 1]
        upper_d[rk] = upper_d[rk] / denom

    for rk in range(1, n):
        denom   = main_d[rk] - low_d[rk - 1] * upper_d[rk - 1]
        data[rk] = (data[rk] - low_d[rk - 1] * data[rk - 1]) / denom

    # Reverse sweep
    bs = np.zeros(n)
    bs[-1] = data[-1]
    for rk in range(1, n):
        rrk      = n - 1 - rk
        bs[rrk]  = data[rrk] - upper_d[rrk] * bs[rrk + 1]

    return bs


def baseline_correct(data: np.ndarray, Rsqrd: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (baseline_corrected_data, baseline) for a 1-D signal."""
    bs = tds(Rsqrd, Rsqrd * (data - data.mean()))
    return data - bs, bs


def lowpass_filter(data: np.ndarray, fcutoff: float, fsample: float = 25_000.0,
                   order: int = 4) -> np.ndarray:
    """Zero-phase Butterworth low-pass filter (port of filtfilt in MATLAB)."""
    b, a = butter(order, fcutoff / (fsample / 2.0), btype="low")
    return filtfilt(b, a, data)


def process(
    raw_npz_path: str,
    Rsqrd: float,
    fcutoff_hz: float,
    out_baseline_path: str | None = None,
    out_filtered_path: str | None = None,
) -> dict:
    """
    Load raw data from a .npz produced by load_data.py, baseline-correct,
    filter, and save both intermediate products.

    Parameters
    ----------
    raw_npz_path       : path to .npz from load_data.save_loaded_data()
    Rsqrd              : noise guess for TDS baseline correction
    fcutoff_hz         : Butterworth cutoff frequency in Hz
    out_baseline_path  : output .npz for baseline-corrected data (auto-named if None)
    out_filtered_path  : output .npz for filtered data (auto-named if None)

    Returns
    -------
    dict with 'data_nA_baseline', 'data_nA_filtered', 't', 'fsample', 'Rsqrd', 'fcutoff_hz'
    """
    raw_npz_path = Path(raw_npz_path)
    loaded = np.load(str(raw_npz_path), allow_pickle=False)

    fsample    = float(loaded["fsample"])
    n_segments = int(loaded["n_segments"])

    if n_segments == 1:
        segments = [(loaded["t"], loaded["data_nA"])]
    else:
        segments = [(loaded[f"t_{i}"], loaded[f"data_nA_{i}"]) for i in range(n_segments)]

    bl_segments   = []
    filt_segments = []
    t_segments    = []

    for t, data in segments:
        bl_data, _   = baseline_correct(data, Rsqrd)
        filt_data    = lowpass_filter(bl_data, fcutoff_hz, fsample)
        bl_segments.append(bl_data)
        filt_segments.append(filt_data)
        t_segments.append(t)

    stem = raw_npz_path.stem
    out_baseline_path = out_baseline_path or str(raw_npz_path.parent / f"{stem}_baseline.npz")
    out_filtered_path = out_filtered_path or str(raw_npz_path.parent / f"{stem}_baseline_filt_{int(fcutoff_hz)}Hz.npz")

    _save_segments(bl_segments, t_segments, fsample, Rsqrd, out_baseline_path, extra={"Rsqrd": Rsqrd})
    _save_segments(filt_segments, t_segments, fsample, Rsqrd, out_filtered_path,
                   extra={"Rsqrd": Rsqrd, "fcutoff_hz": fcutoff_hz})

    print(f"[baseline_filter] Baseline-corrected → {out_baseline_path}")
    print(f"[baseline_filter] Filtered           → {out_filtered_path}")

    result = {"fsample": fsample, "Rsqrd": Rsqrd, "fcutoff_hz": fcutoff_hz}
    if n_segments == 1:
        result["t"] = t_segments[0]
        result["data_nA_baseline"] = bl_segments[0]
        result["data_nA_filtered"] = filt_segments[0]
    else:
        result["t"] = t_segments
        result["data_nA_baseline"] = bl_segments
        result["data_nA_filtered"] = filt_segments

    return result


def _save_segments(segments, t_segments, fsample, Rsqrd, path, extra=None):
    payload = {"fsample": np.array(fsample), "n_segments": np.array(len(segments))}
    if extra:
        for k, v in extra.items():
            payload[k] = np.array(v)
    if len(segments) == 1:
        payload["data"] = segments[0]
        payload["t"]    = t_segments[0]
    else:
        for i, (d, t) in enumerate(zip(segments, t_segments)):
            payload[f"data_{i}"] = d
            payload[f"t_{i}"]    = t
    np.savez(path, **payload)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Baseline-correct and filter patch-clamp data.")
    parser.add_argument("raw_npz", help="Path to .npz from load_data.py")
    parser.add_argument("Rsqrd", type=float, help="Noise parameter for TDS baseline correction")
    parser.add_argument("fcutoff_hz", type=float, help="Butterworth cutoff frequency (Hz)")
    args = parser.parse_args()

    process(args.raw_npz, args.Rsqrd, args.fcutoff_hz)
