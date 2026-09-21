# IMPLEMENTATION GAP ANALYSIS: SIH26168 SYSTEM

**System Target**: SIH26168 AI-ML Based Intelligent Dead Reckoning System for Seamless Navigation  
**Audit Scope**: Entire Codebase (`ai_pipeline/`, `sih_modules/`, `data/`)  

---

## 1. Executive Summary of Gaps

While the current codebase establishes a functional modular prototype for data logging, signal preprocessing, deep learning speed estimation, disturbance flagging, 2D dead reckoning kinematics, and temporal handover blending, significant architectural and data gaps must be resolved to fulfill the complete SIH26168 problem statement.

---

## 2. Detailed Gap Identification Matrix

| Component Area | Problem / Gap | Impact on Navigation | Corrective Technical Remediation |
| :--- | :--- | :--- | :--- |
| **Dataset & Ground-Truth** | Lack of vehicle driving dataset ($20 - 80\text{ km/h}$) with OBD2 velocity labels in `data/`. | Models trained on creeping data ($<4.3\text{ km/h}$) cannot generalize to real vehicle driving speeds. | Import IO-VNBD benchmark dataset or log physical vehicle driving sessions with OBD2 telemetry. |
| **Sampling Frequency Grid** | Paper baseline ran at 100 Hz ($T=200 = 2.0\text{s}$) instead of paper's 50 Hz ($T=200 = 4.0\text{s}$). | Sequence window duration mismatch with paper specification. | Build standalone `paper_baseline/` pipeline operating strictly at 50 Hz with $T=200$ ($4.0\text{s}$). |
| **Heading Initialization** | Dead Reckoning started from fixed $0^\circ$ North heading instead of pre-outage GNSS course over ground. | Creates artificial geometric trajectory rotation errors ($>4,000\text{m}$) on unaligned trajectories. | Initialize starting orientation $\psi_0 = \psi_{\text{GNSS}}(t_{\text{outage\_start}})$. |
| **3D State Estimation (ESKF)** | Pure kinematic integration used instead of 15-State Error-State Kalman Filter. | Unestimated accelerometer bias ($\mathbf{b}_a$) and gyro bias ($\mathbf{b}_g$) cause unbounded drift over long blackouts. | Implement 15-state ESKF ($\delta \mathbf{p}, \delta \mathbf{v}, \delta \boldsymbol{\theta}, \mathbf{b}_a, \mathbf{b}_g$) with covariance propagation. |
| **Map Matching Engine** | No OpenStreetMap (OSM) road network graph matcher integrated. | Dead-reckoned trajectory wanders off actual road geometry during extended tunnels/underpasses. | Implement Hidden Markov Model (HMM) road topology matcher on OSM road graphs. |
| **Cellular Signal Fusion** | Cell ID & RSSI logged as raw fields; no cell location prior DB attached. | Cellular signals cannot bound positioning drift radius during multi-minute outages. | Implement cell tower range bounding constraint when tower DB is available. |
| **Edge Deployment (Android)** | Android app currently logs raw CSV; deep learning model runs offline in Python. | Real-time on-device navigation is not active on physical smartphone. | Quantize PyTorch model to INT8 ONNX and integrate C++ NDK inference handler into Android app. |

---

## 3. Prioritized Action Plan & Roadmap

1. **Phase 2 (Paper Baseline Standardization)**: Build a clean, self-contained `paper_baseline/` module operating strictly at 50 Hz with 4.0s sequence windows ($T=200$) and 21-D features.
2. **Phase 3 (Realistic GNSS Outage Simulation)**: Enhance outage simulator with heading initialization fix ($\psi_0 = \psi_{\text{GNSS}}$) across 5s, 15s, 30s, 60s blackout windows.
3. **Phase 4 (Navigation Baseline Verification)**: Verify units, coordinate frames (WGS84 Lat/Lon to local ENU/NED meters), and numerical integration stability.
4. **Phase 5 (15-State ESKF Design & Implementation)**: Implement full 15-state Error-State Kalman Filter with Non-Holonomic Constraints (NHC).
5. **Phase 6 (Disturbance Threshold Calibration)**: Calibrate road bump and hard braking signal thresholds against empirical dataset recordings.
