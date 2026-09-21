# SIH168 Prioritized Action Plan: P0, P1, P2 Breakdown

**Project:** SIH26168 AI-ML Based Intelligent Dead Reckoning System for Seamless Navigation  
**Audit Standard:** Strict Senior Navigation Engineer Review  
**Date:** 2026-09-20  

---

## 1. Prioritized Gap Matrix

### 🔴 P0 — Required for a Technically Valid SIH Solution

| Gap Name | Why Required | Current Status | File / Module | Minimal Implementation Needed | Validation Test | Affects |
|---|---|---|---|---|---|:---:|
| **P0-1: 2D Position Propagation & Metre-Level Error Table** | Judges evaluate dead-reckoning by position drift in metres (10s, 30s, 60s), not just 1D speed RMSE. | Speed RMSE measured; position error in metres not yet benchmarked on S3a/S3c. | `sih_modules/dead_reckoning.py`, `outputs/final_test_evaluation/` | Feed Exp_5 speed predictions + heading into 2D kinematic integrator to compute $(x, y)$ displacement and metre-level error table ($10\text{s}, 30\text{s}, 60\text{s}$). | Compute Mean, 95th percentile, and Max position error in metres across 10s, 30s, 60s blackout windows. | **Position** |
| **P0-2: Zero-Velocity Update (ZUPT) & Non-Negative Clamp** | At standstill ($0\text{ km/h}$), raw integration produces negative speed ($-1.08\text{ m/s}$) and unbounded drift. | Standstill detector proposed in `disturbance.py`; not in neural loop. | `sih_modules/dead_reckoning.py`, `sih_modules/disturbance.py` | Add $\hat{v} = \max(0, \hat{v})$ physical clamp and IMU variance standstill detector ($\sigma^2(a) < \text{thresh} \implies v=0$). | Verify zero drift and 0% negative speed when vehicle is stopped for 30s. | **Velocity & Position** |
| **P0-3: Outage Simulation & Handover Benchmark Engine** | Seamless navigation requires demonstrating automatic transition into outage and smooth re-acquisition out of outage. | `sih_modules/outage_simulator.py` and `fusion_engine.py` exist in isolation. | `sih_modules/fusion_engine.py` | Connect Exp_5 speed predictions to Sigmoid handover blending ($T_{\text{blend}}=2.0\text{s}$) upon GNSS return. | Trajectory plot showing no position tele-transporting/jumping when GNSS reconnects. | **Position & Deployment** |

---

### 🟡 P1 — Important for a Convincing Prototype

| Gap Name | Why Required | Current Status | File / Module | Minimal Implementation Needed | Validation Test | Affects |
|---|---|---|---|---|---|:---:|
| **P1-1: Offline Interactive Replay & Demonstration Visualizer** | Live judging presentation needs a graphical interface showing speed, heading, GNSS status, and live route map. | Static matplotlib PNG plots only. | `scratch/live_replay_demo.py` | Lightweight interactive Python/Web visualizer with a "Cut GNSS" toggle showing live dead reckoning. | Test interactive playback on recorded drive session with live metric display. | **Deployment & Demo** |
| **P1-2: ONNX / TFLite Model Export** | Proves mobile edge feasibility ($<10\text{ms}$ latency on mobile CPU). | PyTorch `.pt` format only ($5.87\text{ MB}$). | `paper_baseline/models.py` | Convert `LSTMNoAttention` to INT8/FP32 ONNX and TFLite; measure inference time. | Verify inference latency $< 5\text{ms}$ on CPU and file size $< 1\text{ MB}$. | **Deployment** |
| **P1-3: Heading Fusion Filter (Gyro + Magnetometer / GNSS Course)** | Gyro integration alone drifts over minutes; requires fusion with magnetometer or GNSS pre-outage course. | Logged attitude quaternion used; no active filter. | `sih_modules/alignment.py` | Complementary filter fusing Gyro yaw rate with GNSS Course-Over-Ground prior to outage. | Heading error $< 3^\circ$ over 60-second outages. | **Heading** |

---

### 🟢 P2 — Future Enhancement & Advanced Features

| Gap Name | Why Required | Current Status | File / Module | Minimal Implementation Needed | Validation Test | Affects |
|---|---|---|---|---|---|:---:|
| **P2-1: 15-State Error-State Kalman Filter (ESKF)** | Full 3D strapdown inertial navigation with online accelerometer/gyro bias estimation. | 2D kinematics implemented. | `sih_modules/` | Implement 15-state covariance propagation ($\delta \mathbf{p}, \delta \mathbf{v}, \delta \boldsymbol{\theta}, \mathbf{b}_a, \mathbf{b}_g$). | Compare ESKF position drift against pure kinematic integration. | **Position & Heading** |
| **P2-2: OpenStreetMap (OSM) Graph Map-Matching** | Snaps dead-reckoned trajectory to physical road network to eliminate lateral cross-track drift. | Not implemented. | Future module | Hidden Markov Model (HMM) Viterbi map matcher. | Trajectory stays 100% on road geometry in multi-km tunnels. | **Position** |
| **P2-3: Cellular Tower RTT / Fingerprinting Bounding** | Bounds drift circle radius during extended 10+ minute catastrophic GPS blackouts. | Cell ID & RSSI logged in Android app. | `android/app/` | Cell tower location database lookup. | Bounding circle radius $< 250\text{m}$. | **Position** |

---

## 2. Recommended Next Action Selection

### Options Evaluated:
* **Option A (Read-only architecture correction):** Already completed via Stage 5 investigation and Exp_5 audit.
* **Option B (Position Propagation & Metre-Level Error Evaluation):** **RECOMMENDED PRIMARY NEXT STEP**.
* **Option C (Heading estimation and fusion):** Secondary to establishing 2D metric error baseline.
* **Option D (Physics-based velocity correction):** Valuable, but speed is already within $\sim 8\text{ km/h}$; position error in metres is the critical missing judge requirement.
* **Option E (Offline interactive replay demo):** High visual value for presentation, best paired immediately after Option B.
* **Option F (Model export and Android deployment):** Low engineering risk, but does not close the theoretical positioning gap.

---

### 🎯 **The Single Recommended Immediate Next Step:**
👉 **Option B: Position Propagation & Metre-Level Outage Error Evaluation (P0-1 + P0-2)**

**Rationale:**  
Speed RMSE ($2.35\text{ m/s}$) alone does not satisfy the SIH navigation problem statement. We must run full 2D position propagation using Exp_5 velocity + ZUPT + heading on the validated benchmark sessions, and produce the **Official Metre-Level Position Error Table for 10s, 30s, and 60s Outage Durations**. This gives judges the exact metric they demand.
