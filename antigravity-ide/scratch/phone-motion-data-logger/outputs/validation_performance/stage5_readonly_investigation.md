# Stage 5 Read-Only Investigation: Root Cause Analysis of Speed Estimation & Dynamic-Range Compression

**Subject:** Physical Identifiability, Feature Distributions, Cross-Session Shift, and Mathematical Limits of Smartphone IMU Speed Estimation  
**Data Evaluated:** `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2` (Training split: 1,027,579 steps / 205,398 stride-5 windows) and `IOVNBD_S3a` (Validation benchmark: 123,100 steps / 122,901 stride-1 windows)  
**Safety Protocol:** **STRICTLY READ-ONLY**. `IOVNBD_S3c` was **100% FROZEN, NEVER ACCESSED, NEVER LOADED**. No neural networks were trained. No scalers were fitted on validation data.

---

## 1. Executive Finding

The fundamental cause of prediction dynamic-range compression on unseen driving sessions is **Inertial Identifiability & Physical Feature Degeneracy under Galilean Invariance**, exacerbated by **Cross-Session Vibration/Attitude Shifts**:

1. **Physical Degeneracy:** Accelerometers measure proper acceleration ($\vec{a} = \frac{d\vec{v}}{dt} + \vec{g}$), not velocity $\vec{v}$. At steady-state cruising, whether a vehicle is stopped ($0\text{ m/s}$) or cruising on a highway ($27\text{ m/s}$ / $98\text{ km/h}$), the net acceleration vector is identical ($\approx 9.85\text{ m/s}^2$ downward gravity). Instantaneous raw IMU features have a Pearson correlation with speed of $r \approx 0.000$ ($|r| \le 0.008$).
2. **Surrogate Signal Weakness:** The only feature with non-zero correlation to speed is high-frequency vibration variance (`accel_mag_var`, `accel_z_var`, `gyro_z_var`, $\rho \approx 0.21 - 0.24$). However, vibration is vehicle-, road-, and mount-dependent rather than a direct measurement of velocity.
3. **Non-Neural Baseline Proof:** Even an optimal statistical Ridge regression fitted on 84 window aggregate features exhibits the exact same behavior on unseen `S3a` ($r = 0.5499$, $R^2 = 0.1153$, predictions compressed to $[4.22, 16.82]\text{ m/s}$).
4. **Conclusion:** Neural networks are not failing because of architecture or optimization; they are correctly converging to the conditional expectation $\mathbb{E}[y \mid \text{IMU}]$ because the 4-second local IMU motion window lacks an absolute velocity reference frame.

---

## 2. Feature–Speed Relationship

Correlation analysis across all **1,027,579 training steps** (`IOVNBD_M`, `S1`, `S2`) reveals a stark dichotomy between raw kinematic signals and statistical variances:

| Feature Category | Features | Pearson $r$ (Combined) | Spearman $\rho$ (Combined) | Session Variation Range | Physical Meaning |
|---|---|:---:|:---:|:---:|---|
| **Raw Instantaneous Accelerations** | `accel_x`, `accel_y`, `accel_z`, `accel_mag` | **-0.0088 to +0.0008** | **-0.0118 to +0.0105** | [-0.033, +0.034] | **Zero direct relationship with speed.** Measures instantaneous acceleration / gravity. |
| **Raw Instantaneous Angular Rates** | `gyro_x`, `gyro_y`, `gyro_z` | **-0.0017 to +0.0021** | **-0.0027 to +0.0011** | [-0.013, +0.019] | **Zero direct relationship with speed.** Measures rotation rate during cornering. |
| **Window Mean Accelerations** | `accel_x_mean`, `accel_y_mean`, `accel_z_mean`, `accel_mag_mean` | **-0.0216 to +0.0153** | **-0.0048 to +0.0107** | [-0.052, +0.048] | Reflects vehicle pitch/roll mount angles, not speed. |
| **Window Mean Angular Rates** | `gyro_x_mean`, `gyro_y_mean`, `gyro_z_mean` | **-0.0005 to +0.0082** | **-0.0100 to +0.0070** | [-0.028, +0.031] | Reflects steady turning / road curvature. |
| **IMU High-Frequency Variances** | `accel_z_var`, `accel_mag_var`, `gyro_z_var` | **+0.0315 to +0.0423** | **+0.2078 to +0.2415** | [+0.156, +0.288] | **Moderate rank correlation.** Road roughness and chassis vibrations scale monotonically with wheel rotation rate. |

*Artifact Reference:* [`stage5_feature_target_correlation.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_feature_target_correlation.csv)

---

## 3. Train vs S3a Distribution Shift

Comparing training features against the unseen `IOVNBD_S3a` validation session ($123,100$ steps):

| Variable | Train Mean ($\pm \sigma$) | S3a Mean ($\pm \sigma$) | Cohen's $d$ (Shift) | KS Statistic ($p$-val) | Shift Interpretation |
|---|:---:|:---:|:---:|:---:|---|
| **Target Speed** | $8.31 \pm 5.52\text{ m/s}$ | $10.54 \pm 6.04\text{ m/s}$ | **+0.403** | 0.2016 ($p=0.0$) | **Substantial Target Shift:** S3a has $26.8\%$ higher average speed. |
| `accel_x_var` | $0.632 \pm 0.784$ | $0.302 \pm 0.430$ | **-0.422** | 0.3641 ($p=0.0$) | S3a has significantly lower horizontal vibration (smoother road/mount). |
| `accel_y_var` | $0.613 \pm 0.821$ | $0.312 \pm 0.445$ | **-0.366** | 0.3285 ($p=0.0$) | S3a has significantly lower lateral vibration. |
| `accel_mag_mean` | $9.962 \pm 0.134$ | $9.919 \pm 0.127$ | **-0.324** | 0.1651 ($p=0.0$) | Slight mount calibration/orientation shift ($\Delta \approx 0.04\text{ m/s}^2$). |
| `gyro_x_var` | $0.0122 \pm 0.0694$ | $0.0009 \pm 0.0021$ | **-0.163** | 0.6186 ($p=0.0$) | Severe variance suppression on S3a (13x lower pitch jitter). |
| `gyro_z_var` | $0.0028 \pm 0.0391$ | $0.0010 \pm 0.0008$ | **-0.047** | 0.2995 ($p=0.0$) | 2.8x lower yaw jitter on S3a. |
| `accel_z` | $9.853 \pm 0.525$ | $9.841 \pm 0.453$ | **-0.024** | 0.0210 ($p=1.4\times 10^{-42}$) | Stable gravity vector ($<0.012\text{ m/s}^2$ difference). |

*Key Finding:* While raw gravity acceleration is stable across sessions, the **vibration noise proxy (`accel_var`, `gyro_var`) is 30% to 70% lower in S3a**. Because models rely partially on vibration magnitude to infer high speeds, the quieter S3a session causes predictions to be biased lower.

*Artifact Reference:* [`stage5_distribution_shift.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_distribution_shift.csv)

---

## 4. Speed-Conditioned Feature Separation

Analyzing training features conditioned on the seven standardized speed bins:

| Speed Regime ($m/s$) | Sample Count ($N$) | Mean Speed ($m/s$) | `accel_mag_mean` ($m/s^2$) | `accel_z_mean` ($m/s^2$) | `accel_mag_var` | `gyro_mag_mean` ($rad/s$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0 – 2** (Crawl / Stop) | 175,778 ($17.1\%$) | $0.41\text{ m/s}$ | $9.940 \pm 0.471$ | $9.855 \pm 0.187$ | **0.1957** | 0.1003 |
| **2 – 5** (Low Speed) | 101,212 ($9.8\%$) | $3.66\text{ m/s}$ | $9.974 \pm 0.482$ | $9.854 \pm 0.259$ | **0.2771** | 0.1631 |
| **5 – 10** (Moderate) | 385,783 ($37.5\%$) | $7.64\text{ m/s}$ | $9.973 \pm 0.545$ | $9.851 \pm 0.282$ | **0.3006** | 0.1370 |
| **10 – 15** (Med-High) | 262,711 ($25.6\%$) | $12.27\text{ m/s}$ | $9.964 \pm 0.609$ | $9.854 \pm 0.298$ | **0.3080** | 0.1201 |
| **15 – 20** (Highway) | 68,491 ($6.7\%$) | $16.93\text{ m/s}$ | $9.934 \pm 0.549$ | $9.854 \pm 0.283$ | **0.2870** | 0.0994 |
| **20 – 25** (High Speed) | 28,141 ($2.7\%$) | $22.01\text{ m/s}$ | $9.960 \pm 0.602$ | $9.865 \pm 0.336$ | **0.3439** | 0.1118 |
| **25 – 30** (Very High) | 5,463 ($0.5\%$) | $27.02\text{ m/s}$ | $9.929 \pm 0.526$ | $9.848 \pm 0.263$ | **0.2640** | 0.1360 |

### Separation Diagnostics:
1. **Severe Overlap in Acceleration:** `accel_mag_mean` at $0\text{ m/s}$ ($9.940\text{ m/s}^2$) is statistically indistinguishable from $27\text{ m/s}$ ($9.929\text{ m/s}^2$). 
2. **Non-Monotonicity of Variances:** `accel_mag_var` plateaus between $5\text{ m/s}$ and $20\text{ m/s}$ ($\approx 0.29 - 0.31$) and actually *drops* at $25–30\text{ m/s}$ ($0.2640$) because smooth highway pavement generates fewer chassis shocks than uneven city streets.
3. **Consequence:** There is **no separable cluster** in feature space distinguishing steady highway cruising from moderate city driving.

*Artifact Reference:* [`stage5_speed_conditioned_features.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_speed_conditioned_features.csv)

---

## 5. Session Generalization

| Session ID | Split | Steps ($N$) | Duration | Speed Mean ($\pm \sigma$) | Speed Range | `accel_mag_mean` | `accel_mag_var` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **IOVNBD_M** | TRAIN | 308,799 | 102.9 min | $9.70 \pm 5.61\text{ m/s}$ | $[0.0, 27.97]\text{ m/s}$ | $9.962\text{ m/s}^2$ | 0.3110 |
| **IOVNBD_S1** | TRAIN | 258,725 | 86.2 min | $7.33 \pm 4.51\text{ m/s}$ | $[0.0, 26.07]\text{ m/s}$ | $9.945\text{ m/s}^2$ | 0.1866 |
| **IOVNBD_S2** | TRAIN | 460,055 | 153.4 min | $7.93 \pm 5.79\text{ m/s}$ | $[0.0, 29.23]\text{ m/s}$ | $9.971\text{ m/s}^2$ | 0.3169 |
| **IOVNBD_S3a** | VAL | 123,100 | 41.0 min | **$10.54 \pm 6.04\text{ m/s}$** | $[0.0, 27.23]\text{ m/s}$ | $9.919\text{ m/s}^2$ | 0.2003 |

*Session Heterogeneity:* `IOVNBD_S1` and `IOVNBD_S3a` have low vibration noise ($0.18 - 0.20$), while `IOVNBD_M` and `IOVNBD_S2` have high vibration noise ($0.31 - 0.32$). However, `S3a` has the highest mean speed ($10.54\text{ m/s}$ vs $7.33\text{ m/s}$ in `S1`), creating a contradictory cross-session signal (high speed with low vibration).

*Artifact Reference:* [`stage5_session_statistics.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_session_statistics.csv)

---

## 6. 4-Second Window Information Content

Evaluating 205,398 training windows ($T=200$, $50\text{ Hz}$, $4.0\text{ s}$ duration):

* **Nearly Constant Speed Windows ($<0.5\text{ m/s}$ total change in 4s):** **19.06%**
* **Active Acceleration Windows ($>1.0\text{ m/s}$ increase in 4s):** **26.82%**
* **Active Deceleration Windows ($>1.0\text{ m/s}$ decrease in 4s):** **24.19%**
* **Moderate Maneuvers ($0.5 - 1.0\text{ m/s}$ change):** **29.93%**

*Key Finding:* Over $80\%$ of 4-second windows contain measurable delta acceleration ($\Delta v > 0.5\text{ m/s}$). Within-window acceleration is strong and identifiable for computing **speed changes** ($\Delta v$), but the window contains zero physical DC offset informing the model whether the maneuver started from $0\text{ m/s}$, $10\text{ m/s}$, or $20\text{ m/s}$.

---

## 7. Endpoint Target Analysis

Comparing the endpoint target $y_{\text{end}} = v(t)$ against within-window statistics:

| Target Comparison | Mean Offset | Standard Deviation | Mean Absolute Error (MAE) | 10th Percentile | 50th Percentile (Median) | 90th Percentile |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **$y_{\text{end}} - \text{mean}(y_{\text{win}})$** | $+0.0009\text{ m/s}$ | $1.2975\text{ m/s}$ | **$0.8667\text{ m/s}$** ($3.12\text{ km/h}$) | $-1.58\text{ m/s}$ | $+0.007\text{ m/s}$ | $+1.50\text{ m/s}$ |
| **$y_{\text{end}} - \text{median}(y_{\text{win}})$** | $-0.0071\text{ m/s}$ | $1.3707\text{ m/s}$ | **$0.8803\text{ m/s}$** ($3.17\text{ km/h}$) | $-1.64\text{ m/s}$ | $+0.007\text{ m/s}$ | $+1.52\text{ m/s}$ |
| **$y_{\text{end}} - y_{\text{start}}$** | $+0.0019\text{ m/s}$ | $2.4407\text{ m/s}$ | **$1.6526\text{ m/s}$** ($5.95\text{ km/h}$) | $-3.03\text{ m/s}$ | $+0.011\text{ m/s}$ | $+2.86\text{ m/s}$ |
| **Within-Window $\sigma(y)$** | $0.5580\text{ m/s}$ | $0.5785\text{ m/s}$ | $0.5580\text{ m/s}$ | $0.057\text{ m/s}$ | $0.379\text{ m/s}$ | $1.298\text{ m/s}$ |

*Key Finding:* Endpoint speed is tightly coupled to window mean speed ($\text{MAE} = 0.87\text{ m/s}$). The target formulation itself is not noisy or misaligned; rather, both the endpoint and the window mean suffer from the identical absence of an absolute velocity anchor.

*Artifact Reference:* [`stage5_window_target_analysis.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_window_target_analysis.csv)

---

## 8. Simple Non-Neural Baselines on Unseen S3a

To isolate whether the dynamic-range collapse is a failure of neural training or intrinsic to the data, four non-neural baselines were fitted strictly on training data (`M`, `S1`, `S2`) and evaluated on all **122,901 validation windows** of `IOVNBD_S3a`:

| Model / Baseline | Val RMSE ($m/s$) | Val MAE ($m/s$) | $R^2$ Score | Pearson $r$ | Pred Mean ($m/s$) | Pred Std ($m/s$) | Pred Range ($m/s$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Constant Training Mean** | 6.4386 | 5.1551 | -0.1363 | 0.0000 | 8.3144 | 0.0000 | [8.31, 8.31] |
| **2. Linear Regression (21 Window Means)** | 6.3265 | 5.0507 | -0.0971 | 0.2584 | 8.2084 | 0.8388 | [4.81, 18.84] |
| **3. Ridge Regression (84 Window Aggregates)** | **5.6809** | **4.5951** | **+0.1153** | **0.5499** | **8.5919** | **1.5866** | **[4.22, 16.82]** |
| **4. Physical IMU Variance Model** | 6.3556 | 5.0960 | -0.1073 | 0.2818 | 8.2879 | 0.3920 | [7.56, 15.17] |
| **Exp 2 (LSTMNoAttention Neural Model)** | **5.3725** | **4.2842** | **+0.2088** | **0.5432** | **9.2109** | **2.1113** | **[5.09, 15.21]** |
| **Ground Truth S3a Benchmark** | — | — | 1.0000 | 1.0000 | 10.5447 | 6.0400 | [0.00, 27.23] |

### Diagnostic Takeaways:
1. **Identical Pearson Correlation:** Non-neural Ridge regression achieves $r = 0.5499$, matching the LSTM ($r = 0.5432$).
2. **Identical Range Compression:** Non-neural Ridge regression predictions are compressed to $[4.22, 16.82]\text{ m/s}$ ($\sigma = 1.59\text{ m/s}$), proving that **range compression is not a neural training artifact**—it is the optimal linear Bayesian estimate given noisy features.

*Artifact Reference:* [`stage5_simple_baselines.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_simple_baselines.csv)

---

## 9. Physical Signal Analysis

From classical mechanics:
$$\vec{f}_{\text{IMU}} = \vec{a}_{\text{vehicle}} - \vec{g} + \vec{\eta}_{\text{vib}}(t)$$
* **Constant Velocity Cruising ($\vec{a}_{\text{vehicle}} = 0$):**
  $$\vec{f}_{\text{IMU}} = -\vec{g} + \vec{\eta}_{\text{vib}}(t)$$
  The sensor output is completely independent of the velocity scalar $\|\vec{v}\|$.
* **Vibration Dependence:** The noise term $\vec{\eta}_{\text{vib}}(t)$ depends on engine RPM, transmission gear ratio, tire pressure, suspension stiffness, road asphalt texture, and phone mount rigidity.
* **Why Pure IMU Speed Estimation Drifts/Collapses:** In dead-reckoning without external velocity constraints (wheel tick, optical flow, or GPS/GNSS velocity fixes), instantaneous speed is mathematically unobservable from pure IMU windows without integration from a known initial condition $v(t_0)$.

---

## 10. Exp_2 Error Pattern

| Speed Bin ($m/s$) | Sequence Count ($N$) | True Mean ($m/s$) | Pred Mean ($m/s$) | Mean Bias ($m/s$) | RMSE ($m/s$) | MAE ($m/s$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0 – 2** (Crawl / Stop) | 14,199 | 0.3182 | 6.6662 | **+6.3480** | 6.5107 | 6.3480 |
| **2 – 5** (Low Speed) | 7,951 | 3.8958 | 8.2642 | **+4.3685** | 4.8794 | 4.3685 |
| **5 – 10** (Moderate) | 32,532 | 7.6917 | 8.8748 | **+1.1830** | 2.5746 | 2.1026 |
| **10 – 15** (Medium-High) | 44,036 | 12.3611 | 9.5711 | **-2.7900** | 3.4956 | 2.9258 |
| **15 – 20** (Highway) | 15,306 | 17.0564 | 10.6292 | **-6.4273** | 6.7184 | 6.4273 |
| **20 – 25** (High Speed) | 6,826 | 22.3067 | 11.0341 | **-11.2727** | 11.4624 | 11.2727 |
| **25 – 30** (Very High) | 2,051 | 25.6319 | 11.4436 | **-14.1883** | 14.2203 | 14.1883 |

*Pattern Confirmation:* The error is monotonically increasing from large positive bias ($+6.35\text{ m/s}$) at low speed to large negative bias ($-14.19\text{ m/s}$) at high speed. This linear pivot around the dataset mean ($\approx 8.8\text{ m/s}$) is the classic hallmark of **Bayesian shrinkage to the prior mean** when the feature signal-to-noise ratio is low.

*Artifact Reference:* [`stage5_exp2_error_by_speed.csv`](file:///C:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/outputs/validation_performance/stage5_exp2_error_by_speed.csv)

---

## 11. Root-Cause Evidence Summary

### A. Measured Evidence (Facts)
1. Instantaneous IMU feature correlation with vehicle speed is $|r| \le 0.008$.
2. Feature distributions between $0\text{ m/s}$ and $27\text{ m/s}$ overlap almost entirely ($\mu_{\text{accel}} = 9.94\text{ m/s}^2$ vs $9.93\text{ m/s}^2$).
3. Non-neural Ridge regression achieves $r = 0.5499$ on S3a but experiences identical range compression ($[4.22, 16.82]\text{ m/s}$).
4. S3a has $26.8\%$ higher average speed but $30–70\%$ lower vibration variance than the training data.

### B. Interpretation (Deduction)
* The LSTM model is not broken; it has learned the real physical relationship present in the data (correlating acceleration transients and vibrations to relative velocity changes).
* Because absolute DC velocity is unobservable from a 4-second unanchored IMU slice, minimizing L2 loss forces the network to output the conditional expectation $\mathbb{E}[y \mid \text{window}]$, which mathematically collapses towards the prior mean.

### C. Uncertainty
* Residual variations in road texture across different geographic routes create unpredictable domain shifts in vibration-based speed inference.

---

## 12. Single Recommended Next Experiment: Autoregressive Speed Tracking (Exp_5)

To break the unanchored Galilean degeneracy without violating smartphone-only constraints, the model must transition from **isolated window regression** to **recurrent velocity tracking (temporal dead-reckoning with sequential state carryover)**.

### Experiment Specification: `Exp_5_Autoregressive_DeltaV`
1. **Hypothesis:** Formulating the network to predict the **temporal velocity delta** $\Delta v_t = v_t - v_{t-1}$ from the IMU window, initialized from a single initial anchor $v(0)$, will eliminate range compression because the network directly predicts the physically observable quantity (acceleration integral) rather than absolute speed.
2. **One Controlled Change:** Target formulation changes from absolute speed $y = v_t$ to delta speed $\Delta y = v_t - v_{t-k}$ (or feeding previous step prediction $\hat{v}_{t-1}$ as a recurrent feature input).
3. **Fixed Variables:** Exact same `LSTMNoAttention` backbone, exact 21 features, exact training sessions (`M`, `S1`, `S2`), exact Adam optimizer ($\text{lr}=0.0008$), exact S3a evaluation protocol.
4. **Success Criteria:** Validation prediction span on S3a expands from $[5.09, 15.21]\text{ m/s}$ to $\ge [1.0, 24.0]\text{ m/s}$, and $R^2$ improves above $0.50$.
5. **Failure Criteria:** Accumulated integration drift causes cumulative tracking error to exceed $10\text{ m/s}$.

---

## 13. Data-Safety & Integrity Verification

* [x] **`IOVNBD_S3c` was NOT loaded, NOT read, NOT evaluated, and NOT accessed.**
* [x] **No neural network was trained.**
* [x] **No previous experiment (`Exp_1`, `Exp_2`, `Exp_2b`, `Exp_3`, `Exp_4`) was modified or overwritten.**
* [x] **No validation data (`IOVNBD_S3a`) were used to fit preprocessing scalers or baselines.**
* [x] **No model checkpoints were created.**
* [x] **All existing experiment artifacts and directories remain 100% intact.**
