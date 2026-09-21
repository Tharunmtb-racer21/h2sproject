# Strict Production-Path Validation & Audit Report

**System:** SIH26168 AI-ML Based Intelligent Dead Reckoning System  
**Audit Date:** 2026-09-21  
**Evaluated Session:** `IOVNBD_S3c` (37,183 samples @ 10 Hz)  
**Trained Model Checkpoint:** `outputs/Exp_5_LSTMNoAttention_DeltaV/best_model.pt`  
**Operating Mode Under Audit:** Simulated Continuous & Timed GNSS Outages (10s, 30s, 60s, 120s)  

---

## A. Production Path

Tracing the exact live execution path when a GNSS Outage is triggered:

```
[Continuous Outage Button (Canvas UI)]
                 │
                 ▼
[POST /api/outage/trigger (backend/app.py:174-180)]
                 │
                 ▼
[ReplayEngine.trigger_simulated_outage (backend/replay_engine.py:358-369)]
                 │
                 ▼
[OutageController.trigger_outage (backend/outage_controller.py:46-68)]
                 │  (Captures anchor speed v_anchor, position E0, N0, time t0)
                 ▼
[Playback Loop Tick (backend/app.py:41-49)]
                 │
                 ▼
[ReplayEngine.step() -> process_current_frame() (backend/replay_engine.py:214-353)]
                 │
                 ├──> [ReplayEngine.infer_neural_delta_v() (backend/replay_engine.py:149-179)]
                 │        └── PyTorch Model Forward Pass on 200-sample window
                 │
                 ├──> [Velocity Reconstruction: v = max(0, v_anchor + pred_delta_v) (line 267-268)]
                 │
                 ├──> [NavigationCore.update_heading(gyro_z, dt=0.1) (backend/navigation_core.py:39-44)]
                 │        └── Gyro integration: heading_rad += gyro_z * dt
                 │
                 └──> [NavigationCore.propagate_step() (backend/navigation_core.py:51-109)]
                          ├── dNorth = v * cos(heading_rad) * dt
                          └── dEast  = v * sin(heading_rad) * dt
```

* **Exact Source Files & Functions:**
  1. UI Trigger: `demo_realtime_navigation/static/index.html` & `app.js` $\to$ `fetch('/api/outage/trigger')`
  2. API Endpoint: `demo_realtime_navigation/backend/app.py` (`NavigationRequestHandler.do_POST:L174-L180`)
  3. Controller: `demo_realtime_navigation/backend/outage_controller.py` (`OutageController.trigger_outage:L46-L68`)
  4. Playback / Streamer: `demo_realtime_navigation/backend/replay_engine.py` (`ReplayEngine.process_current_frame:L214-L353`)
  5. Neural Inference: `demo_realtime_navigation/backend/replay_engine.py` (`ReplayEngine.infer_neural_delta_v:L149-L179`)
  6. Heading Integration: `demo_realtime_navigation/backend/navigation_core.py` (`NavigationCore.update_heading:L39-L44`)
  7. Position Integration: `demo_realtime_navigation/backend/navigation_core.py` (`NavigationCore.propagate_step:L51-L109`)

---

## B. Exp_5 Target Definition

* **Source Code Reference:** `outputs/validation_performance/exp5_readonly_design.md:L20-L23`, `outputs/Exp_5_LSTMNoAttention_DeltaV/exp5_final_report.md:L18-L20`
* **Target Formulation:**
  $$\Delta v(t) = v(t) - v(t - T \cdot dt)$$
* **Parameters:**
  * Window Horizon ($T$): 200 samples ($4.0\text{ s}$ @ $50\text{ Hz}$ or $20.0\text{ s}$ @ $10\text{ Hz}$)
  * Source Target Variable: `reference_speed` (CAN/VBOX ground truth speed in $\text{m/s}$)
  * Output Units: $\text{m/s}$ (velocity increment over the 200-sample window)
  * Target Standardization:
    $$y_{\text{norm}} = \frac{\Delta v - \mu_{\Delta v}}{\sigma_{\Delta v}}$$
    $$\mu_{\Delta v} = 0.001914217\text{ m/s}, \quad \sigma_{\Delta v} = 2.4407406\text{ m/s}$$
* **Mathematical Semantic:** The network predicts the **velocity difference** across the temporal window, not absolute speed or instantaneous acceleration.

---

## C. Velocity Reconstruction

* **Reconstruction Formula:**
  $$v_{\text{reconstructed}}(t) = \max\left(0, v_{\text{anchor}} + \widehat{\Delta v}(t)\right)$$
  Where:
  * $v_{\text{anchor}} = v(t_{\text{outage}})$ is the velocity state immediately preceding GNSS loss.
  * $\widehat{\Delta v}(t) = \widehat{y}_{\text{norm}}(t) \cdot \sigma_{\Delta v} + \mu_{\Delta v}$.
* **Mathematical Validity:**
  * For $t \in [t_0, t_0 + T]$, $\widehat{\Delta v}(t)$ reflects change relative to the initial anchor window.
  * For $t > t_0 + T$ (e.g. 60s, 120s outages), the sliding window spans $[t - T, t]$. Because unassisted dead reckoning does not have true velocity fixes at $t - T$, using fixed $v_{\text{anchor}}$ causes the velocity prediction to wander if the vehicle permanently changes speed band (e.g., stops at an intersection).

---

## D. Heading Pipeline

* **Equations:**
  $$\psi(t + dt) = \psi(t) + \omega_z(t) \cdot dt$$
  $$\psi(t) \in [-\pi, \pi]$$
* **Gyroscope Units:** Radians per second ($\text{rad/s}$) in `IOVNBD_S3c` (range $[-0.3346, +0.1688]\text{ rad/s}$, mean bias $-0.00063\text{ rad/s}$).
* **Conversion Factor:** Direct integration with $dt = 0.1\text{ s}$.
* **Initial Heading Source:** `reference_heading` at $t = t_0$ (last valid GNSS heading fix before outage).
* **Ground-Truth Heading Leakage Audit:** **ZERO LEAKAGE**. During outage ($t > t_0$), heading is updated purely via `gyro_z` angular rate integration in `NavigationCore.update_heading`. Reference heading is never passed to `NavigationCore` during outage.

---

## E. Position Integration

* **Kinematic Equations:**
  $$dN = v_{\text{forward}} \cdot \cos(\psi) \cdot dt$$
  $$dE = v_{\text{forward}} \cdot \sin(\psi) \cdot dt$$
* **Coordinate Convention:** Local East-North-Up (ENU) tangent plane.
  * Heading $\psi = 0^\circ$: True North ($+N$).
  * Heading $\psi = 90^\circ$: True East ($+E$).
  * Clockwise positive.
* **Synthetic Sanity Verification:**
  1. Heading $0^\circ$, speed $10.0\text{ m/s}$, $dt=1.0\text{ s}$:
     * Output: $dN = 10.0\text{ m}$, $dE = 0.0\text{ m}$ $\implies$ **PASS**
  2. Heading $90^\circ$, speed $10.0\text{ m/s}$, $dt=1.0\text{ s}$:
     * Output: $dN = 0.0\text{ m}$, $dE = 10.0\text{ m}$ $\implies$ **PASS**

---

## F. Timing & Sampling Rates

| Pipeline Stage | Nominal Rate | Empirical $dt$ | Rate Alignment Check |
|---|:---:|:---:|:---:|
| `IOVNBD_S3c_standardized.csv` | $10\text{ Hz}$ | $0.1000\text{ s}$ ($\mu = 0.099999\text{ s}$) | Aligned |
| Feature Extraction Window | $200\text{ steps}$ | $20.0\text{ s}$ | Note: Exp_5 trained on 50Hz raw resampled (4.0s) |
| Live Replay Engine Tick | $10\text{ Hz}$ | $dt = 0.1\text{ s}$ | Aligned |
| Gyroscope Integration Rate | $10\text{ Hz}$ | $dt = 0.1\text{ s}$ | Aligned |
| 2D Position Propagate Rate | $10\text{ Hz}$ | $dt = 0.1\text{ s}$ | Aligned |

---

## G. Feature & Scaler Compatibility

* **Training Scaler:** `PaperMinMaxScaler` was fitted on training sessions (`IOVNBD_M`, `S1`, `S2`) across all 21 features with range $[0.0, 1.0]$.
* **Live Deployment Audit:**
  * In `replay_engine.py:L114`, `self.features_matrix` was extracted using `extract_paper_features()`, but `PaperMinMaxScaler.transform()` was **NOT CALLED**.
  * **Empirical Verification:**
    * Neural output on raw unscaled window: $\widehat{y} = +0.1051 \implies \Delta v = +0.2585\text{ m/s}$.
    * Neural output on scaled window: $\widehat{y} = -0.2677 \implies \Delta v = -0.6515\text{ m/s}$ (matches ground-truth checkpoint validation value $-0.651492$ to 7 decimal places).
  * **Finding:** Missing input normalization in production causes the neural model to receive out-of-distribution feature values.

---

## H. Ground-Truth Leakage Audit

| Variable | Pre-Outage ($t \le t_0$) | During Outage ($t > t_0$) | Leakage Status |
|---|:---:|:---:|:---:|
| `reference_speed` | Used for GNSS locked display | **NEVER PASSED** to navigation state | **PASS (No Leakage)** |
| `reference_heading` | Used to anchor initial $\psi_0$ | **NEVER PASSED** to navigation state | **PASS (No Leakage)** |
| `latitude` / `longitude` | Used to anchor initial $(E_0, N_0)$ | **NEVER PASSED** to navigation state | **PASS (No Leakage)** |
| `ref_east_m` / `ref_north_m` | Used for canvas reference polyline | **NEVER PASSED** to dead reckoning | **PASS (No Leakage)** |

* **Audit Result:** Navigation propagation during outage is strictly isolated from reference ground-truth data.

---

## I. Strict A/B/C/D Evaluation Results

Evaluated on `IOVNBD_S3c` starting at index 100 ($t=10.0\text{s}$):

### A. Real Production Pipeline (AI Velocity [Deployed Unscaled] + IMU Gyro Heading)
*No reference data in navigation state.*

| Outage Duration | Ref Distance | Est Distance | Final Pos Error | Max Pos Error | Vel MAE | Vel RMSE | Hdg MAE | Hdg RMSE | Final Hdg Error |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **10 s** | $81.18\text{ m}$ | $96.72\text{ m}$ | **$23.44\text{ m}$** | $76.36\text{ m}$ | $1.59\text{ m/s}$ | $1.86\text{ m/s}$ | $3.77^\circ$ | $4.56^\circ$ | $11.15^\circ$ |
| **30 s** | $104.65\text{ m}$ | $302.58\text{ m}$ | **$192.87\text{ m}$** | $192.87\text{ m}$ | $6.61\text{ m/s}$ | $7.77\text{ m/s}$ | $10.24^\circ$ | $11.41^\circ$ | $9.74^\circ$ |
| **60 s** | $171.48\text{ m}$ | $615.21\text{ m}$ | **$492.09\text{ m}$** | $492.09\text{ m}$ | $7.54\text{ m/s}$ | $8.46\text{ m/s}$ | $15.69^\circ$ | $24.63^\circ$ | $73.28^\circ$ |
| **120 s** | $705.08\text{ m}$ | $1222.13\text{ m}$ | **$1028.67\text{ m}$** | $1028.67\text{ m}$ | $6.04\text{ m/s}$ | $7.11\text{ m/s}$ | $37.93^\circ$ | $53.68^\circ$ | $117.61^\circ$ |

---

### B. Diagnostic: AI Velocity + Reference Heading
*Isolates velocity estimation error from gyro heading error.*

| Outage Duration | Ref Distance | Est Distance | Final Pos Error | Max Pos Error | Vel MAE | Vel RMSE | Hdg MAE | Hdg RMSE | Final Hdg Error |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **10 s** | $81.18\text{ m}$ | $96.72\text{ m}$ | **$23.58\text{ m}$** | $76.33\text{ m}$ | $1.59\text{ m/s}$ | $1.86\text{ m/s}$ | $0.89^\circ$ | $1.16^\circ$ | $0.75^\circ$ |
| **30 s** | $104.65\text{ m}$ | $302.58\text{ m}$ | **$192.77\text{ m}$** | $192.77\text{ m}$ | $6.61\text{ m/s}$ | $7.77\text{ m/s}$ | $0.44^\circ$ | $0.82^\circ$ | $0.00^\circ$ |
| **60 s** | $171.48\text{ m}$ | $615.21\text{ m}$ | **$448.71\text{ m}$** | $448.71\text{ m}$ | $7.54\text{ m/s}$ | $8.46\text{ m/s}$ | $0.62^\circ$ | $1.24^\circ$ | $0.32^\circ$ |
| **120 s** | $705.08\text{ m}$ | $1222.13\text{ m}$ | **$570.90\text{ m}$** | $621.32\text{ m}$ | $6.04\text{ m/s}$ | $7.11\text{ m/s}$ | $0.66^\circ$ | $1.21^\circ$ | $1.07^\circ$ |

---

### C. Diagnostic: Reference Speed + IMU Gyro Heading
*Isolates gyro heading integration drift under perfect ground-truth speed.*

| Outage Duration | Ref Distance | Est Distance | Final Pos Error | Max Pos Error | Vel MAE | Vel RMSE | Hdg MAE | Hdg RMSE | Final Hdg Error |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **10 s** | $81.18\text{ m}$ | $81.18\text{ m}$ | **$7.99\text{ m}$** | $63.13\text{ m}$ | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | $3.77^\circ$ | $4.56^\circ$ | $11.15^\circ$ |
| **30 s** | $104.65\text{ m}$ | $104.65\text{ m}$ | **$9.23\text{ m}$** | $63.13\text{ m}$ | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | $10.24^\circ$ | $11.41^\circ$ | $9.74^\circ$ |
| **60 s** | $171.48\text{ m}$ | $171.48\text{ m}$ | **$48.60\text{ m}$** | $63.13\text{ m}$ | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | $15.69^\circ$ | $24.63^\circ$ | $73.28^\circ$ |
| **120 s** | $705.08\text{ m}$ | $705.08\text{ m}$ | **$619.15\text{ m}$** | $619.15\text{ m}$ | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | $37.93^\circ$ | $53.68^\circ$ | $117.61^\circ$ |

---

### D. Oracle Diagnostic: Reference Speed + Reference Heading
*Upper bound kinematic integration baseline.*

| Outage Duration | Ref Distance | Est Distance | Final Pos Error | Max Pos Error | Vel MAE | Vel RMSE | Hdg MAE | Hdg RMSE | Final Hdg Error |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **10 s** | $81.18\text{ m}$ | $81.18\text{ m}$ | **$8.53\text{ m}$** | $63.11\text{ m}$ | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | $0.89^\circ$ | $1.16^\circ$ | $0.75^\circ$ |
| **30 s** | $104.65\text{ m}$ | $104.65\text{ m}$ | **$6.62\text{ m}$** | $63.11\text{ m}$ | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | $0.44^\circ$ | $0.82^\circ$ | $0.00^\circ$ |
| **60 s** | $171.48\text{ m}$ | $171.48\text{ m}$ | **$49.64\text{ m}$** | $63.11\text{ m}$ | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | $0.62^\circ$ | $1.24^\circ$ | $0.32^\circ$ |
| **120 s** | $705.08\text{ m}$ | $705.08\text{ m}$ | **$39.11\text{ m}$** | $120.68\text{ m}$ | $0.00\text{ m/s}$ | $0.00\text{ m/s}$ | $0.66^\circ$ | $1.21^\circ$ | $1.07^\circ$ |

---

## J. 3D Alignment & Scaler Ablation Analysis

Evaluating each enhancement sequentially on the Real Production Pipeline (Mode A):

| Configuration | 10s Pos Error | 30s Pos Error | 60s Pos Error | 120s Pos Error | 120s Vel RMSE |
|---|:---:|:---:|:---:|:---:|:---:|
| **1. Baseline (Deployed Unscaled)** | $23.44\text{ m}$ | $192.87\text{ m}$ | $492.09\text{ m}$ | $1028.67\text{ m}$ | $7.11\text{ m/s}$ |
| **2. Baseline + Scaler Correction** | $21.27\text{ m}$ | $175.04\text{ m}$ | $441.87\text{ m}$ | $959.55\text{ m}$ | $6.60\text{ m/s}$ |
| **3. Baseline + Scaler + ZUPT** | $21.27\text{ m}$ | $175.04\text{ m}$ | $441.87\text{ m}$ | $959.55\text{ m}$ | $6.60\text{ m/s}$ |
| **4. Baseline + Scaler + Damping** | $20.99\text{ m}$ | $174.25\text{ m}$ | $440.69\text{ m}$ | $956.23\text{ m}$ | $6.59\text{ m/s}$ |
| **5. Baseline + Scaler + ZUPT + Damping** | $20.99\text{ m}$ | $174.25\text{ m}$ | $440.69\text{ m}$ | $956.23\text{ m}$ | $6.59\text{ m/s}$ |

---

## K. ZUPT Validation

* **Inspected Code:**
  ```python
  accel_var = float((accel_x**2 + accel_y**2 + (accel_z - 9.81)**2))
  if accel_var < 0.02 and v_reconstructed < 0.3:
      v_reconstructed = 0.0
  ```
* **Physical Meaning:**
  * This is the **squared Euclidean norm of the residual acceleration vector** assuming an ideal vertical gravity vector $(0, 0, 9.81)\text{ m/s}^2$.
  * It is **NOT** a sample variance $\text{Var}(a) = \frac{1}{N}\sum(a_i - \bar{a})^2$ over a temporal window.
* **Units:** $\text{m}^2/\text{s}^4$.
* **Threshold Assessment:**
  * Threshold $0.02\text{ m}^2/\text{s}^4$ corresponds to a net acceleration deviation $\|\mathbf{a} - \mathbf{g}\| < \sqrt{0.02} \approx 0.141\text{ m/s}^2$.
  * If the phone is tilted (e.g. pitched $10^\circ$ on a dashboard mount), gravity leaks into $a_x$ ($g \sin 10^\circ \approx 1.70\text{ m/s}^2$), causing the metric to register $\approx 2.9\text{ m}^2/\text{s}^4 \gg 0.02$, so the condition **never triggers during a true standstill**.
* **Verdict:** The current implementation is an instantaneous gravity residual check and does not qualify as a robust rolling-window ZUPT standstill detector.

---

## L. Deceleration Damping Validation

* **Inspected Logic:** Limiting speed reduction when forward accelerometer indicates braking ($a_x < 0$).
* **Measured Effect:** Provides a minor error reduction ($1028.67\text{ m} \to 956.23\text{ m}$ at 120s), but cannot correct large-scale heading drift or speed band transitions.

---

## M. Root Cause of Error

1. **Missing Input Normalization in Production:** `replay_engine.py` passes unscaled raw sensor values into the PyTorch network, whereas `best_model.pt` was trained on MinMax scaled inputs $[0, 1]$.
2. **Gyroscope Bias Accumulation:** Gyro $z$-axis has an uncalibrated bias ($\approx -0.00063\text{ rad/s}$ plus dynamic drift), accumulating $117.61^\circ$ heading error over 120s. Mode C proves that even with ground-truth velocity, heading drift alone produces $619.15\text{ m}$ position error.
3. **Fixed Anchor Speed Horizon:** $v_{\text{reconstructed}} = v_{\text{anchor}} + \Delta v$ anchors to $v(t_0)$. When an outage exceeds 30–60s and the vehicle changes driving state (e.g. decelerates to a halt), anchoring to the pre-outage speed causes a persistent positive velocity offset.

---

## N. Recommended Fixes

1. **Apply Scaler in Replay Engine:** Load `PaperMinMaxScaler` parameters and normalize sliding window features before model inference.
2. **Online Gyroscope Bias Estimation:** Estimate stationary gyro bias during GNSS-locked periods and subtract it during outage integration.
3. **Multi-Horizon Speed Blending:** Transition velocity estimation from pre-outage anchor to dynamic inertial integration for outages $> 30\text{s}$.
4. **Windowed Rolling-Variance ZUPT:** Replace instantaneous gravity residual with a true 1.0s sliding variance across total acceleration magnitude $\sigma^2(\|\mathbf{a}\|) < 0.01\text{ m}^2/\text{s}^4$.

---

## O. Final Status

**BUG FOUND**

* **Summary of Identified Bugs:**
  1. Input feature scaling was omitted in the live inference pipeline (`backend/replay_engine.py:L114`).
  2. Standstill detector uses instantaneous gravity difference rather than rolling statistical variance, failing when the smartphone is mounted at an angle.
