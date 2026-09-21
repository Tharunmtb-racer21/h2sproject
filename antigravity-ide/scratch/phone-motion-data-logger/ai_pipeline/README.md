# ISRO SIH26168 AI Pipeline - Phase 1: Dataset Inspection & Preprocessing

This directory contains the reproducible Python pipeline for **Phase 1: Dataset Inspection, Stream Synchronization, Signal Quality Flagging, and Validation** for the ISRO SIH26168 Intelligent Dead Reckoning system.

---

## 1. Directory Structure

```
ai_pipeline/
├── inspect_dataset.py      # Script 1: Dynamic dataset format & schema inspector
├── preprocess.py           # Script 2: 100 Hz stream synchronization & Butterworth filtering
├── plot_dataset.py         # Script 3: Multi-panel telemetry & 2D GNSS trajectory plotting
├── validate_dataset.py     # Script 4: Ground-truth validation & signal quality reporting
├── DATASET_REPORT.json     # Auto-generated JSON dataset inspection summary
├── processed_data/         # Output directory for 100 Hz synchronized datasets
│   ├── SESSION-20260917_213518_processed.csv
│   ├── SESSION-20260917_213549_processed.csv
│   ├── SESSION-20260917_214611_processed.csv
│   ├── SESSION-20260917_215707_processed.csv
│   └── sensor_data_processed.csv
├── plots/                  # Output directory for generated PNG figures
│   ├── SESSION-20260917_213518_telemetry_plot.png
│   ├── SESSION-20260917_215707_telemetry_plot.png
│   └── ...
└── README.md               # Execution guide and documentation
```

---

## 2. Requirements & Installation

Dependencies: Python 3.10+, `pandas`, `numpy`, `scipy`, `matplotlib`.

```bash
pip install pandas numpy scipy matplotlib
```

---

## 3. How to Run Phase 1 Pipeline

Execute the pipeline scripts sequentially:

### Step 1: Run Dataset Inspection & Format Detection
```bash
python ai_pipeline/inspect_dataset.py
```
*Detects CSV schema, stream types (SENSOR, GNSS, CELLULAR), missing value percentages, duplicate timestamps, and sampling rates. Output saved to `ai_pipeline/DATASET_REPORT.json`.*

### Step 2: Run Stream Preprocessing & 100 Hz Synchronization
```bash
python ai_pipeline/preprocess.py
```
*Aligns raw asynchronous streams onto a uniform 100 Hz grid, applies a 4th-order 15 Hz Butterworth low-pass filter to accelerations, extracts acceleration magnitude, forward-fills GNSS and Cellular signals, and generates quality flags (`flag_imu_valid`, `flag_gnss_valid`, `flag_speed_ref_valid`, `flag_outage`, `flag_cell_valid`). Output saved to `ai_pipeline/processed_data/`.*

### Step 3: Generate Telemetry Plots
```bash
python ai_pipeline/plot_dataset.py
```
*Generates 5-panel telemetry figures (Accel X/Y/Z, Gyro X/Y/Z, Acceleration Magnitude, Speed Reference, Signal Quality Flags) and 2D GNSS ground track maps. Output saved to `ai_pipeline/plots/`.*

### Step 4: Validate Ground-Truth & Dataset Quality
```bash
python ai_pipeline/validate_dataset.py
```
*Performs sanity checks on sample counts, gravity vectors, uniform dt, and verifies availability of ground-truth speed reference before proceeding to AI model training.*

---

## 4. Signal Specifications & Quality Flags

- **Target Frequency**: 100 Hz ($dt = 10\text{ ms}$).
- **Accelerometer Unit**: $\text{m/s}^2$ (includes $g \approx 9.81\text{ m/s}^2$).
- **Gyroscope Unit**: $\text{rad/s}$.
- **Speed Reference**: $\text{m/s}$ and $\text{km/h}$ (GNSS velocity).
- **Quality Flags**:
  - `flag_imu_valid`: 1 if $2.0 \le \|a\| \le 25.0\text{ m/s}^2$, else 0.
  - `flag_gnss_valid`: 1 if position fix present and accuracy $\le 50\text{m}$, else 0.
  - `flag_speed_ref_valid`: 1 if speed reference is non-null and valid, else 0.
  - `flag_outage`: 1 if GNSS signal is missing or invalid (`gnss_valid == 0`), else 0.
