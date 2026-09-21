# SIH26168 — Heading Drift Investigation Report

**System:** SIH26168 AI-ML Based Intelligent Dead Reckoning System  
**Evaluation Target:** Gyroscope Yaw Integration, Mount Alignment, EKF/NHC Constraints, and Outage Drift  
**Date:** 2026-09-21  

---

## 1. Executive Summary

This report presents a code-level and empirical investigation into heading drift during GNSS-denied navigation. Heading drift is the primary source of trajectory error during extended GNSS outages ($>30\text{ seconds}$), particularly in urban environments with sharp turns.

---

## 2. Code-Level Inspection & Sensor Mapping

### 2.1 Sensor Axis & Mapping Convention
* **Source Dataset Headers:** `GYROSCOPE Yaw (rad/s)`, `GYROSCOPE Pitch (rad/s)`, `GYROSCOPE Roll (rad/s)`.
* **Phone Orientation:** Smartphone mounted upright on vehicle dashboard/windshield.
* **Axis Alignment:** Vehicle vertical yaw rotation axis aligns with smartphone $-Y$ axis (pointing downwards).
* **Pipeline Integration:** In `demo_realtime_navigation/backend/replay_engine.py:L328`:
  $$\text{yaw\_rate\_raw} = -\text{gyro\_y}$$
  This mapping correctly isolates vehicle yaw rate from phone sensor inputs.

### 2.2 Gyroscope Units & Timing Verification
* **Sensor Stream Units:** Radians per second ($\text{rad/s}$).
* **Integration Step:** In `demo_realtime_navigation/backend/navigation_core.py:L39-L44`:
  $$\Delta \psi = \omega_{\text{yaw}} \cdot dt \quad (\text{rad})$$
  $$\psi_{\text{deg}} = \text{degrees}(\psi_{\text{rad}})$$
  $$\psi_{\text{rad}} \in [-\pi, \pi]$$
  * Sampling frequency is $10.0\text{ Hz}$ ($dt = 0.1\text{ s}$). Integration is mathematically unit-consistent.

### 2.3 Bias Calibration Procedure
* **Online Pre-Outage Calibration (`replay_engine.py`):**
  * When GNSS is locked and course change is straight ($|\Delta \psi_{\text{ref}}| < 0.2^\circ/\text{step}$), raw yaw samples are collected into a 300-sample circular buffer.
  * `online_gyro_bias` is estimated using **median filtering**:
    $$\text{bias}_{\text{gyro}} = \text{median}(\mathbf{\Omega}_{\text{yaw\_samples}})$$
  * Median estimation provides high immunity against sudden vibration or chassis jitter.

### 2.4 Online Yaw Scale Calibration
* **Least-Squares (LSQ) Scale Estimation (`replay_engine.py`):**
  * During pre-outage turning maneuvers ($|\Delta \psi_{\text{ref}}| > 0.3^\circ/\text{step}$), LSQ terms are accumulated:
    $$\text{num} += g_{\text{debiased}} \cdot \dot{\psi}_{\text{ref}}, \quad \text{den} += g_{\text{debiased}}^2$$
    $$\text{scale} = \text{clip}\left(\frac{\text{num}}{\text{den}}, 0.5, 2.0\right)$$
  * Corrected yaw rate applied during outage:
    $$\omega_{\text{corrected}} = (\text{yaw\_rate\_raw} - \text{bias}_{\text{gyro}}) \times \text{scale}$$

### 2.5 Initial Heading Alignment
* At GNSS blackout onset ($t = t_{\text{outage}}$), `NavigationCore` initializes heading to the last valid GNSS reference heading:
  $$\psi_0 = \psi_{\text{ref}}(t_{\text{outage}})$$
* During GNSS-off operation, heading propagates strictly via internal IMU integration with **zero reference heading leakage**.

### 2.6 Non-Holonomic Constraints (NHC) & ZUPT Integration
* **NHC Enforcement (`drift_corrector.py` & `navigation_core.py`):**
  * Lateral velocity orthogonal to vehicle heading is constrained to $0$:
    $$dNorth = v_{\text{forward}} \cdot \cos(\psi) \cdot dt, \quad dEast = v_{\text{forward}} \cdot \sin(\psi) \cdot dt$$
* **Zero-Velocity Updates (`SafeStandstillDetector`):**
  * Evaluates 6-DOF IMU invariants: accelerometer variance $< 0.015\text{ m}^2/\text{s}^4$ and gyro magnitude $< 0.02\text{ rad/s}$ across an 8-step window.
  * When active, forward velocity is zeroed ($v = 0.0\text{ m/s}$), preventing false position drift during standstill.

---

## 3. Diagnostic Heading Measurements

Evaluated across Motorway (`IOVNBD_S3c`) and Urban (`IOVNBD_S3a`) benchmark sessions:

| Benchmark Session | Outage Duration | Heading MAE | Heading RMSE | Max Heading Error | Gyro Bias Est. | Primary Error Driver |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **IOVNBD_S3c (Motorway)** | 10 s | $2.20^\circ$ | $3.24^\circ$ | $4.72^\circ$ | $-0.0010\text{ rad/s}$ | Low angular rate noise |
| **IOVNBD_S3c (Motorway)** | 30 s | $4.40^\circ$ | $5.24^\circ$ | $11.45^\circ$ | $-0.0010\text{ rad/s}$ | Slight scale residual |
| **IOVNBD_S3c (Motorway)** | 60 s | $4.69^\circ$ | $5.17^\circ$ | $12.30^\circ$ | $-0.0010\text{ rad/s}$ | Long-term integration drift |
| **IOVNBD_S3c (Motorway)** | 120 s | $4.69^\circ$ | $5.28^\circ$ | $15.26^\circ$ | $-0.0010\text{ rad/s}$ | Unobservable 1-DOF yaw drift |
| **IOVNBD_S3a (Urban)** | 10 s | $17.77^\circ$ | $23.12^\circ$ | $28.40^\circ$ | $-0.0018\text{ rad/s}$ | $90^\circ$ turn initiation delay |
| **IOVNBD_S3a (Urban)** | 30 s | $20.75^\circ$ | $24.54^\circ$ | $31.10^\circ$ | $-0.0018\text{ rad/s}$ | Cornering scale misalignment |
| **IOVNBD_S3a (Urban)** | 60 s | $17.75^\circ$ | $20.27^\circ$ | $28.90^\circ$ | $-0.0018\text{ rad/s}$ | Sharp turn cumulative error |
| **IOVNBD_S3a (Urban)** | 120 s | $22.44^\circ$ | $24.53^\circ$ | $35.40^\circ$ | $-0.0018\text{ rad/s}$ | Multi-turn heading offset |

---

## 4. Key Findings & Trajectory Impact

1. **Motorway vs Urban Drift Characteristics:**
   * Motorway driving (`S3c`) maintains low heading error ($4.69^\circ$ MAE at 120s) because vehicle motion is predominantly linear with smooth, gradual curves.
   * Urban driving (`S3a`) exhibits significant heading error ($17.75^\circ - 22.44^\circ$ MAE) due to multiple sharp $90^\circ$ turns where 1-DOF gyro integration accumulates small scale and tilt errors.
2. **Impact on Trajectory Accuracy:**
   * In urban sessions (`S3a`), heading drift of $22.44^\circ$ causes a position error of over $300\text{ metres}$ after 120 seconds even when speed estimation is accurate.
   * Fixing velocity alone cannot eliminate position drift if heading error exceeds $15^\circ$. Heading drift is the primary bottleneck for long-duration urban dead reckoning.

---

## 5. Limitations & Recommendations

* **Current System Limitation:** 1-DOF gyro integration lacks absolute directional anchoring during GNSS blackout.
* **Recommended Next Step:** Integrate 3D accelerometer gravity vector projection to dynamically compute phone-to-vehicle transformation matrix $\mathbf{R}_{\text{phone} \to \text{vehicle}}$ across changing mount angles.
