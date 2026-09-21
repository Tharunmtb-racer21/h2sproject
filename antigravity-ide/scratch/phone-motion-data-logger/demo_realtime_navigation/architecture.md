# SIH26168 Real-Time Navigation Prototype: Architecture & Technical Specification

**Project:** SIH26168 AI-ML Based Intelligent Dead Reckoning System for Seamless Navigation  
**Module:** `demo_realtime_navigation/`  
**Status:** Interactive Prototype & Navigation Dashboard  
**Date:** September 2026  

---

## 1. System Overview

The `demo_realtime_navigation/` subsystem is an interactive research prototype that demonstrates **continuous, seamless vehicle navigation under GNSS-denied environments** using the validated **Exp_5 LSTM Velocity-Delta estimation model** fused with 2D kinematic dead reckoning, Zero-Velocity Updates (ZUPT), and smooth Sigmoid handover re-acquisition.

```
[Smartphone IMU: Accel (3-axis) + Gyro (3-axis)]
                      │
                      ▼
        [Coordinate Auto-Alignment]
                      │
                      ▼
    [AI Neural Velocity-Delta Estimation (Exp_5 LSTM)]
                      │  (Δv = v_end - v_start, R² = 0.92)
                      ▼
      [2D Kinematic Dead Reckoning Engine]
          • Non-Holonomic Constraints (v_lateral = 0)
          • Non-Negative Velocity Clamping (v >= 0)
          • Zero-Velocity Updates (ZUPT Standstill Detector)
                      │
                      ▼
         [GNSS–INS Handover Engine]
          • Outage Detection (10s, 30s, 60s blackout)
          • Sigmoid Blending (T_blend = 2.0s upon recovery)
                      │
                      ▼
    [Real-Time HUD Dashboard (Local ENU Tangent Plane)]
```

---

## 2. Directory Structure

```
demo_realtime_navigation/
├── backend/
│   ├── app.py                   # Python HTTP & REST API server (port 8080)
│   ├── navigation_core.py       # 2D Kinematic Dead Reckoning (ENU Frame + ZUPT)
│   ├── outage_controller.py     # GNSS State Machine & Sigmoid Handover
│   ├── replay_engine.py         # Deterministic IO-VNBD dataset streamer (S3c, S3a, M)
│   └── sensor_receiver.py       # Live smartphone sensor ingestion stub (Next Phase)
├── static/
│   ├── index.html               # Main dashboard UI
│   ├── style.css                # Dark glassmorphic HUD styling
│   ├── app.js                   # Client-side 20Hz polling & control manager
│   ├── map_renderer.js          # 2D Local ENU Canvas trajectory visualizer
│   ├── gauge_speedometer.js     # Animated dual-needle speedometer canvas
│   └── compass_dial.js          # Rotating compass heading canvas
├── run_demo.py                  # One-click startup script
├── architecture.md              # Architecture documentation
├── verification_report.md       # Pre-flight test results
└── README.md                    # Quickstart guide
```

---

## 3. Implemented Features vs. Future Work (Honesty Matrix)

| Component | Implemented Status | Methodological Description |
|---|:---:|---|
| **Deterministic Replay Mode** | ✅ **100% Implemented** | Streams raw IMU and ECU ground truth from standardized benchmark sessions (`IOVNBD_S3c`, `IOVNBD_S3a`, `IOVNBD_M`). |
| **AI Speed Estimation** | ✅ **100% Implemented** | Uses Exp_5 LSTM Velocity-Delta formulation ($R^2 = 0.9190$, Pearson $r = 0.9601$, $\text{RMSE} = 2.35\text{ m/s}$). |
| **2D Local ENU Dead Reckoning** | ✅ **100% Implemented** | Propagates $dN = v \cos\psi dt$ and $dE = v \sin\psi dt$ in local metric tangent plane with non-negative clamping. |
| **Zero-Velocity Update (ZUPT)** | ✅ **100% Implemented** | Automatically clamps speed to $0.0\text{ m/s}$ when vehicle is stationary to prevent drift. |
| **Outage Simulation & Handover** | ✅ **100% Implemented** | One-click triggers for 10s, 30s, and 60s blackouts with Sigmoid blending ($T=2\text{s}$) upon GNSS restoration. |
| **Animated HUD Dashboard** | ✅ **100% Implemented** | Real-time Canvas map, dual-needle speedometer gauge, rotating compass dial, and telemetry feeds. |
| **Live Android Sensor Receiver** | 🟡 **Next Phase Stub** | Ingestion interface and buffer implemented; direct phone streaming to be connected in field deployment. |
| **Autonomous EKF Heading Filter** | 🟡 **Next Phase** | Currently uses logged attitude/gyro progression with pre-outage anchor; full 15-state ESKF in development. |
| **Road Map-Matching (OSM)** | 🟡 **Next Phase** | Future feature to snap coordinates to road geometry in multi-km tunnels. |

---

## 4. Validated Performance Summary

* **Held-Out Test Session (`IOVNBD_S3c` — 185k windows @ stride 1):**
  * Speed $R^2$: **$0.9190$ ($91.9\%$)**
  * Pearson Correlation: **$0.9601$**
  * Speed RMSE: **$2.3505\text{ m/s}$ ($8.46\text{ km/h}$)**
  * Speed MAE: **$1.6479\text{ m/s}$ ($5.93\text{ km/h}$)**
* **60-Second Outage Benchmark ($634\text{ m}$ travel):**
  * AI Position RMSE: **$131.27\text{ m}$**
  * Persistence Baseline RMSE: **$214.94\text{ m}$**
  * **Relative Error Reduction:** **$38.9\%$**
