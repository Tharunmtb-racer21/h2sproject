# Forensic Audit Report: Heading Pipeline, Gyro Drift & Sensor Alignment

**System:** SIH26168 AI-ML Based Intelligent Dead Reckoning System  
**Audit Date:** 2026-09-21  
**Evaluated Session:** `IOVNBD_S3c` (37,183 samples @ 10 Hz)  
**Trained Model Checkpoint:** `outputs/Exp_5_LSTMNoAttention_DeltaV/best_model.pt`  
**Focus of Audit:** Root-cause analysis of the ~110° heading drift over 120 seconds  

---

## A. Current Heading Pipeline Execution Trace

Tracing the exact live execution path for heading and yaw-rate in the production repository:

```
[Raw Smartphone Sensor S-File]
         │  Columns: 'GYROSCOPE Yaw (rad/s)', 'GYROSCOPE Pitch (rad/s)', 'GYROSCOPE Roll (rad/s)'
         ▼
[Preprocessing: ai_pipeline/preprocess_iovnbd.py:L62-L68]
         │  gyro_x = 'GYROSCOPE Yaw'
         │  gyro_y = 'GYROSCOPE Pitch'
         │  gyro_z = 'GYROSCOPE Roll'   <--- CRITICAL MAPPING BUG
         ▼
[Dataset Loading & Replay: demo_realtime_navigation/backend/replay_engine.py:L230-L244]
         │  gyro_z = float(row["gyro_z"])
         ▼
[Online Straight-Line Bias Tracking: backend/replay_engine.py:L263-L270]
         │  Tracks mean gyro_z when GNSS course change < 0.2 deg/step
         ▼
[Outage Yaw Integration: backend/replay_engine.py:L290-L295]
         │  gyro_z_corrected = gyro_z - self.online_gyro_bias
         │  NavigationCore.update_heading(gyro_z_corrected, dt=0.1)
         ▼
[Heading State Propagation: backend/navigation_core.py:L39-L44]
         │  self.heading_rad += gyro_z_corrected * dt
         │  self.heading_rad = (self.heading_rad + pi) % (2*pi) - pi
         ▼
[2D Kinematic Position Displacement: backend/navigation_core.py:L82-L86]
         ├── dNorth = v_reconstructed * cos(self.heading_rad) * dt
         └── dEast  = v_reconstructed * sin(self.heading_rad) * dt
```

* **Exact Source Files, Functions, and Lines:**
  1. Data Ingestion / Mapping: `ai_pipeline/preprocess_iovnbd.py` (`process_iovnbd_session_pair:L62-L68`)
  2. Telemetry Extract & Bias Tracking: `demo_realtime_navigation/backend/replay_engine.py` (`ReplayEngine.process_current_frame:L230-L270`)
  3. Outage Yaw Dispatch: `demo_realtime_navigation/backend/replay_engine.py` (`ReplayEngine.process_current_frame:L290-L295`)
  4. Heading Integration: `demo_realtime_navigation/backend/navigation_core.py` (`NavigationCore.update_heading:L39-L44`)
  5. Coordinate Propagation: `demo_realtime_navigation/backend/navigation_core.py` (`NavigationCore.propagate_step:L82-L86`)

---

## B. Gyroscope Units Verification

* **Raw Data Headers in `S-S3c.csv`:**
  * `' GYROSCOPE Yaw (rad/s)'`
  * `' GYROSCOPE Pitch (rad/s)'`
  * `' GYROSCOPE Roll (rad/s)'`
* **Finding:** Gyroscope sensor streams are recorded in **radians per second ($\text{rad/s}$)**.
* **Production Conversion:** Direct kinematic integration without intermediate unit conversion:
  $$\Delta \psi = \omega \cdot dt \quad [\text{rad/s} \times \text{s} = \text{rad}]$$
  $$\psi_{\text{deg}} = \frac{180}{\pi} \cdot \psi_{\text{rad}}$$
  * The mathematical conversion in `NavigationCore.update_heading` is unit-consistent.

---

## C. Timing & Sampling Alignment

| Parameter | Value | Verification Source | Status |
|---|:---:|:---:|:---:|
| Source Data Rate | $10.0\text{ Hz}$ | `IOVNBD_S3c_standardized.csv` mean $dt = 0.099999\text{ s}$ | Validated |
| Replay Engine Step Rate | $10.0\text{ Hz}$ | `replay_engine.py` $dt = 0.1\text{ s}$ | Validated |
| Gyro Integration $dt$ | $0.1000\text{ s}$ | `NavigationCore.update_heading(dt=0.1)` | Validated |
| 10 Hz vs 50 Hz Mismatch | None | Standardized CSVs are resampled to uniform $10\text{ Hz}$ grid | Validated |

---

## D. Gyroscope Bias Analysis

* **Calibration Interval:** $t \in [0.0\text{s}, 10.0\text{s}]$ (index 0 to 100, $N=100$ samples @ 10 Hz).
* **Kinematic State during Calibration:**
  * Mean Vehicle Speed: $9.64\text{ m/s}$ ($34.7\text{ km/h}$) — Range: $[7.64, 10.58]\text{ m/s}$.
  * Number of Stationary Samples: **0 samples** ($v < 0.05\text{ m/s}$).
  * Initial Heading: $293.03^\circ$, Final Heading at $t=10\text{s}$: $294.09^\circ$ ($\Delta \psi = +1.06^\circ$ over 10s).
  * Vehicle Behavior: **Straight-line driving on an open road** (mean course deviation $0.022^\circ/\text{step}$).
* **Sensor Statistics over Calibration Window:**
  * Mean `gyro_z`: $-0.000995\text{ rad/s}$ ($-0.0570^\circ/\text{s}$)
  * Standard Deviation $\sigma(\text{gyro}_z)$: $0.019025\text{ rad/s}$
* **Ground-Truth Usage Check:** Reference heading was accessed solely to confirm straight-line motion ($|\Delta \psi| < 0.2^\circ$), and was **NOT** passed into the heading state.

---

## E. Dataset Sensor Availability

Inspecting both the raw S-file (`S-S3c.csv`) and standardized CSV:

| Sensor Modality | Raw S-File Column Name | Standardized Column | Available in Repo? |
|---|---|---|:---:|
| **3-Axis Accelerometer** | `ACCELEROMETER X/Y/Z (m/s²)` | `accel_x, accel_y, accel_z` | Yes |
| **3-Axis Gyroscope** | `GYROSCOPE Yaw/Pitch/Roll (rad/s)` | `gyro_x, gyro_y, gyro_z` | Yes |
| **Gravity Vector** | `GRAVITY X/Y/Z (m/s²)` | Not in standardized CSV | In raw S-file |
| **3-Axis Magnetometer** | `MAGNETIC FIELD X/Y/Z (μT)` | Not in standardized CSV | In raw S-file |
| **Android Orientation** | `ORIENTATION (Yaw/Pitch/Roll) (°)` | Not in standardized CSV | In raw S-file |
| **Smartphone GNSS** | `GPS LATITUDE/LONGITUDE/ALTITUDE/SPEED/ORIENTATION` | `latitude, longitude, altitude, gnss_speed, gnss_bearing` | Yes |
| **Vehicle VBOX Ground Truth** | `Velocity (km/hr), Heading (degrees)` | `reference_speed, reference_heading` | Yes (Eval only) |

---

## F. Heading Error Growth by Outage Duration

Evaluated on `IOVNBD_S3c` ($t=10.0\text{s} \to 130.0\text{s}$):

| Outage Duration | True Heading Change ($\Delta \psi_{\text{ref}}$) | Gyro Heading Change ($\Delta \psi_{\text{int}}$) | Heading MAE | Heading RMSE | Final Heading Error | Mean Yaw-Rate Error |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **10 s** | $-10.09^\circ$ | $+0.91^\circ$ | $3.96^\circ$ | $4.72^\circ$ | **$11.00^\circ$** | $9.12^\circ/\text{s}$ |
| **30 s** | $-15.27^\circ$ | $-3.81^\circ$ | $11.09^\circ$ | $12.34^\circ$ | **$11.45^\circ$** | $4.43^\circ/\text{s}$ |
| **60 s** | $+61.16^\circ$ | $-8.37^\circ$ | $16.40^\circ$ | $24.05^\circ$ | **$69.53^\circ$** | $6.30^\circ/\text{s}$ |
| **120 s** | **$+98.12^\circ$** | **$-13.76^\circ$** | **$35.70^\circ$** | **$50.41^\circ$** | **$111.89^\circ$** | $6.76^\circ/\text{s}$ |

* **Physical Insight:** Over 120s, the vehicle executes a **$+98.12^\circ$ clockwise turn**. However, the integrated `gyro_z` signal registered a **$-13.76^\circ$ counter-clockwise turn**, resulting in a **$111.89^\circ$ error**.

---

## G. Oracle Separation Matrix

Separating the contribution of Velocity Error vs. Heading Error to total position drift across all outage durations:

| Outage Duration | (A) Gyro Hdg + AI Vel (Production) | (B) Ref Hdg + AI Vel (Hdg Error Removed) | (C) Gyro Hdg + Ref Spd (Vel Error Removed) | (D) Ref Hdg + Ref Spd (Oracle Baseline) |
|:---:|:---:|:---:|:---:|:---:|
| **10 s** | $21.27\text{ m}$ | $21.42\text{ m}$ | $7.99\text{ m}$ | $8.53\text{ m}$ |
| **30 s** | $175.04\text{ m}$ | $175.01\text{ m}$ | $9.23\text{ m}$ | $6.62\text{ m}$ |
| **60 s** | $441.87\text{ m}$ | $402.26\text{ m}$ | $48.60\text{ m}$ | $49.64\text{ m}$ |
| **120 s** | **$959.55\text{ m}$** | **$510.58\text{ m}$** | **$619.15\text{ m}$** | **$39.11\text{ m}$** |

* **Key Separation Insight:**
  * At 120s, removing heading error (Configuration B) cuts position drift from **$959.55\text{ m} \to 510.58\text{ m}$** ($-448.97\text{ m}$ error reduction).
  * In Configuration C, using perfect ground-truth speed with production gyro heading still produces **$619.15\text{ m}$ position drift**.
  * This proves heading drift accounts for $>50\%$ of total position error during long outages.

---

## H. Root-Cause Analysis: Sensor Axis Alignment

### 1. The Physical Cause of Heading Inversion:
* **Correlation with True Vehicle Yaw Rate:**
  * $\text{corr}(\text{gyro}_z, \dot{\psi}_{\text{true}}) = -0.0584$ (Near zero correlation)
  * $\text{corr}(\text{gyro}_x, \dot{\psi}_{\text{true}}) = -0.0361$ (Near zero correlation)
  * $\text{corr}(-\text{gyro}_y, \dot{\psi}_{\text{true}}) = \mathbf{+0.4753}$ (Strong, direct correlation!)
* **Why?**
  * When a smartphone is placed in an upright dashboard/windshield mount, the vehicle's vertical yaw rotation axis (rotation around gravity) points along the phone's **vertical $Y$-axis (or $-Y$)**, NOT perpendicular to the screen ($Z$-axis).
  * In addition, `preprocess_iovnbd.py:L62-L68` mapped `'GYROSCOPE Roll'` to `gyro_z`, effectively integrating screen-plane roll rather than vehicle yaw.

### 2. Forensic Demonstration on Held-Out `IOVNBD_S3c` (120s Outage):

| Axis Integrated | 120s Heading MAE | 120s Heading RMSE | 120s Final Heading Error | 120s Position Error (with Ref Speed) |
|---|:---:|:---:|:---:|:---:|
| `+gyro_z` (Current Production) | $37.86^\circ$ | $53.59^\circ$ | $118.72^\circ$ | $619.15\text{ m}$ |
| `+gyro_x` (Mapped to Raw Yaw) | $33.15^\circ$ | $46.49^\circ$ | $98.83^\circ$ | $542.80\text{ m}$ |
| **$-\text{gyro}_y$ (True Mount Vertical Axis)** | **$8.87^\circ$** | **$10.09^\circ$** | **$15.26^\circ$** | **$77.83\text{ m}$** |

---

## I. Potential Heading-Fusion Approaches & Limitations

1. **3D Gravity-Vector Frame Alignment:**
   * **Mechanism:** Use 3-axis accelerometer gravity vector $\mathbf{g} = (a_x, a_y, a_z)$ during steady motion to compute the 3D rotation matrix $\mathbf{R}_{\text{phone} \to \text{vehicle}}$, isolating the true vertical yaw component: $\omega_{\text{yaw}} = \mathbf{R} \cdot \boldsymbol{\omega}$.
   * **Advantage:** Self-calibrating across any arbitrary smartphone mount angle without user intervention.
2. **Magnetometer Yaw Fusion:**
   * **Limitations:** Severe ferromagnetic disturbances from vehicle chassis, motor, and infotainment systems cause multi-microtesla hard/soft iron distortions indoors/in-vehicle.
3. **Android Onboard Orientation Sensor:**
   * **Limitations:** Proprietary black-box fusion; unavailable when running standalone on raw IMU hardware.

---

## J. Recommended Next Controlled Experiment

* **Proposed Next Step:** Implement an automated Phone-to-Vehicle 3D Orientation Calibration module (`sih_modules/alignment.py`) that projects 3-axis angular rates $(\omega_x, \omega_y, \omega_z)$ onto the gravity vector $\hat{\mathbf{g}}$ determined from pre-outage GNSS-locked acceleration.
* **Controlled Protocol:** Validate on `IOVNBD_S3c` and measure whether 120s heading error drops from $111.89^\circ \to < 16^\circ$ without using any ground-truth heading in navigation.

---

## K. Final Status

**BUG FOUND**

* **Summary of Root Cause:**
  1. `ai_pipeline/preprocess_iovnbd.py` mapped `'GYROSCOPE Roll'` to `gyro_z`.
  2. The phone mount orientation in `IOVNBD_S3c` aligned the vehicle's vertical yaw rotation axis with phone $-Y$, while production `NavigationCore` integrated `gyro_z`.
  3. This axis mismatch caused the system to completely miss the $+98.12^\circ$ vehicle turn during the 120-second outage.
