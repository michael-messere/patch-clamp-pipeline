"""
load_data.py — Python port of load_data_nA_newGUI.m

Reads raw int16 .bin files for a given channel, parses the .param file
for V_DC_offset, ADC offset, gain (MOhm), and Vhold, then converts to nA.
Saves intermediate output as a .npz file.
"""

import glob
import re
import struct
import numpy as np
from pathlib import Path


# Hardware constants (match MATLAB source)
VDD = 5.0
BITS = 14
FSAMPLE = 25_000  # Hz


def _channel_str(channel_num: int) -> str:
    return f"{channel_num:02d}"


def _read_param_value(param_path: str, key: str) -> float:
    """Return the float value on the first line containing `key`."""
    with open(param_path, "r") as fh:
        for line in fh:
            if key in line:
                _, val = line.split("=", 1)
                return float(val.strip())
    raise ValueError(f"Key '{key}' not found in {param_path}")


def load_data_nA(channel_num: int, data_dir: str = ".") -> dict:
    """
    Load raw binary data for `channel_num` and convert to nA.

    Parameters
    ----------
    channel_num : int
        Channel index (used to find *_Chan_NN_*.bin files).
    data_dir : str
        Directory containing the .bin and .param files.

    Returns
    -------
    dict with keys:
        't'       : list of 1-D np.ndarray (seconds)
        'data_nA' : list of 1-D np.ndarray (nanoamps)
        'fsample' : float
        'channel' : int
    """
    data_dir = Path(data_dir)
    ch_str = _channel_str(channel_num)

    bin_files = sorted(data_dir.glob(f"*_Chan_{ch_str}_*.bin"))
    if not bin_files:
        raise FileNotFoundError(
            f"No .bin files matching *_Chan_{ch_str}_*.bin in {data_dir}"
        )

    param_files = list(data_dir.glob("*.param"))
    if not param_files:
        raise FileNotFoundError(f"No .param file found in {data_dir}")
    param_path = str(param_files[0])

    V_DC_offset = _read_param_value(param_path, "Default vset (V) ")
    ADCoffset   = _read_param_value(param_path, f"ADC Offset {channel_num} value")
    gain_Mohm   = _read_param_value(param_path, f"Resistor {channel_num} gain")
    Vhold       = _read_param_value(param_path, f"HOLD {channel_num} value")

    t_list = []
    data_nA_list = []

    for bf in bin_files:
        raw = np.fromfile(str(bf), dtype=np.int16).astype(np.float64)
        data = raw * VDD / (2**BITS - 1) + V_DC_offset
        data_A = (data - V_DC_offset - ADCoffset - Vhold) / (gain_Mohm * 1e6)
        data_nA = data_A * 1e9

        n = len(data_nA)
        t = np.arange(n) / FSAMPLE

        t_list.append(t)
        data_nA_list.append(data_nA)

    # Collapse to plain arrays when there is only one file
    if len(bin_files) == 1:
        return {
            "t": t_list[0],
            "data_nA": data_nA_list[0],
            "fsample": float(FSAMPLE),
            "channel": channel_num,
        }

    return {
        "t": t_list,
        "data_nA": data_nA_list,
        "fsample": float(FSAMPLE),
        "channel": channel_num,
    }


def save_loaded_data(result: dict, out_path: str) -> None:
    """Save the output of load_data_nA to a .npz file."""
    out_path = Path(out_path)
    if isinstance(result["t"], list):
        payload = {}
        for i, (t, d) in enumerate(zip(result["t"], result["data_nA"])):
            payload[f"t_{i}"] = t
            payload[f"data_nA_{i}"] = d
        payload["n_segments"] = np.array(len(result["t"]))
    else:
        payload = {"t": result["t"], "data_nA": result["data_nA"], "n_segments": np.array(1)}

    payload["fsample"] = np.array(result["fsample"])
    payload["channel"] = np.array(result["channel"])
    np.savez(str(out_path), **payload)
    print(f"[load_data] Saved → {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load raw patch-clamp binary data.")
    parser.add_argument("channel_num", type=int, help="Channel number")
    parser.add_argument("--data_dir", default=".", help="Directory with .bin/.param files")
    parser.add_argument("--out", default=None, help="Output .npz path")
    args = parser.parse_args()

    result = load_data_nA(args.channel_num, args.data_dir)
    out = args.out or f"chan{args.channel_num:02d}_raw.npz"
    save_loaded_data(result, out)
