"""
make_synthetic_data.py — generate fake raw recordings for testing/demos

Produces a `.param` file and one or more `*_Chan_NN_*.bin` files in the same
binary int16 format the real hardware writes, so the pipeline can be exercised
end-to-end without access to real recordings.

The synthetic current is a slow drifting baseline (so baseline correction has
something to remove) plus a few square "events" and white noise. The values are
converted back into raw int16 ADC counts using the inverse of the conversion in
load_data.py, so a round-trip through the pipeline recovers the intended signal.
"""

import numpy as np
from pathlib import Path

from load_data import VDD, BITS, FSAMPLE


def _nA_to_int16(data_nA, V_DC_offset, ADCoffset, Vhold, gain_Mohm):
    """Inverse of the conversion in load_data.load_data_nA."""
    data_A = data_nA * 1e-9
    data = data_A * (gain_Mohm * 1e6) + V_DC_offset + ADCoffset + Vhold
    counts = (data - V_DC_offset) * (2**BITS - 1) / VDD
    return np.round(counts).astype(np.int16)


def make_synthetic_recording(
    out_dir: str,
    channel_num: int = 1,
    duration_s: float = 2.0,
    n_files: int = 1,
    seed: int = 0,
):
    """
    Write a synthetic recording (`.param` + `.bin` files) into `out_dir`.

    Returns a dict with the parameter values and the clean (noise-free, drift-free)
    nA signal used to build each file, for use as a ground-truth reference in tests.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    # Parameter values written into the .param file
    V_DC_offset = 2.5
    ADCoffset   = 0.01
    gain_Mohm   = 500.0
    Vhold       = 0.0

    param_path = out_dir / "experiment.param"
    param_path.write_text(
        "Patch-clamp synthetic experiment\n"
        f"Default vset (V)  = {V_DC_offset}\n"
        f"ADC Offset {channel_num} value = {ADCoffset}\n"
        f"Resistor {channel_num} gain (Mohm) = {gain_Mohm}\n"
        f"HOLD {channel_num} value = {Vhold}\n"
    )

    n = int(duration_s * FSAMPLE)
    t = np.arange(n) / FSAMPLE

    clean_signals = []
    for i in range(n_files):
        # Slow sinusoidal baseline drift (~0.5 Hz), a couple of square events,
        # and white measurement noise.
        drift = 0.3 * np.sin(2 * np.pi * 0.5 * t)
        events = np.zeros(n)
        events[n // 4 : n // 4 + n // 20] = 1.0
        events[n // 2 : n // 2 + n // 20] = -0.8
        clean = events  # the part baseline correction + filtering should recover
        noise = 0.05 * rng.standard_normal(n)

        data_nA = clean + drift + noise
        counts = _nA_to_int16(data_nA, V_DC_offset, ADCoffset, Vhold, gain_Mohm)

        fname = out_dir / f"recording_Chan_{channel_num:02d}_{i:03d}.bin"
        counts.tofile(str(fname))
        clean_signals.append(clean)

    return {
        "out_dir": str(out_dir),
        "channel_num": channel_num,
        "V_DC_offset": V_DC_offset,
        "ADCoffset": ADCoffset,
        "gain_Mohm": gain_Mohm,
        "Vhold": Vhold,
        "n_samples": n,
        "n_files": n_files,
        "clean_signals": clean_signals,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic patch-clamp recording.")
    parser.add_argument("--out_dir", default="synthetic_data")
    parser.add_argument("--channel", type=int, default=1)
    parser.add_argument("--duration_s", type=float, default=2.0)
    parser.add_argument("--n_files", type=int, default=1)
    args = parser.parse_args()

    info = make_synthetic_recording(
        args.out_dir, args.channel, args.duration_s, args.n_files
    )
    print(f"Wrote {info['n_files']} .bin file(s) + .param to {info['out_dir']}")
