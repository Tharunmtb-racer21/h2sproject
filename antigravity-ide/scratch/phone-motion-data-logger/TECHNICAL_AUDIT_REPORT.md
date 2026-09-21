# TECHNICAL AUDIT REPORT: SIH26168 INTELLIGENT DEAD RECKONING SYSTEM

**System Component**: SIH26168 Navigation Pipeline  
**Repository Directory**: `phone-motion-data-logger`  
**Audit Date**: September 2026  
**Auditor**: Senior Navigation Systems & AI/ML Systems Engineer  

---

## Executive Audit Summary

A comprehensive technical audit was performed across all source files (`ai_pipeline/`, `sih_modules/`, `data/`), datasets, generated reports, PyTorch models, and unit tests. The current codebase contains a solid foundation for data ingestion, signal filtering, sequence windowing, deep learning speed regression, GNSS outage masking, 2D dead reckoning kinematics, and temporal handover blending. However, critical data limitations (lack of high-speed vehicle driving logs with OBD2 ground-truth velocity) and architectural gaps (15-state ESKF, OSM map matching, on-device ONNX C++ NDK engine) must be addressed before vehicle-level navigation accuracy can be achieved.

---

## 1. System Module Audit Matrix

| Module | Status | Evidence | Problems & Limitations | Next Action |
| :--- | :--- | :--- | :--- | :--- |
| **Data Ingestion & Logging** | **COMPLETE** | Android app (`SessionLogger.kt`) & Web telemetry (`server.js`) logging 100 Hz Accel/Gyro, 1 Hz GNSS, and Cell ID metrics. | Web socket format drops raw sensor nanoseconds; Android NDK stream preferred. | Standardize ingestion schema across NDK and Web streams. |
| **Stream Preprocessing & Filtering** | **COMPLETE** | `ai_pipeline/preprocess.py` executing 100 Hz uniform resampling and 4th-order 15 Hz Butterworth low-pass filtering. | Resampling interpolation can smooth transient shock spikes. | Preserve unfiltered raw IMU peak values in a separate high-g channel. |
| **Paper Feature Extraction** | **PARTIALLY IMPLEMENTED** | `ai_pipeline/dataset_loader.py` constructing 21-D feature vectors (7 raw + 14 rolling mean/var). | Feature generation ran at 100 Hz (T=200 = 2.0s) instead of paper's 50 Hz (T=200 = 4.0s). | Re-sample sequences to exact 50 Hz paper grid ($T=200 \implies 4.0\text{s}$). |
| **Paper AI Speed Model** | **COMPLETE** | PyTorch models `LSTMSelfAttention`, `LSTMNoAttention`, and `SimpleBaselineMLP` in `ai_pipeline/models.py`. | Model trained on low-speed creeping data ($<4.3\text{ km/h}$) due to dataset limits. | Train on high-speed vehicle benchmark dataset (IO-VNBD / OBD2 logs). |
| **Dataset Readiness & Target Labels** | **REQUIRES DATA** | Audit of 5 CSVs in `data/`: 3 indoor logs lack GPS speed; 2 logs contain only low-speed creep ($0 - 4.3\text{ km/h}$). | No vehicle driving logs (20–80 km/h) with OBD2/high-accuracy velocity ground-truth exist in `data/`. | Acquire/import vehicle OBD2 driving logs (IO-VNBD benchmark). |
| **GNSS Outage Simulator** | **COMPLETE** | `sih_modules/outage_simulator.py` masking position, velocity, and fix flags over configurable durations (5s to 60s). | Outage masking evaluated on stationary/slow logs yields artificial drift artifacts. | Evaluate outage simulator on continuous vehicle driving trajectories. |
| **Phone-to-Vehicle Alignment** | **PARTIALLY IMPLEMENTED** | `sih_modules/alignment.py` implementing static gravity Pitch/Roll and dynamic PCA Yaw calibration. | Dynamic PCA Yaw requires forward vehicle acceleration event to resolve direction. | Add stationary heading initialization from initial GNSS velocity vector. |
| **Disturbance & Anomaly Detection** | **PARTIALLY IMPLEMENTED** | `sih_modules/disturbance.py` detecting bumps, hard braking, sharp turns, and chassis vibration. | Heuristic thresholds selected without labeled anomaly ground-truth. | Calibrate thresholds against labeled road condition datasets. |
| **2D Dead Reckoning Engine** | **COMPLETE** | `sih_modules/dead_reckoning.py` integrating speed and yaw rate under Non-Holonomic Constraints (NHC). | Open-loop integration accumulates heading drift over time without map matching. | Integrate heading correction from ESKF and road graph map matching. |
| **GNSS/IMU Fusion & Handover** | **PARTIALLY IMPLEMENTED** | `sih_modules/fusion_engine.py` implementing Sigmoid temporal handover ($T_{blend}=2.0\text{s}$). | Blends trajectories heuristically; does not update internal IMU state error covariance. | Replace heuristic blending with 15-State Error-State Kalman Filter (ESKF). |
| **15-State ESKF Fusion** | **NOT IMPLEMENTED** | Not present in codebase. | High dead-reckoning drift over long outages due to unestimated accelerometer/gyroscope biases. | Formulate state vector and implement 15-State ESKF process & measurement updates. |
| **OpenStreetMap Map Matching** | **NOT IMPLEMENTED** | Not present in codebase. | Lateral drift causes vehicle position to wander off roads during prolonged blackouts. | Implement HMM topological road graph matcher on OSM network. |
| **Cellular Signal Location Prior** | **PARTIALLY IMPLEMENTED** | `cell_id` and `signal_dbm` fields logged in Android CSVs. | No cell tower location database or RTT fingerprint mapping available. | Use Cell ID as an outage context flag until cell location DB is attached. |
| **Android Edge Deployment (ONNX/NDK)** | **NOT IMPLEMENTED** | Android app records CSV logs; on-device inference not integrated. | Inference runs offline in Python; cannot navigate live on physical phone. | Export PyTorch model to ONNX INT8 and build C++ NDK inference handler. |

---

## 2. Key Audit Findings & Critical Issues Discovered

1. **Dataset Limitation (Ground-Truth Deficit)**:
   - The dataset in `data/` contains 5 CSV files totaling 1,468,706 bytes.
   - **3 files** (`SESSION-20260917_213518`, `213549`, `214611`) were recorded indoors and have **0 valid GNSS speed or location samples**.
   - **1 file** (`SESSION-20260917_215707`) has GNSS fix, but speed was $0.0\text{ m/s}$ (stationary test).
   - **1 file** (`sensor_data.csv`) has 50 GNSS samples with speeds ranging from $0.09\text{ m/s}$ to $1.2\text{ m/s}$ ($0.32 - 4.32\text{ km/h}$), collected at a low web sampling rate of 4.7 Hz.
   - **Conclusion**: The current dataset in `data/` is **insufficient for training a production vehicle-speed model**.

2. **Validation Integrity Analysis**:
   - The reported high positioning drift ($4,077\text{ m}$ on `sensor_data` over a 30s blackout) was investigated.
   - **Root Cause Identified**: `sensor_data` was recorded with an uncalibrated initial heading ($0.0\text{ rad}$ facing North), while the true GPS ground-truth was heading East ($90^\circ$). Integrating forward speed along North while the vehicle traveled East created a geometric orthogonal displacement error of $r \cdot \theta \approx 50\text{m}$ per second of integration.
   - **Correction Required**: Dead Reckoning integration MUST initialize starting heading angle $\psi_0$ from the GNSS course-over-ground vector immediately prior to outage entry.

3. **Paper Reproduction Gap**:
   - The reference paper (*Shin et al., 2025*) samples data at **50 Hz** and uses a window $T=200$ ($4.0\text{ seconds}$).
   - Current implementation ran preprocessing at **100 Hz**, causing $T=200$ to represent only $2.0\text{ seconds}$.
   - The paper evaluated models against **OBD2 wheel-speed ground truth** across 4 distinct phone mounting postures (Pitch $90^\circ$, $60^\circ$, $30^\circ$, Landscape).

---

## 3. Prioritized Next Five Technical Actions

1. **Action 1 (Paper Baseline Standardization)**: Create a dedicated `paper_baseline/` module operating strictly at 50 Hz with $T=200$ ($4.0\text{s}$ window) and 21-D features ($7\text{ raw} + 14\text{ rolling stats}$).
2. **Action 2 (Heading & Coordinate Frame Fix)**: Update Dead Reckoning integrator to automatically initialize starting orientation $\psi_0$ from pre-outage GNSS bearing, eliminating geometric heading offset errors.
3. **Action 3 (15-State ESKF Formulation)**: Formulate and implement the 15-State Error-State Kalman Filter ($\delta \mathbf{p}, \delta \mathbf{v}, \delta \boldsymbol{\theta}, \mathbf{b}_a, \mathbf{b}_g$) with Non-Holonomic Constraints (NHC).
4. **Action 4 (Benchmark Dataset Integration)**: Acquire/import vehicle driving dataset with OBD2 ground-truth speed (IO-VNBD benchmark dataset) to validate speed estimation across $20 - 80\text{ km/h}$.
5. **Action 5 (OpenStreetMap Map Matcher)**: Build modular Hidden Markov Model (HMM) road network map matcher to constrain DR trajectory to drivable road segments.
