"""
pipeline.py — end-to-end patch-clamp processing pipeline

Steps
-----
1. load_data      : read raw .bin files → convert to nA → save .npz
2. baseline_filter: TDS baseline correction + Butterworth filter → save .npz
3. chunk_data     : split into equal chunks → save final .h5

Usage
-----
python pipeline.py \\
    --channel 1 \\
    --data_dir /path/to/recording \\
    --Rsqrd 1e-4 \\
    --fcutoff_hz 1000 \\
    --bias_str 0mV \\
    --num_chunks 5 \\
    --out_dir ./output
"""

import argparse
from pathlib import Path

from load_data import load_data_nA, save_loaded_data
from baseline_filter import process as baseline_process
from chunk_data import save_chunks_hdf5


def run_pipeline(
    channel_num: int,
    data_dir: str,
    Rsqrd: float,
    fcutoff_hz: float,
    bias_str: str,
    num_chunks: int,
    out_dir: str = ".",
) -> dict:
    """
    Run the full pipeline and return paths to all saved artefacts.

    Parameters
    ----------
    channel_num  : channel index (matches *_Chan_NN_*.bin filenames)
    data_dir     : directory containing raw .bin and .param files
    Rsqrd        : noise parameter for TDS baseline correction
    fcutoff_hz   : Butterworth low-pass cutoff in Hz
    bias_str     : label for the bias condition (e.g. '0mV')
    num_chunks   : number of equal-length chunks for final output
    out_dir      : directory to write all output files

    Returns
    -------
    dict with 'raw_npz', 'baseline_npz', 'filtered_npz', 'hdf5'
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = f"chan{channel_num:02d}"

    # ── Step 1: load raw data ────────────────────────────────────────────────
    print("\n=== Step 1: Loading raw data ===")
    raw = load_data_nA(channel_num, data_dir)
    raw_npz = str(out_dir / f"{stem}_raw.npz")
    save_loaded_data(raw, raw_npz)

    # ── Step 2: baseline correction + filtering ──────────────────────────────
    print("\n=== Step 2: Baseline correction and filtering ===")
    baseline_npz  = str(out_dir / f"{stem}_baseline.npz")
    filtered_npz  = str(out_dir / f"{stem}_baseline_filt_{int(fcutoff_hz)}Hz.npz")
    baseline_process(
        raw_npz,
        Rsqrd,
        fcutoff_hz,
        out_baseline_path=baseline_npz,
        out_filtered_path=filtered_npz,
    )

    # ── Step 3: chunk and save as HDF5 ──────────────────────────────────────
    print("\n=== Step 3: Chunking and saving HDF5 ===")
    hdf5_path = str(out_dir / f"{stem}_bias_{bias_str}_{num_chunks}chunks.h5")
    save_chunks_hdf5(filtered_npz, bias_str, num_chunks, out_hdf5_path=hdf5_path)

    print("\n=== Pipeline complete ===")
    artefacts = {
        "raw_npz":      raw_npz,
        "baseline_npz": baseline_npz,
        "filtered_npz": filtered_npz,
        "hdf5":         hdf5_path,
    }
    for label, path in artefacts.items():
        print(f"  {label:15s}: {path}")

    return artefacts


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end patch-clamp data processing pipeline."
    )
    parser.add_argument("--channel",     type=int,   required=True,  help="Channel number")
    parser.add_argument("--data_dir",    default=".", help="Directory with .bin/.param files")
    parser.add_argument("--Rsqrd",       type=float, required=True,  help="TDS noise parameter")
    parser.add_argument("--fcutoff_hz",  type=float, required=True,  help="Butterworth cutoff (Hz)")
    parser.add_argument("--bias_str",    required=True,  help="Bias label (e.g. '0mV')")
    parser.add_argument("--num_chunks",  type=int,   required=True,  help="Number of output chunks")
    parser.add_argument("--out_dir",     default="output", help="Output directory")
    args = parser.parse_args()

    run_pipeline(
        channel_num=args.channel,
        data_dir=args.data_dir,
        Rsqrd=args.Rsqrd,
        fcutoff_hz=args.fcutoff_hz,
        bias_str=args.bias_str,
        num_chunks=args.num_chunks,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
