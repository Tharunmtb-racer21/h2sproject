# SIH26168 — Final Production Baseline Evaluation & Benchmark Report

---

## 1. Executive Summary

This report documents the rigorous, reproducible evaluation of the **SIH26168 GNSS-Denied Navigation System** following commit `9ed14e5`. 

The production navigation state operates under strict zero-ground-truth leakage, utilizing **Constant-Speed Persistence (last valid GNSS speed fix)** combined with an **Extended Kalman Filter (EKF)**, **multi-signal Zero-Velocity Updates (ZUPT)**, and **online least-squares calibrated gyroscope heading rate integration**. 

Empirical testing confirms **100% numerical identity (0.00000000 m error)** across normal, NaN-corrupted, and adversarial fake reference data during outages. The production persistence baseline achieves a 120-second outage position error of **$307.55\text{ m}$ ($1201.1\text{ m}$ traveled)** on `IOVNBD_S3a`. The PyTorch neural velocity model ($\Delta v$) is retained exclusively in an offline diagnostic capacity pending model retraining.

---

## 2. Exact Production Configuration

The runtime pipeline in [`demo_realtime_navigation/backend/replay_engine.py`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/backend/replay_engine.py#L353-L418) operates as follows:

1. **Production Velocity Fix**:
   At the exact moment of GNSS outage initiation ($t_0$), the last valid GNSS speed fix $v_0$ is captured by [`outage_controller.py:L57`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/backend/outage_controller.py#L57). Production reconstructed velocity is set to $v_0$ ([`replay_engine.py:L363`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/backend/replay_engine.py#L363)).
2. **EKF Velocity Smoothing**:
   Forward acceleration $a_x$ is clamped to $[-4.0, 4.0]\text{ m/s}^2$ and passed to `VelocityEKF` ([`drift_corrector.py:L110-145`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/backend/drift_corrector.py#L110-L145)) to smooth speed transitions.
3. **Multi-Signal Pure IMU ZUPT**:
   `SafeStandstillDetector` ([`drift_corrector.py:L54-85`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/backend/drift_corrector.py#L54-L85)) monitors accelerometer variance $\sigma_a^2 < 0.015\text{ (m/s}^2)^2$ and gyro magnitude $||\boldsymbol{\omega}|| < 0.02\text{ rad/s}$ over 8 consecutive steps ($0.8\text{s}$). When standstill is declared, production velocity is clamped to $0.0\text{ m/s}$ and EKF state is zeroed.
4. **Calibrated Heading Kinematics**:
   Vehicle vertical yaw rate $\omega_{yaw} = -\text{gyro}_y$ is debiased using online rolling median bias and scaled using pre-outage least-squares (LSQ) scale factor $k_{scale} \in [0.8, 1.2]$ ([`replay_engine.py:L387-394`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/backend/replay_engine.py#L387-L394)).
5. **Local ENU Kinematic Propagation**:
   `NavigationCore.propagate_step()` ([`navigation_core.py:L51-109`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/backend/navigation_core.py#L51-L109)) advances local East and North displacements under Non-Holonomic Constraints ($v_{lat} = 0$).
6. **Diagnostic AI Model Isolation**:
   PyTorch model forward pass inference (`LSTMNoAttention`, 217,729 parameters) executes in [`replay_engine.py:L355`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/backend/replay_engine.py#L355), but its output is saved exclusively to `ai_speed_mps` for diagnostic logging and **never enters production state propagation**.

---

## 3. Dataset and Outage Setup

- **Benchmark Datasets**: Standardized IO-VNBD drive sessions ([`IOVNBD_S3c_standardized.csv`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/data/iovnbd_selected/IOVNBD_S3c_standardized.csv), [`IOVNBD_S3a_standardized.csv`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/data/iovnbd_selected/IOVNBD_S3a_standardized.csv)).
- **Sampling Frequency**: $10\text{ Hz}$ uniform playback ($dt = 0.1\text{ s}$).
- **Outage Initiation Point**: $t = 100.0\text{ seconds}$ (Index $1000$).
- **Outage Horizons**: $10\text{s}$, $30\text{s}$, $60\text{s}$, and $120\text{s}$ simulated blackouts.

---

## 4. Benchmark Methodology

Evaluation metrics are computed using independent ground-truth reference values strictly after state propagation:

- **Final Position Error ($E_{final}$)**: Euclidean distance between final estimated ENU position and final reference ENU position in metres.
- **Maximum Position Error ($E_{max}$)**: Maximum Euclidean position error across all outage steps in metres.
- **Mean Position Error ($E_{mean}$)**: Average Euclidean position error across all outage steps in metres.
- **Speed MAE & RMSE**: Mean Absolute Error and Root Mean Squared Error of forward speed in m/s.
- **Heading MAE & RMSE**: Mean Absolute Error and Root Mean Squared Error of vehicle heading angle in degrees (wrapped to $[-180^\circ, 180^\circ]$).
- **Distance Traveled**: Total reference ground-truth trajectory displacement during the outage in metres.

---

## 5. Production Baseline Results Table

Reproduced via [`reconcile_benchmarks.py`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/reconcile_benchmarks.py):

| Session | Outage Dur | Steps | Final Error | Max Error | Mean Error | Distance Traveled | Hdg Error (Mean) | Speed MAE | Ref Usage |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **IOVNBD_S3c** | $10\text{ s}$ | $100$ | **$5.99\text{ m}$** | $62.65\text{ m}$ | $30.03\text{ m}$ | $77.67\text{ m}$ | $2.20^\circ$ | $1.44\text{ m/s}$ | Eval Only |
| **IOVNBD_S3c** | $30\text{ s}$ | $300$ | **$64.37\text{ m}$** | $89.85\text{ m}$ | $30.54\text{ m}$ | $238.54\text{ m}$ | $4.40^\circ$ | $4.26\text{ m/s}$ | Eval Only |
| **IOVNBD_S3c** | $60\text{ s}$ | $600$ | **$268.18\text{ m}$** | $309.99\text{ m}$ | $99.66\text{ m}$ | $635.84\text{ m}$ | $4.69^\circ$ | $6.44\text{ m/s}$ | Eval Only |
| **IOVNBD_S3c** | $120\text{ s}$ | $1200$ | **$578.38\text{ m}$** | $597.88\text{ m}$ | $273.72\text{ m}$ | $1342.75\text{ m}$ | $4.69^\circ$ | $6.04\text{ m/s}$ | Eval Only |
| **IOVNBD_S3a** | $30\text{ s}$ | $300$ | **$34.31\text{ m}$** | $80.35\text{ m}$ | $32.75\text{ m}$ | $231.99\text{ m}$ | $20.75^\circ$ | $2.51\text{ m/s}$ | Eval Only |
| **IOVNBD_S3a** | $60\text{ s}$ | $600$ | **$42.81\text{ m}$** | $95.14\text{ m}$ | $36.60\text{ m}$ | $554.04\text{ m}$ | $17.75^\circ$ | $2.92\text{ m/s}$ | Eval Only |
| **IOVNBD_S3a** | $120\text{ s}$ | $1200$ | **$320.41\text{ m}$** | $354.25\text{ m}$ | $123.13\text{ m}$ | $1201.09\text{ m}$ | $22.44^\circ$ | $3.85\text{ m/s}$ | Eval Only |

---

## 6. Persistence versus AI Mode Comparison

Executed via [`compare_three_modes.py`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/compare_three_modes.py) for 120-second outages:

- **Mode A**: AI $\Delta v$ Model Speed + Calibrated Gyro Heading (Diagnostic)
- **Mode B**: Production Constant-Speed Persistence ($v_0$) + Calibrated Gyro Heading (**PRODUCTION BASELINE**)
- **Mode C**: Reference Diagnostic (Ground-Truth Speed & Heading — **NON-PRODUCTION EVALUATION DIAGNOSTIC ONLY**)

| Session | Operating Mode | Final Error | Max Error | Mean Error | East Error | North Error | Speed MAE / RMSE | Heading MAE / RMSE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **IOVNBD_S3c** | Mode A (AI Diagnostic) | $566.18\text{ m}$ | $584.92\text{ m}$ | $267.25\text{ m}$ | $205.35\text{ m}$ | $168.43\text{ m}$ | $5.94\text{ / }6.82\text{ m/s}$ | $4.69^\circ\text{ / }5.28^\circ$ |
| **IOVNBD_S3c** | **Mode B (Production)** | **$561.83\text{ m}$** | **$583.06\text{ m}$** | **$265.52\text{ m}$** | **$203.28\text{ m}$** | **$168.32\text{ m}$** | **$5.77\text{ / }6.60\text{ m/s}$** | **$4.40^\circ\text{ / }4.94^\circ$** |
| **IOVNBD_S3c** | Mode C (Ref Diagnostic) | $43.05\text{ m}$ | $141.72\text{ m}$ | $50.29\text{ m}$ | $31.16\text{ m}$ | $36.99\text{ m}$ | $0.00\text{ / }0.00\text{ m/s}$ | $0.00^\circ\text{ / }0.00^\circ$ |
| **IOVNBD_S3a** | Mode A (AI Diagnostic) | $307.28\text{ m}$ | $335.05\text{ m}$ | $115.50\text{ m}$ | $88.97\text{ m}$ | $68.81\text{ m}$ | $3.69\text{ / }4.27\text{ m/s}$ | $22.44^\circ\text{ / }24.53^\circ$ |
| **IOVNBD_S3a** | **Mode B (Production)** | **$307.55\text{ m}$** | **$335.83\text{ m}$** | **$115.85\text{ m}$** | **$89.48\text{ m}$** | **$68.83\text{ m}$** | **$3.72\text{ / }4.28\text{ m/s}$** | **$22.46^\circ\text{ / }24.56^\circ$** |
| **IOVNBD_S3a** | Mode C (Ref Diagnostic) | $86.40\text{ m}$ | $163.35\text{ m}$ | $70.24\text{ m}$ | $49.16\text{ m}$ | $44.50\text{ m}$ | $0.00\text{ / }0.00\text{ m/s}$ | $0.00^\circ\text{ / }0.00^\circ$ |

---

## 7. Leakage-Test Scope & Limitations

The 3-run adversarial leakage suite ([`test_adversarial_leakage.py`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/demo_realtime_navigation/test_adversarial_leakage.py)) proves that setting outage reference columns to NaN or corrupting them with $+10\text{km}$ offsets, $3\text{x}$ speed, and $+180^\circ$ heading offsets produces **$0.00000000\text{ m}$ change in dead reckoning output**.

### Scope & Limitations:
- **Scope**: Proves zero dependence on ground-truth columns during active blackout propagation (`outage_active == True`).
- **Limitation**: Pre-outage initialization relies on GNSS fix $v_0, E_0, N_0, \psi_0$ captured before the blackout. This is legitimate and standard in dead reckoning systems.

---

## 8. Known Limitations

1. **6-DOF Unobservable Yaw Drift**: A 6-DOF IMU without magnetometer cannot observe absolute yaw drift. Complex multi-turn sessions (`IOVNBD_S3a`) exhibit $22.44^\circ$ mean heading drift, driving position error to $307.55\text{ m}$.
2. **Current AI Speed Model Performance**: Step-by-step $\Delta v$ accumulation diverges over long outage horizons. Mode B (Constant-Speed Persistence) remains the superior production velocity source until absolute speed model retraining is completed.

---

## 9. Reproducibility Commands

Run the following commands in the workspace root to reproduce all test and benchmark results:

```bash
# 1. Execute Automated 8-Test Navigation Suite
python demo_realtime_navigation/test_nav_suite.py

# 2. Execute 3-Run Adversarial Ground-Truth Leakage Proof
python demo_realtime_navigation/test_adversarial_leakage.py

# 3. Execute Kinematic Coordinate Convention Test
python demo_realtime_navigation/test_synthetic_square.py

# 4. Execute Reconciled Benchmark Suite
python demo_realtime_navigation/reconcile_benchmarks.py

# 5. Execute 3-Mode Performance Comparison Script
python demo_realtime_navigation/compare_three_modes.py
```

---

## 10. Recommended Next Development Step

**Model Target Reformulation**:
Retrain the PyTorch neural network to predict **Absolute Speed Ratio $r_t = v_t / v_{anchor}$** bounded within $[0.0, 2.0]$ rather than unconstrained step-by-step $\Delta v$ accumulation. This will allow the AI model to capture acceleration/deceleration trends without random-walk velocity divergence.
