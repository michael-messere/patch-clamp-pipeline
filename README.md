# patch-clamp-pipeline

A Python pipeline for processing patch-clamp electrophysiology data, ported from
a set of MATLAB scripts. It reads raw binary recordings, converts them to
nanoamps, baseline-corrects and filters the signal, then splits the result into
equal-length chunks saved as HDF5.

Intermediate steps are saved in Python-native `.npz` format; the final product is
saved as `.hdf5`.

## Pipeline overview

The pipeline runs in three stages, in this order:

| Stage | Python file | MATLAB equivalent | Output |
|-------|-------------|-------------------|--------|
| 1. Load & convert | [`load_data.py`](load_data.py) | `load_data_nA_newGUI.m` | `.npz` (raw nA) |
| 2. Baseline + filter | [`baseline_filter.py`](baseline_filter.py) | `tds.m` + `SAVE_FULL_baseline_corrected_filtered_data.m` | `.npz` (baseline-corrected, filtered) |
| 3. Chunk | [`chunk_data.py`](chunk_data.py) | `SAVE_CHUNKS.m` | `.h5` (final) |

[`pipeline.py`](pipeline.py) orchestrates all three stages end-to-end.

### Stage details

1. **`load_data.py`** — Reads raw `int16` `*_Chan_NN_*.bin` files for a given
   channel, parses the `.param` file for the DAC voltage offset, ADC offset, gain
   (MΩ), and hold voltage, and converts the binary samples to nanoamps. Saves the
   converted signal and time vector to a `.npz` file.

2. **`baseline_filter.py`** — Applies the tridiagonal smoother (TDS) baseline
   estimator (from John Pearson's automated maximum-likelihood paper) to remove
   the baseline, then applies a 4th-order zero-phase Butterworth low-pass filter.
   Saves both the baseline-corrected and the filtered signal as separate `.npz`
   files.

3. **`chunk_data.py`** — Splits the filtered signal into `num_chunks`
   equal-length segments and writes the final product to an HDF5 file.

## Output formats

**Intermediate (`.npz`):** numpy archives for the raw nA data, the
baseline-corrected data, and the filtered data.

**Final (`.h5` / HDF5):**

```
/chunks/
    chunk_00, chunk_01, ...   # signal (nA, float64)
/time/
    chunk_00, chunk_01, ...   # time (seconds, float64)
/metadata/
    bias_str, num_chunks, fsample, Rsqrd, fcutoff_hz   # attributes
```

## Installation

```bash
pip install -r requirements.txt
```

Requirements: `numpy`, `scipy`, `h5py`.

## Usage

### Full pipeline

```bash
python pipeline.py \
  --channel 1 \
  --data_dir /path/to/recording \
  --Rsqrd 1e-4 \
  --fcutoff_hz 1000 \
  --bias_str 0mV \
  --num_chunks 5 \
  --out_dir ./output
```

| Argument | Description |
|----------|-------------|
| `--channel` | Channel number (matches `*_Chan_NN_*.bin` filenames) |
| `--data_dir` | Directory containing the raw `.bin` and `.param` files |
| `--Rsqrd` | Noise parameter for the TDS baseline correction |
| `--fcutoff_hz` | Butterworth low-pass cutoff frequency (Hz) |
| `--bias_str` | Label for the bias condition (e.g. `0mV`) |
| `--num_chunks` | Number of equal-length chunks for the final output |
| `--out_dir` | Directory to write all output files |

### Running stages individually

Each module also has a standalone command-line interface:

```bash
# Stage 1
python load_data.py 1 --data_dir /path/to/recording --out chan01_raw.npz

# Stage 2
python baseline_filter.py chan01_raw.npz 1e-4 1000

# Stage 3
python chunk_data.py chan01_raw_baseline_filt_1000Hz.npz 0mV 5
```

## Hardware constants

Defined in `load_data.py`, matching the original MATLAB source:

- `VDD = 5.0` V
- `BITS = 14`
- `FSAMPLE = 25000` Hz
