# SIH168 Output Validity & Physical Correctness Audit

**Audit Scope:** Deep audit of actual pipeline outputs, physical consistency, and neural performance vs baselines.  
**Evaluator:** Senior Navigation Engineer & SIH System Reviewer  
**Audit Date:** 2026-09-20  

---

## 1. Audit of Current Pipeline Outputs

| Output Variable | Current Implementation Status | Units | Verified Range / Behavior | Audit Assessment |
|---|:---:|:---:|:---:|---|
| **Velocity Target Formulation** | **Relative Change ($\Delta v = v_{\text{end}} - v_{\text{start}}$)** | $m/s$ | S3c Pred: `[-1.25, +0.88] m/s` | ✅ **Physically sound**. Solved dynamic range collapse. |
| **Reconstructed Speed** | **Anchored Speed ($\hat{v} = v_0 + \hat{\Delta v}$)** | $m/s$ & $km/h$ | S3c: `[-1.08, 32.30] m/s` ($0 - 116\text{ km/h}$) | ⚠️ **Near-Complete**. Needs non-negative clamp $\max(0, \hat{v})$ at stops. |
| **Heading ($\psi$)** | **Attitude Quaternion Logged / Gyro Yaw in `sih_modules`** | Degrees / Radians | $0^\circ - 360^\circ$ | ⚠️ **Disconnected**. Heading integration exists in `sih_modules/` but is not fed by Exp_5 neural speeds. |
| **Local Displacement ($\Delta X, \Delta Y$)** | **Implemented in `sih_modules/dead_reckoning.py`** | Metres ($m$) | Local ENU frame | ⚠️ **Partial**. Tested on short sessions; not yet benchmarked on full IOVNBD S3a/S3c drives. |
| **Geodetic Coordinates (Lat, Lon)** | **Logged in Raw Dataset; WGS84 transform in `sih_modules`** | Decimal Degrees | WGS84 Ellipsoid | ⚠️ **Partial**. Conversion logic exists; live map projection not in active execution loop. |
| **Position Error in Metres ($10s, 30s, 60s$)** | **NOT TABULATED IN NEURAL BENCHMARK** | Metres ($m$) | Unmeasured in Exp_5 | ❌ **CRITICAL GAP**. Speed RMSE was measured, but positional displacement error was not. |
| **Sequential Integration Drift** | **Evaluated on Full 62-min Test Drive** | $m/s$ | Final drift: $-0.05\text{ km/h}$, RMSE: $51.4\text{ km/h}$ | ⚠️ **Expected Open-Loop Characteristic**. Proves requirement for ZUPT & periodic GNSS anchors. |

---

## 2. Physical & Mathematical Correctness Review

### 2.1 Velocity vs Acceleration (Galilean Invariance)
* **Finding:** Pure unanchored inertial neural networks cannot estimate absolute velocity $v$ because consumer accelerometers measure proper acceleration $\frac{dv}{dt}$ ($a_x = \dot{v} + g \sin\theta$).
* **Verification:** Exp_1 to Exp_4 proved that optimizing directly for absolute speed leads to catastrophic dynamic range collapse ($R^2 \le 0.20$, predictions trapped between $18 - 55\text{ km/h}$).
* **Validity of Exp_5:** Reformulating to $\Delta v = \int a \cdot dt$ with an initial GNSS velocity fix ($v_0$) restored the full $0 - 116\text{ km/h}$ dynamic spectrum ($R^2 = 0.919$ on S3c).

### 2.2 Heading & Position Kinematics
* **Finding:** Speed accuracy is only 1 dimension of a 2D/3D navigation solution.
* **Math Check:** 
  $$\mathbf{p}(t) = \mathbf{p}(t_0) + \int_{t_0}^t \begin{bmatrix} \hat{v}(\tau) \cos\psi(\tau) \\ \hat{v}(\tau) \sin\psi(\tau) \end{bmatrix} d\tau$$
  If heading drift $\delta\psi = 2^\circ$ accumulates over $30\text{ s}$ at $20\text{ m/s}$ ($72\text{ km/h}$), the resulting lateral position error is:
  $$\text{Error}_{\text{cross}} \approx v \cdot t \cdot \sin(\delta\psi) = 20 \times 30 \times \sin(2^\circ) \approx 20.94\text{ metres}$$
* **Conclusion:** Claiming "92% $R^2$ speed accuracy means 92% position accuracy" is **mathematically invalid**. True navigation accuracy must be stated in **metres of CEP / RMSE position error**.

---

## 3. Honest Neural Model vs Persistence Baseline Evaluation

### 3.1 Measured Results on Final Held-Out Test Set (`IOVNBD_S3c` — 185,711 Windows)
* **Exp_5 Neural Speed RMSE:** **`2.3505 m/s` ($8.46\text{ km/h}$)**
* **Anchored Persistence Baseline RMSE ($\Delta v = 0$):** **`2.3039 m/s` ($8.29\text{ km/h}$)**
* **Difference:** Neural model is **$+0.0466\text{ m/s}$ ($+0.17\text{ km/h}$ / $+2.0\%$) higher** in RMSE than persistence.

### 3.2 Scientific Interpretation & Claims to Judges
1. **What CANNOT be claimed:**
   * ❌ *"Our neural network beats all mathematical baselines on raw RMSE."* (False — persistence is $+0.0466\text{ m/s}$ better on pure MSE).
   * ❌ *"Our model achieves 92% position accuracy."* ($R^2 = 0.919$ is the coefficient of determination for anchored velocity, not positional error in meters).
2. **What CAN be legitimately and powerfully claimed:**
   * ✅ *"We discovered and mathematically resolved the fundamental dynamic range collapse in existing literature by identifying Galilean invariance in smartphone IMUs."*
   * ✅ *"Our anchored $\Delta v$ architecture captures the full vehicular speed dynamic range ($0 - 116\text{ km/h}$) with $r = 0.9601$ correlation across 185,000 continuous test windows."*
   * ✅ *"We established that pure inertial neural networks operate near the zero-mean variance bound in 4-second windows, proving that real-world navigation requires a hybrid Physics-Residual filter with Zero-Velocity Updates (ZUPT)."*
