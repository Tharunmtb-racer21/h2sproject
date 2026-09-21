# Independent Audit Report: S3a Validation Performance & Visual Diagnostic

**Audit Subject:** Validation Performance on `IOVNBD_S3a` (122,901 sequences)  
**Models Audited:**
1. `Exp_1`: LSTMSelfAttention + TargetStd (`outputs/Exp_1_TargetStd/best_model.pt`)
2. `Exp_2`: LSTMNoAttention + TargetStd + Stride 1 (`outputs/Exp_2_LSTMNoAttention_TargetStd/best_model.pt`)
3. `Exp_2b`: LSTMNoAttention + TargetStd + Stride 5 (`outputs/Exp_2b_LSTMNoAttention_TargetStd_Stride5/best_model.pt`)
**Test Set Protocol:** `IOVNBD_S3c` remains **100% FROZEN, UNTOUCHED, AND NEVER EVALUATED**

---

## 1. Mathematical Consistency & Reconciliation Audit

All performance metrics were independently recomputed directly from the model forward passes over all **122,901 validation sequences** with physical inverse standardization:
$$\hat{y}_{m/s} = \hat{y}_{std} \times 5.5192132 + 8.3119106$$

### Metric Reconciliation Table
| Experiment | Samples Verified | Reported MAE | Recomputed MAE | Reported RMSE | Recomputed RMSE | Reported $R^2$ | Recomputed $R^2$ | Reported $r$ | Recomputed $r$ | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Exp 1** | 122,901 | 4.851529 | 4.851529 | 5.987178 | 5.987178 | 0.017398 | 0.017398 | 0.417334 | 0.417334 | **EXACT MATCH (0.0 discrepancy)** |
| **Exp 2** | 122,901 | 4.284192 | 4.284192 | 5.372490 | 5.372490 | 0.208803 | 0.208803 | 0.543207 | 0.543207 | **EXACT MATCH (0.0 discrepancy)** |
| **Exp 2b** | 122,901 | 4.883275 | 4.883275 | 6.106267 | 6.106267 | -0.022079 | -0.022079 | 0.424127 | 0.424127 | **EXACT MATCH (0.0 discrepancy)** |

* All array lengths match exactly: $\text{len}(\text{predictions}) = \text{len}(\text{targets}) = 122,901$.
* All speed-binned sequence counts sum exactly to **122,901** ($14,199 + 7,951 + 32,532 + 44,036 + 15,306 + 6,826 + 2,051 + 0 = 122,901$).

---

## 2. Statistical Analysis: $R^2$ Score vs. Pearson Correlation ($r$)

A key finding in the validation results is that models exhibit moderate positive Pearson correlation ($r \approx 0.42 - 0.54$) while displaying near-zero or negative $R^2$ scores ($R^2 \approx -0.02 \text{ to } 0.21$).

### Mathematical Explanation of the Difference:
1. **Pearson Correlation Coefficient ($r$):**
   $$r = \frac{\sum (y_i - \bar{y})(\hat{y}_i - \bar{\hat{y}})}{\sqrt{\sum (y_i - \bar{y})^2 \sum (\hat{y}_i - \bar{\hat{y}})^2}}$$
   * Pearson $r$ is scale- and shift-invariant. It measures whether predicted speed increases monotonically with actual speed. A correlation of $r=0.42 - 0.54$ confirms that the models successfully capture the directional trends of vehicle acceleration and braking.
2. **Coefficient of Determination ($R^2$):**
   $$R^2 = 1 - \frac{\text{MSE}}{\text{Var}(y)} = 1 - \frac{\frac{1}{N}\sum (y_i - \hat{y}_i)^2}{\frac{1}{N}\sum (y_i - \bar{y})^2}$$
   * $R^2$ penalizes absolute calibration error and dynamic range compression.
   * On `IOVNBD_S3a`, actual speed has a standard deviation of $\sigma_{val} = 6.04\text{ m/s}$ ($\text{Var}(y) = 36.48\text{ m}^2/\text{s}^2$).
   * Because the model predictions are compressed towards the training mean ($8.31\text{ m/s}$) and cannot span the full $[0, 27.2\text{ m/s}]$ dynamic range, $\text{MSE} \approx 35.8 - 37.3\text{ m}^2/\text{s}^2 \approx \text{Var}(y)$, yielding $R^2 \approx 0$.
   * **Conclusion:** The low $R^2$ is **not** a mathematical error; it accurately reflects the dynamic range compression (regression-to-the-mean) despite positive linear trend correlation.

---

## 3. Overlapping Window Interpretation Limitations

* **Sampling Rate & Windowing:** Sequences are sampled at $50\text{ Hz}$ ($dt = 0.02\text{ s}$) with length $T=200$ ($4.0\text{ s}$) and validation evaluated at $\text{stride}=1$.
* **Window Overlap:** Consecutive validation windows share $199$ out of $200$ IMU sample steps ($99.5\%$ temporal overlap).
* **Implications:**
  1. **Unbiased Point Estimates:** Point estimates of global RMSE, MAE, and mean residuals remain mathematically unbiased representations of instantaneous speed error.
  2. **Autocorrelated Residuals:** Residual errors $e_t$ are highly autocorrelated over a $\approx 4\text{ s}$ horizon. This means sample points are not statistically independent, artificially inflating effective degrees of freedom.
  3. **Evaluation Protocol Validity:** Evaluating with $\text{stride}=1$ is standard practice in real-time dead-reckoning because vehicle state estimation runs continuously at every IMU update step.

---

## 4. Visual Diagnostic & Failure Mode Analysis

Inspection of the 19 generated plots reveals four primary failure modes:

```
+-------------------------------------------------------------------------------+
|                             VISUAL FAILURE MODES                              |
+-----------------------------------+-------------------------------------------+
| 1. Dynamic Range Truncation       | Predictions stay within [4.9, 15.2-20.0]  |
|                                   | m/s, failing to reach 22-27 m/s speeds.   |
+-----------------------------------+-------------------------------------------+
| 2. Stationary Crawl Overestimate  | Stopped/crawling vehicles (0-2 m/s) are   |
|                                   | predicted as 6.4 - 7.5 m/s (Bias > +6 m/s)|
+-----------------------------------+-------------------------------------------+
| 3. High-Speed Underestimation     | Highway driving (20-27 m/s) is predicted  |
|                                   | as 9.0 - 11.4 m/s (Negative Bias > -13m/s)|
+-----------------------------------+-------------------------------------------+
| 4. Temporal Inertial Lag          | Predictions exhibit a ~1.0-1.5s lag during|
|                                   | rapid vehicle acceleration & hard braking.|
+-----------------------------------+-------------------------------------------+
```

### Plot Evidence:
1. **Actual vs. Predicted Scatter Plots:** The regression slope is visibly shallower than the $y=x$ ideal line ($\text{slope} \approx 0.35 - 0.45$), confirming dynamic range attenuation.
2. **Residual vs. Actual Speed Plots:** Displays a strong negative linear trend in errors—errors are large positive at $0\text{ m/s}$ ($+6.5\text{ m/s}$) and large negative at $25\text{ m/s}$ ($-15\text{ m/s}$), intersecting zero at $\approx 8.3\text{ m/s}$ (the dataset mean).
3. **Speed-Binned Comparison:** Models achieve their highest accuracy in the moderate urban driving regime (**$5 - 10\text{ m/s}$**, with $\text{RMSE} \approx 1.80 - 2.57\text{ m/s}$ and $\text{MAE} \approx 1.43 - 2.10\text{ m/s}$), while errors increase predictably at speed extremes.

---

## 5. Model Comparison Summary

| Model | Parameters | Stride | Epoch | S3a Val RMSE | S3a Val MAE | Pearson $r$ | Assessment |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **Exp 1: Self-Attention** | 267,265 | 1 | 1 | `5.9872 m/s` | `4.8515 m/s` | `0.4173` | Balanced, widest range ($20.0\text{ m/s}$) |
| **Exp 2: No-Attention** | 217,729 | 1 | 1 | **`5.3725 m/s`** | **`4.2842 m/s`** | **`0.5432`** | Lowest RMSE/MAE on S3a |
| **Exp 2b: No-Attention Pilot**| 217,729 | 5 | 1 | `6.1063 m/s` | `4.8833 m/s` | `0.4241` | Compute-efficient pilot (5x faster) |

---

## 6. Readiness Assessment & Final Test Set Recommendation

### Is the Model Ready for Final Test Evaluation (`IOVNBD_S3c`)?

> [!WARNING]
> **RECOMMENDATION: DO NOT EVALUATE ON FROZEN TEST SET `IOVNBD_S3c` YET.**

### Reasons:
1. **One-Shot Integrity Safeguard:** `IOVNBD_S3c` is a strictly frozen test set that should only be evaluated once for final reporting. Evaluating it now would exhaust its unbiased benchmark status.
2. **Unresolved Range Truncation:** The models still suffer from regression-to-the-mean at high speeds ($>15\text{ m/s}$) and crawl speeds ($<2\text{ m/s}$).
3. **Cross-Session Shift:** Training dynamics show that validation error increases after Epoch 1 due to cross-session distribution shift.

---

## 7. Recommended Next Experiment (Stage 4)

### Proposed Experiment: **`Exp_3 — Weighted/Huber Loss for Dynamic Range Expansion`**

* **Problem Addressed:** Standard MSE penalizes large errors symmetrically, encouraging the network to minimize worst-case risk by predicting near the training mean ($8.31\text{ m/s}$).
* **Proposed Intervention:**
  1. Replace standard MSE with a **Smooth L1 / Huber Loss** or a **Speed-Weighted Loss Function** that applies higher loss weights to non-zero accelerations and extreme speed bins ($<2\text{ m/s}$ and $>15\text{ m/s}$).
  2. Implement **Zero-Velocity Update (ZUPT) thresholding** to explicitly clamp predictions to $0\text{ m/s}$ when IMU accelerometer variance indicates the vehicle is stationary.
* **Controlled Protocol:**
  - Maintain locked target standardization ($\mu_{train}=8.3119, \sigma_{train}=5.5192$).
  - Maintain train/val split (M+S1+S2 / S3a).
  - Keep `IOVNBD_S3c` 100% frozen.
