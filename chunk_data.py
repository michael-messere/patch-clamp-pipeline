"""
chunk_data.py — Python port of SAVE_CHUNKS.m

Splits a processed data array into N equal-length chunks and saves the final
product as an HDF5 file. Each chunk is stored as a separate dataset.
"""

import numpy as np
import h5py
from pathlib import Path


def chunk_data(data: np.ndarray, num_chunks: int) -> list[np.ndarray]:
    """
    Split `data` into `num_chunks` equal-length segments (mirrors MATLAB reshape).
    Trailing samples that don't divide evenly are discarded, matching MATLAB behaviour.
    """
    n_per_chunk = len(data) // num_chunks
    truncated = data[: n_per_chunk * num_chunks]
    return [truncated[i * n_per_chunk : (i + 1) * n_per_chunk] for i in range(num_chunks)]


def save_chunks_hdf5(
    filtered_npz_path: str,
    bias_str: str,
    num_chunks: int,
    out_hdf5_path: str | None = None,
) -> str:
    """
    Load filtered data from a .npz, split into chunks, and save to HDF5.

    HDF5 layout
    -----------
    /metadata/
        bias_str, num_chunks, fsample, Rsqrd, fcutoff_hz
    /chunks/
        chunk_00, chunk_01, ...   (nA, float64)
    /time/
        chunk_00, chunk_01, ...   (seconds, float64)

    Parameters
    ----------
    filtered_npz_path : str  — path to .npz from baseline_filter.process()
    bias_str          : str  — label for the bias condition (e.g. "0mV")
    num_chunks        : int  — number of equal-length chunks
    out_hdf5_path     : str  — output file path (auto-named if None)

    Returns
    -------
    str : path to the written HDF5 file
    """
    npz_path = Path(filtered_npz_path)
    loaded   = np.load(str(npz_path), allow_pickle=False)

    n_segments = int(loaded["n_segments"])
    fsample    = float(loaded["fsample"])

    # Concatenate across segments if needed
    if n_segments == 1:
        data = loaded["data"]
        t    = loaded["t"]
    else:
        data = np.concatenate([loaded[f"data_{i}"] for i in range(n_segments)])
        t    = np.concatenate([loaded[f"t_{i}"]    for i in range(n_segments)])

    chunks   = chunk_data(data, num_chunks)
    t_chunks = chunk_data(t,    num_chunks)

    out_hdf5_path = out_hdf5_path or str(
        npz_path.parent / f"{npz_path.stem}_bias_{bias_str}_{num_chunks}chunks.h5"
    )

    with h5py.File(out_hdf5_path, "w") as hf:
        meta = hf.create_group("metadata")
        meta.attrs["bias_str"]   = bias_str
        meta.attrs["num_chunks"] = num_chunks
        meta.attrs["fsample"]    = fsample
        for key in ("Rsqrd", "fcutoff_hz"):
            if key in loaded:
                meta.attrs[key] = float(loaded[key])

        grp_data = hf.create_group("chunks")
        grp_time = hf.create_group("time")
        for i, (chunk, t_chunk) in enumerate(zip(chunks, t_chunks)):
            name = f"chunk_{i:02d}"
            ds = grp_data.create_dataset(name, data=chunk, compression="gzip")
            ds.attrs["bias_str"]     = bias_str
            ds.attrs["chunk_index"]  = i
            ds.attrs["n_samples"]    = len(chunk)
            grp_time.create_dataset(name, data=t_chunk, compression="gzip")

    print(f"[chunk_data] HDF5 saved → {out_hdf5_path}  ({num_chunks} chunks)")
    return out_hdf5_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Split filtered data into chunks and save as HDF5.")
    parser.add_argument("filtered_npz", help="Path to filtered .npz from baseline_filter.py")
    parser.add_argument("bias_str",     help="Bias condition label (e.g. '0mV')")
    parser.add_argument("num_chunks",   type=int, help="Number of chunks to split into")
    parser.add_argument("--out",        default=None, help="Output .h5 path")
    args = parser.parse_args()

    save_chunks_hdf5(args.filtered_npz, args.bias_str, args.num_chunks, args.out)
