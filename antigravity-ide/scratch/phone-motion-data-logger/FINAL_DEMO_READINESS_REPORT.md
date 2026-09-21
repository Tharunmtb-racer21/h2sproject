# FINAL DEMO READINESS & VALIDATION REPORT — SIH168

**Project:** SIH26168 AI-ML Based Intelligent Dead Reckoning System for Seamless Navigation  
**Problem Statement:** ISRO Dead-Reckoning Navigation Under GNSS Denied Environments  
**System Status:** **FREEZE & DEMO READY (VERIFIED ZERO-LEAKAGE)**  
**Date:** September 21, 2026  

---

## 1. Executive Summary & Configuration Freeze

All algorithmic developments and experimental explorations are now **officially frozen**. The navigation pipeline has completed rigorous verification, zero-leakage auditing, multi-signal physical ZUPT calibration, smooth sigmoid GNSS recovery validation, and automated regression testing.

### Final Frozen Configuration: **Configuration F (Pure Autonomous Combined)**
- **Sensor Frame Yaw Rate:** Vehicle vertical axis $- \text{gyro}_y$ with online pre-outage bias subtraction.
- **AI Neural Velocity Estimator:** Frozen PyTorch `Exp_5_LSTMNoAttention_DeltaV` checkpoint (`best_model.pt`) with training-fitted MinMax normalization (`scaler_params.json`).
- **1D Extended Kalman Filter (EKF):** Fuses high-frequency IMU forward acceleration ($a_x$) with AI neural Delta-V velocity estimates.
- **Safe Physical IMU ZUPT:** Standstill detector relying strictly on 6-DOF IMU invariants ($\sigma^2(a) < 0.015\text{ m}^2/\text{s}^4$, $\|\boldsymbol{\omega}\| < 0.02\text{ rad/s}$, 8-step persistence) with **zero velocity arguments**.
- **Non-Holonomic Constraint (NHC):** Lateral velocity vector damping along instantaneous vehicle heading ($\alpha = 0.95$).
- **Sigmoid Restoration Handover:** 2.0-second S-curve transition on GNSS recovery to eliminate coordinate jumps.
- **Map Matching:** **PERMANENTLY DISABLED / EXCLUDED** from production navigation to prevent test-set road polyline leakage.

---

## 2. Audited Benchmark Metrics (`IOVNBD_S3c` — Zero Ground-Truth Leakage)

All configurations evaluated under identical initial conditions ($t = 10.0\text{s}$, $v_{\text{anchor}} = 9.87\text{ m/s}$) across standardized outage durations:

| Configuration | 10s Error (Max) | 30s Error (Max) | 60s Error (Max) | 120s Error (Max) | Heading RMSE | Vel RMSE | ZUPTs (120s) | Production Decision |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. Baseline (+gyro_z, Unscaled)** | 23.48m (76.36m) | 193.05m (193.05m) | 492.53m (492.53m) | 1000.92m (1000.92m) | 50.49° | 7.11 m/s | 0 | Deprecated (Wrong Axis) |
| **B. Corrected Yaw (Scaled, -gyro_y)** | 21.20m (74.67m) | 174.67m (174.67m) | 393.87m (393.87m) | 485.48m (549.43m) | 4.24° | 6.60 m/s | 0 | Baseline Standard |
| **C. Corrected Yaw + NHC** | 21.20m (74.67m) | 174.67m (174.67m) | 393.87m (393.87m) | 485.48m (549.43m) | 4.24° | 6.60 m/s | 0 | Integrated |
| **D. Corrected Yaw + Safe IMU-ZUPT** | 21.20m (74.67m) | **42.54m (74.67m)** | **125.07m (125.07m)** | **129.27m (195.49m)** | 4.24° | **3.81 m/s** | 388 | Integrated (-73.4%) |
| **E. Corrected Yaw + EKF Fusion** | **19.59m (73.52m)** | 171.63m (171.63m) | 391.62m (391.62m) | 486.49m (546.80m) | 4.24° | 6.64 m/s | 0 | Integrated (+7.6% 10s) |
| **F. Pure Autonomous Combined (B+C+D+E)** | **19.59m (73.52m)** | **44.94m (73.92m)** | **127.20m (127.20m)** | **137.65m (200.31m)** | **4.24°** | **4.03 m/s** | 388 | **SELECTED FROZEN** |
| *G. Map Matching (Offline Test-Set Exp)* | *21.14m (74.67m)* | *14.85m (74.67m)* | *65.63m (74.67m)* | *19.14m (108.61m)* | *4.24°* | *6.60 m/s* | *0* | *DISABLED (Leakage Warning)* |

---

## 3. Strict Zero-Leakage Audit Summary

1. **State Isolation:** During simulated GNSS denial (`outage_active == True`), the production engine queries **zero** reference values (`reference_speed`, `reference_heading`, `ref_east_m`, `ref_north_m`, `latitude`, `longitude`).
2. **Anchor Integrity:** Initial anchor position and velocity are latched exclusively at the single time-step immediately preceding outage onset.
3. **ZUPT Detector Interface:** `SafeStandstillDetector.update(...)` accepts strictly 6-DOF IMU readings (`accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z`). No velocity arguments are accepted.
4. **Causal Forward Window:** Feature buffers strictly look back ($t-200 \to t$), ensuring zero future sample lookahead.

---

## 4. Full Validation & Verification Results

### 4.1. Continuous Outage & Sigmoid Restoration Test (`test_continuous_restoration.py`)
- **Status:** **PASS (100% OK)**
- **Outage Transition:** Seamless state switch to `AI_DEAD_RECKONING` at $t=10.0\text{s}$.
- **Sigmoid Recovery:** Over $2.0\text{s}$ (20 steps), position error blended smoothly from $43.95\text{m} \to 0.00\text{m}$ with maximum step displacement $\le 3.315\text{ m}$.
- **Discontinuities / Position Jumps:** **Zero (No visual teleportation)**.

### 4.2. Unittest Regression Suite (`sih_modules/tests`)
- **Status:** **PASS (11/11 tests passing in 0.079s)**
- Verified dead-reckoning coordinate transformations, outage simulation timing, and sensor scaling.

### 4.3. ZUPT False-Positive Verification
- **Episode 1 ($t = 25.3\text{s} \to 33.2\text{s}$):** 80 samples, Mean GT speed = $0.022\text{ m/s}$ (Traffic deceleration & stop).
- **Episode 2 ($t = 34.1\text{s} \to 56.2\text{s}$):** 222 samples, Mean GT speed = $0.048\text{ m/s}$ (Red light idle).
- **Episode 3 ($t = 85.2\text{s} \to 93.7\text{s}$):** 86 samples, Mean GT speed = $0.038\text{ m/s}$ (Turn yield stop).
- **False Cruising Triggers:** **0** (Zero false activations during highway driving or road vibration).

---

## 5. Live Demonstration Instructions

1. **Start the Real-Time Navigation Server:**
   ```bash
   python demo_realtime_navigation/run_demo.py --port 8080 --no-browser
   ```
2. **Open Dashboard in Browser:**
   Navigate to `http://127.0.0.1:8080` (or `http://localhost:8080`).
3. **Execution Sequence for Hackathon Jury:**
   - Click **PLAY** to start live PyTorch inference on benchmark session `IOVNBD_S3c`.
   - Observe live speedometer, heading compass, and green ground-truth trajectory.
   - Click **10s Outage**: Observe immediate transition to yellow dead-reckoning trajectory and AI inference telemetry, followed by smooth sigmoid restoration.
   - Click **30s Outage**: Demonstrate ZUPT engaging at the intersection ($t \approx 25\text{s} \to 33\text{s}$) to clamp drift, followed by smooth handover.
   - Click **Continuous Outage**: Demonstrate multi-minute autonomous dead reckoning under sustained blackout.
   - Click **Restore GNSS**: Demonstrate zero-jump S-curve return to locked navigation.

---

## 6. Known Operational Limitations

1. **Continuous High-Speed Straight Line Outage:** In driving scenarios where the vehicle cruises uninterrupted for multiple minutes without any stops (no ZUPT events), integration error scales with time ($\approx 1\text{ m/s}$ cumulative velocity bias).
2. **Smartphone Alignment:** The system assumes an upright dashboard mount where vertical vehicle yaw corresponds to $-\text{gyro}_y$.
