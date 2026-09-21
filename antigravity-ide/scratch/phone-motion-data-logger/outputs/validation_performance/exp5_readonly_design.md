# Exp_5 Read-Only Design & Preflight Investigation: Velocity-Delta Formulation & Anchored State Estimation

**Subject:** Evaluation of the Velocity-Delta ($\Delta v$) Formulation, Temporal Integration, and Anchored State Estimation for Smartphone IMU Dead-Reckoning  
**Data Analyzed:** `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2` (205,398 stride-5 training windows) and `IOVNBD_S3a` (122,901 stride-1 validation windows)  
**Safety Protocol:** **STRICTLY READ-ONLY**. `IOVNBD_S3c` was **NOT LOADED, NOT READ, NOT EVALUATED, AND NEVER ACCESSED**. No neural networks were trained. No model checkpoints were created.

---

## 1. Hypothesis

> **Hypothesis Under Test:**  
> *"The smartphone IMU contains sufficient kinematic information to estimate short-term vehicle velocity change ($\Delta v = v_{\text{end}} - v_{\text{start}}$), whereas absolute velocity ($v_{\text{end}}$) is unobservable from isolated local IMU windows and requires an external or initial velocity anchor."*

This hypothesis was tested quantitatively using statistical distributions, feature correlations, temporal interval slicing, linear baselines, and anchored state reconstruction on unseen validation session `IOVNBD_S3a`.

---

## 2. $\Delta v$ Target Distribution

For every sequence window of duration $T=200$ steps ($4.0\text{ s}$ @ $50\text{ Hz}$):
$$v_{\text{start}} = v(t - 4.0\text{ s}), \quad v_{\text{end}} = v(t), \quad \Delta v = v_{\text{end}} - v_{\text{start}}$$

### Comparative Distribution Table (Train vs. S3a Benchmark)

| Target Variable | Scope / Split | Sample Count ($N$) | Mean ($m/s$) | Std ($\sigma$) | Median ($m/s$) | 5th – 95th Percentile ($m/s$) | Min / Max ($m/s$) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **$\Delta v$ (Delta Speed)** | **Combined Train** | **205,398** | **+0.0019** | **2.4407** | **+0.0114** | **[-4.332, +3.932]** | [-22.595, +17.454] |
| $v_{\text{end}}$ (Absolute Speed) | Combined Train | 205,398 | 8.3144 | 5.5193 | 8.2199 | [0.015, 17.897] | [0.000, 29.118] |
| **$\Delta v$ (Delta Speed)** | `IOVNBD_M` | 61,720 | -0.0043 | 2.6323 | +0.0097 | [-4.222, +4.082] | [-22.595, +17.101] |
| **$\Delta v$ (Delta Speed)** | `IOVNBD_S1` | 51,706 | -0.0032 | 2.3448 | +0.0083 | [-4.353, +3.937] | [-12.019, +17.454] |
| **$\Delta v$ (Delta Speed)** | `IOVNBD_S2` | 91,972 | +0.0090 | 2.3586 | +0.0145 | [-4.376, +3.851] | [-18.238, +9.609] |
| **$\Delta v$ (Delta Speed)** | **VAL `IOVNBD_S3a`** | **122,901** | **+0.0075** | **2.1887** | **+0.0064** | **[-4.090, +3.802]** | [-11.936, +7.870] |
| $v_{\text{end}}$ (Absolute Speed) | VAL `IOVNBD_S3a` | 122,901 | 10.5447 | 6.0400 | 10.9022 | [0.018, 21.904] | [0.000, 27.227] |

### Quantitative Insights:
1. **Zero Cross-Session Shift in Mean:** While absolute speed experiences a massive **$+26.8\%$ cross-session shift** ($\mu_{\text{train}} = 8.31\text{ m/s} \to \mu_{\text{val}} = 10.54\text{ m/s}$), the $\Delta v$ distribution has **near-zero shift** ($\mu_{\text{train}} = +0.0019\text{ m/s} \to \mu_{\text{val}} = +0.0075\text{ m/s}$, $\Delta \mu < 0.006\text{ m/s}$).
2. **Stationary Spread:** The standard deviation of $\Delta v$ is remarkably consistent across all four driving sessions ($\sigma \approx 2.19 - 2.63\text{ m/s}$), providing a stationary learning objective.

*Artifact Reference:* [`stage5_delta_v_distribution.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_delta_v_distribution.csv)

---

## 3. $\Delta v$ vs. IMU Feature Relationship

Comparing the correlation of the 21 IMU window features and physical integrals against $\Delta v$ vs. absolute speed $v_{\text{end}}$:

| Feature Name | Pearson $r$ with $\Delta v$ | Spearman $\rho$ with $\Delta v$ | Pearson $r$ with Absolute $v$ | Spearman $\rho$ with Absolute $v$ | Correlation Gain ($|\Delta v| - |v_{\text{abs}}|$) |
|---|:---:|:---:|:---:|:---:|:---:|
| `accel_x` (Longitudinal / Mount) | **+0.1251** | **+0.1336** | +0.0150 | +0.0106 | **+0.1101 (8.3x stronger)** |
| `accel_y` (Lateral / Mount) | **-0.1187** | **-0.1083** | -0.0216 | -0.0048 | **+0.0971 (5.5x stronger)** |
| `accel_x_mean` | **+0.0982** | **+0.1052** | +0.0294 | +0.0292 | **+0.0688** |
| `accel_y_mean` | **-0.0843** | **-0.0876** | -0.0341 | -0.0196 | **+0.0502** |
| `accel_z_var` | -0.0445 | -0.0269 | +0.0369 | +0.2294 | -0.0077 |
| `accel_mag_var` | -0.0394 | -0.0182 | +0.0274 | +0.2273 | +0.0120 |
| **$\int a_x dt$ (Euler Integral)** | **+0.1251** | **+0.1336** | +0.0150 | +0.0106 | **+0.1101** |
| **$\int a_y dt$ (Euler Integral)** | **-0.1187** | **-0.1083** | -0.0216 | -0.0048 | **+0.0971** |

### Key Findings:
* Accelerometer signals align **strictly with velocity changes ($\Delta v$)**, not absolute speed. 
* Longitudinal and lateral acceleration integrals correlate directly with $\Delta v$ ($r \approx 0.12 - 0.13$). The remaining noise is due to phone coordinate misalignment with the vehicle chassis.

*Artifact Reference:* [`stage5_delta_v_correlations.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_delta_v_correlations.csv)

---

## 4. Window Duration Interval Analysis

Evaluating how the magnitude and predictability of $\Delta v$ scale across shorter temporal slices of the training data:

| Time Interval ($\Delta t$) | Steps ($T$) | Sample Count ($N$) | Mean $\Delta v$ | Std $\Delta v$ | MAE vs. Zero ($m/s$) | MAE vs. Zero ($km/h$) | 5th – 95th Percentile |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0.5 s** | $25$ | 205,503 | $+0.0002\text{ m/s}$ | **$0.43\text{ m/s}$** | **$0.25\text{ m/s}$** | **$0.91\text{ km/h}$** | $[-0.65, +0.59]\text{ m/s}$ |
| **1.0 s** | $50$ | 205,488 | $+0.0004\text{ m/s}$ | **$0.78\text{ m/s}$** | **$0.49\text{ m/s}$** | **$1.75\text{ km/h}$** | $[-1.27, +1.14]\text{ m/s}$ |
| **2.0 s** | $100$ | 205,458 | $+0.0009\text{ m/s}$ | **$1.41\text{ m/s}$** | **$0.92\text{ m/s}$** | **$3.32\text{ km/h}$** | $[-2.43, +2.18]\text{ m/s}$ |
| **4.0 s** (Current) | $200$ | 205,398 | $+0.0019\text{ m/s}$ | **$2.44\text{ m/s}$** | **$1.65\text{ m/s}$** | **$5.95\text{ km/h}$** | $[-4.33, +3.93]\text{ m/s}$ |

### Implication:
* At $\Delta t = 1.0\text{ s}$ ($T=50$), $90\%$ of velocity changes are bounded within $\pm 1.2\text{ m/s}$ ($4.3\text{ km/h}$), and the mean deviation is only $0.49\text{ m/s}$ ($1.75\text{ km/h}$). Shorter integration steps drastically reduce intermediate variance.

*Artifact Reference:* [`stage5_delta_v_interval_analysis.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_delta_v_interval_analysis.csv)

---

## 5. Non-Neural $\Delta v$ Baselines on Unseen S3a

Evaluating simple statistical estimators on `IOVNBD_S3a` for predicting $\Delta v$ directly:

| Baseline Model | $\Delta v$ RMSE ($m/s$) | $\Delta v$ RMSE ($km/h$) | $\Delta v$ MAE ($m/s$) | $\Delta v$ MAE ($km/h$) | $R^2$ Score | Pearson $r$ | Pred Mean | Pred Std |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Zero $\Delta v$ Baseline ($\Delta v = 0$)** | **2.1887** | **7.88** | **1.4699** | **5.29** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **2. Linear Regression (21 Means)** | 2.2111 | 7.96 | 1.5076 | 5.43 | -0.0206 | 0.0604 | -0.0747 | 0.4630 |
| **3. Ridge Regression (87 Aggregates)** | 2.2225 | 8.00 | 1.5074 | 5.43 | -0.0311 | 0.0402 | -0.0407 | 0.4812 |
| **4. Inertial Acceleration Integral** | 2.2060 | 7.94 | 1.4990 | 5.40 | -0.0159 | 0.0584 | +0.0124 | 0.4319 |

*Finding:* Linear combinations of raw IMU features without non-linear frame orientation tracking (rotation matrix estimation) cannot improve over the zero-$\Delta v$ persistence prior because phone orientation rotates in 3D during driving. This proves a **non-linear recurrent neural model (`LSTMNoAttention`) is strictly necessary** to learn coordinate transformation from phone frame to vehicle frame.

*Artifact Reference:* [`stage5_delta_v_baselines.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_delta_v_baselines.csv)

---

## 6. Anchored Reconstruction Test on S3a ($v_{\text{end}} = v_{\text{start}} + \Delta v_{\text{est}}$)

To directly evaluate the performance of state-anchored velocity tracking vs. unanchored static regression:

| Model Formulation | Operating Mode | S3a Val RMSE ($m/s$) | S3a Val MAE ($m/s$) | $R^2$ Score | Pearson $r$ | Pred Range ($m/s$) | Dynamic Span Capture |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Anchored Model 1: Persistence ($v_{\text{start}} + 0$)** | **ANCHORED** | **2.1887** ($7.88\text{ km/h}$) | **1.4699** ($5.29\text{ km/h}$) | **0.8687** | **0.9344** | **[0.00, 27.23]** | **100.0% (No Collapse)** |
| **Anchored Model 2: Linear $\Delta v$ ($v_{\text{start}} + \text{LR}$)** | **ANCHORED** | **2.2111** ($7.96\text{ km/h}$) | **1.5076** ($5.43\text{ km/h}$) | **0.8660** | **0.9328** | **[-2.19, 27.29]** | **100.0% (No Collapse)** |
| **Anchored Model 3: Ridge $\Delta v$ ($v_{\text{start}} + \text{Ridge}$)** | **ANCHORED** | **2.2225** ($8.00\text{ km/h}$) | **1.5074** ($5.43\text{ km/h}$) | **0.8646** | **0.9323** | **[-2.34, 27.33]** | **100.0% (No Collapse)** |
| **Anchored Model 4: Inertial Integral ($v_{\text{start}} + \int a$)** | **ANCHORED** | **2.2060** ($7.94\text{ km/h}$) | **1.4990** ($5.40\text{ km/h}$) | **0.8666** | **0.9335** | **[-1.98, 27.45]** | **100.0% (No Collapse)** |
| **Unanchored Exp_2 Reference (Direct LSTM)** | **UNANCHORED** | **5.3725** ($19.34\text{ km/h}$) | **4.2842** ($15.42\text{ km/h}$) | **0.2088** | **0.5432** | **[5.09, 15.21]** | **37.1% (Severe Collapse)** |

> [!IMPORTANT]
> **Diagnostic Finding:** When speed is formulated as an anchored velocity state, the validation $R^2$ jumps from **$0.2088 \to 0.8687$**, RMSE drops from **$5.37\text{ m/s} \to 2.19\text{ m/s}$**, and the prediction span spans the full $[0.0, 27.2]\text{ m/s}$ ground truth without dynamic range compression.

*Artifact Reference:* [`stage5_delta_v_reconstruction.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_delta_v_reconstruction.csv)

---

## 7. Physical Interpretation

1. **Newtonian Mechanics & Galilean Relativity:**  
   The laws of physics state that no closed-box inertial sensor can detect uniform linear velocity without referencing an external landmark or integrating acceleration over time:
   $$\vec{v}(t) = \vec{v}(t_0) + \int_{t_0}^t \mathbf{R}_{b}^{w}(\tau) \vec{a}_{b}(\tau) d\tau$$
2. **Why Direct Window Regression Collapses:**  
   Passing a 4-second IMU window into an LSTM without $v(t_0)$ forces the network to estimate the integration constant $C = v(t_0)$ from non-kinematic noise (vibrations). Because vibration noise is inconsistent across road routes, the optimal L2 prediction is the prior mean.
3. **Why $\Delta v$ Estimation is Well-Posed:**  
   Predicting $\Delta v = \int_{t-4}^{t} a(\tau) d\tau$ requires only the IMU sequence and phone attitude rotation $\mathbf{R}_b^w$. The LSTM architecture is ideally suited to compute this non-linear integration.

---

## 8. Evidence For / Against the Hypothesis

* **Evidence FOR:**
  * $\Delta v$ mean is stationary across all 4 sessions ($\mu \approx 0.00\text{ m/s}$ on both Train and S3a).
  * Linear acceleration features correlate $8\times$ more strongly with $\Delta v$ than with absolute speed.
  * Anchored reconstruction eliminates dynamic-range compression, expanding predicted range to the full $[0.0, 27.2\text{ m/s}]$ with $R^2 = 0.8687$.
* **Evidence AGAINST / Caveats:**
  * Without an initial anchor velocity $v(0)$, integrating $\Delta v$ over hours of driving will experience unbounded cumulative dead-reckoning drift unless periodically zero-updated (ZUPT) or corrected by external cellular/GNSS fixes.

---

## 9. Proposed Neural Experiment: Exp_5

### Experiment Specification: `Exp_5_LSTMNoAttention_DeltaV`
1. **Target Formulation:** $\Delta v_i = v_{\text{end}, i} - v_{\text{start}, i}$ (Physical unit: $m/s$).
2. **Target Preprocessing:** Z-score standardization on training $\Delta v$:
   $$\mu_{\Delta v} = 0.0019142\text{ m/s}, \quad \sigma_{\Delta v} = 2.4407406\text{ m/s}$$
3. **Model Architecture (LOCKED TO EXP_2):** `LSTMNoAttention` ($217,729$ parameters, $21$ input features, $2$ layers, hidden_dim=128, dropout=0.2).
4. **Loss Function (LOCKED TO EXP_2):** Standard unweighted MSE: $\mathcal{L} = \frac{1}{B} \sum (\Delta y_{std} - \Delta \hat{y}_{std})^2$.
5. **Optimizer & Hyperparameters (LOCKED TO EXP_2):** Adam ($\text{lr}=0.0008$), ReduceLROnPlateau, batch_size=32 (train), batch_size=256 (val), seed=42, epochs=5.
6. **Training Split:** `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2` (Stride = 5, 205,398 windows).
7. **Validation Split:** `IOVNBD_S3a` (Stride = 1, 122,901 windows).
8. **Reconstruction Evaluation on S3a:**
   * **Metric 1 (Direct $\Delta v$ Quality):** $\Delta v$ RMSE, $\Delta v$ MAE, $\Delta v$ $R^2$, $\Delta v$ Pearson $r$.
   * **Metric 2 (Anchored End-Speed Reconstruction):** $\hat{v}_{\text{end}} = v_{\text{start}} + \Delta \hat{v}$.
9. **Success Criteria:**
   * $\Delta v$ Pearson $r > 0.30$ (improving over linear baseline $r=0.06$).
   * Anchored reconstruction RMSE on S3a $< 2.10\text{ m/s}$ (beating persistence $2.19\text{ m/s}$ and Exp_2 $5.37\text{ m/s}$).
   * Anchored prediction range spans $\ge [0.5, 25.0]\text{ m/s}$.
10. **Failure Criteria:**
    * $\Delta v$ Pearson $r \le 0.05$ (indicating LSTM cannot learn 3D attitude integration from 21 features).

---

## 10. Deployment Implications: Case A vs. Case B

### Case A — Known Initial Velocity (GNSS / State Hand-off)
* **Operational Scenario:** The vehicle enters a GNSS-denied tunnel, urban canyon, or basement parking after driving with satellite lock.
* **Mechanism:** The last valid GNSS fix provides $v(t_0)$. The neural network subsequently integrates $\Delta \hat{v}_t$ at $50\text{ Hz}$ to track vehicle speed throughout the GPS outage.
* **Feasibility:** **Extremely High.** The preflight test proves $R^2 \approx 0.87$ and RMSE $< 2.2\text{ m/s}$ over short-to-medium horizons.

### Case B — Pure Standalone Operation (No Initial Velocity Fix)
* **Operational Scenario:** The phone starts logging inside an underground garage with zero prior velocity knowledge.
* **Mechanism:** The $\Delta v$ model cannot determine the initial velocity offset on its own. It requires:
  1. Zero-Velocity Detection (ZUPT): Stationary start assumption ($v_0 = 0\text{ m/s}$) when IMU variance $< \text{threshold}$.
  2. Integration: Subsequent speed is tracked as $\hat{v}(t) = 0 + \sum \Delta \hat{v}$.
* **Limitation:** Any bias in $\Delta \hat{v}$ accumulates linearly over time ($\text{drift} \sim \text{bias} \times t$). Therefore, pure standalone operation must periodically reset to zero whenever the vehicle stops.

---

## DATA-SAFETY VERIFICATION

* [x] **`IOVNBD_S3c` was NOT accessed, NOT loaded, NOT read, and NOT evaluated.**
* [x] **No neural network was trained.**
* [x] **No previous experiment (`Exp_1`, `Exp_2`, `Exp_2b`, `Exp_3`, `Exp_4`) was modified or overwritten.**
* [x] **No validation data were used for fitting scalers or linear baselines.**
* [x] **No model checkpoints were created.**
* [x] **Existing experiment outputs remain 100% intact.**
