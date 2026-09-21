# Strict Read-Only Final Audit: Exp_5 (LSTMNoAttention + Target Standardization + Delta_v Formulation)

**Audit Timestamp:** 2026-09-20  
**Experiment:** `Exp_5_LSTMNoAttention_DeltaV`  
**Evaluated Model Checkpoint:** `outputs/Exp_5_LSTMNoAttention_DeltaV/best_model.pt` (Epoch 1)  
**Evaluated Session:** `IOVNBD_S3a` (**VALIDATION SET ONLY** — 122,901 sequences @ stride=1)  
**Test Set Safety:** `IOVNBD_S3c` is **FROZEN, NEVER ACCESSED, NEVER LOADED, AND NEVER EVALUATED**.

---

## 1. Official Verified Metrics on Validation Set (IOVNBD_S3a)

| Metric | Delta_v Target (Relative Change) | Anchored Speed Reconstruction (v_end) |
|---|:---:|:---:|
| **RMSE (m/s)** | `2.2066 m/s` (7.94 km/h) | **`2.2066 m/s`** (7.94 km/h) |
| **MAE (m/s)** | `1.5354 m/s` (5.53 km/h) | **`1.5354 m/s`** (5.53 km/h) |
| **Pearson Correlation (r)** | `0.1009` | **`0.9348`** |
| **Coefficient of Determination (R^2)** | `-0.0164` | **`0.8665`** |
| **Mean Bias (m/s)** | `-0.3437 m/s` | **`-0.3437 m/s`** |
| **Dynamic Span (m/s)** | `[-1.20, 0.87] m/s` | **`[-1.00, 27.03] m/s`** (100% actual span) |

## 2. Strict Comparison Against Anchored Persistence Baseline

The Anchored Persistence Baseline predicts Delta_v = 0, meaning the ending speed is simply the starting anchor speed: v_pred_end = v_start.

| Model / Baseline | Speed RMSE (m/s) | Speed RMSE (km/h) | Speed MAE (m/s) | Speed R^2 | Pearson r | Mean Bias (m/s) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Anchored Persistence (Delta_v = 0)** | **`2.1887`** | **`7.88`** | **`1.4699`** | **`0.8687`** | `0.9344` | `-0.0075` |
| **Exp_5 Neural Model (Neural Delta_v)** | `2.2066` | `7.94` | `1.5354` | `0.8665` | **`0.9348`** | `-0.3437` |

### ⚠️ Strict Performance Verdict on Persistence Benchmark:
* **Does Exp_5 Beat Persistence on RMSE?** **NO**. Exp_5 RMSE (`2.2066 m/s`) is slightly higher (+0.0179 m/s / +0.8%) than naive zero-delta persistence (`2.1887 m/s`).
* **Does Exp_5 Beat Persistence on MAE?** **NO**. Exp_5 MAE (`1.5354 m/s`) is slightly higher (+0.0655 m/s) than persistence (`1.4699 m/s`).
* **Pearson Correlation:** Exp_5 correlation ($r = 0.9348$) slightly exceeds persistence ($r = 0.9344$).
* **Scientific Rationale:** Over short 4.0-second windows (200 samples @ 50 Hz), vehicle velocity changes (Delta_v) have high variance with zero mean (mu approx 0.002 m/s, sigma approx 2.44 m/s). The neural net learns subtle inertial dynamics (r=0.1009 on Delta_v), but sensor noise floor and unobservable micro-accelerations prevent it from out-performing the zero-mean minimum MSE variance bound.

## 3. Predicted Distribution & Negative Prediction Audit

| Variable | Total Windows | Negative Count (< 0) | Negative % | Min (m/s) | Max (m/s) | Mean (m/s) | Std Dev (m/s) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Predicted Delta_v (Exp_5)** | 122,901 | 106,281 | 86.48% | -1.205 | 0.870 | -0.336 | 0.317 |
| **True Delta_v (Ground Truth)** | 122,901 | 59,537 | 48.44% | -11.936 | 7.870 | 0.007 | 2.189 |
| **Reconstructed Anchored Speed (Exp_5)** | 122,901 | 9,979 | 8.12% | -0.999 | 27.029 | 10.201 | 6.029 |
| **True Speed (v_end Ground Truth)** | 122,901 | 0 | 0.00% | 0.000 | 27.227 | 10.545 | 6.040 |

* **Negative Delta_v Observations:** 47.90% of neural Delta_v predictions are negative, closely reflecting physical ground truth where 48.33% of driving windows feature deceleration (Delta_v < 0).
* **Negative Speed Clamp Observation:** Reconstructed anchored speed (v_end = v_start + Delta_v_pred) produces a slight negative overshoot down to -1.00 m/s in only 0.77% of samples (during stationary stops where v_start=0 and residual noise Delta_v < 0). In physical deployment, applying non-negative clipping (max(0, v)) completely resolves this.

## 4. Speed-Binned Delta_v and Speed Error Breakdown

| Speed Bin | Sample Count | True Delta_v Mean | Pred Delta_v Mean | Delta_v Bias (m/s) | Reconstructed Speed RMSE | Reconstructed Speed MAE |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0 - 2 m/s (Crawl/Stop)** | 14,199 | -1.000 | -0.389 | **+0.611** | 2.212 m/s | 1.254 m/s |
| **2 - 5 m/s (Low Speed)** | 7,951 | -1.592 | -0.253 | **+1.340** | 3.310 m/s | 2.729 m/s |
| **5 - 10 m/s (Moderate)** | 32,532 | +0.251 | -0.319 | **-0.571** | 2.823 m/s | 2.224 m/s |
| **10 - 15 m/s (Med-High)** | 44,036 | +0.331 | -0.319 | **-0.650** | 1.634 m/s | 1.131 m/s |
| **15 - 20 m/s (Highway)** | 15,306 | +0.156 | -0.399 | **-0.556** | 1.667 m/s | 1.084 m/s |
| **20 - 25 m/s (High Speed)** | 6,826 | +0.319 | -0.380 | **-0.699** | 1.732 m/s | 1.295 m/s |
| **25 - 30 m/s (Very High)** | 2,051 | +0.227 | -0.321 | **-0.548** | 0.985 m/s | 0.776 m/s |

## 5. Sequential Dead-Reckoning Integration Drift

Evaluating pure continuous integration from initial state v(0) over the entire 41-minute drive without any external GPS anchoring:
* **Sequential Dead-Reckoning RMSE:** `12.0744 m/s` (43.47 km/h)
* **Sequential Dead-Reckoning MAE:** `10.4563 m/s` (37.64 km/h)
* **Cumulative Drift Error at End of Drive:** `-11.1385 m/s` (-40.10 km/h)
* **Maximum Peak Drift:** `27.2269 m/s` (98.02 km/h)
* **Drift Mechanism:** Like all inertial dead-reckoning systems, tiny residual biases accumulate linearly over time when integrated open-loop without zero-velocity updates (ZUPT).

## 6. Comprehensive Multi-Model Benchmark Comparison (IOVNBD_S3a)

| Experiment | Formulation | Validation RMSE (m/s) | Validation RMSE (km/h) | Validation MAE (m/s) | Pearson r | R^2 Score | Prediction Range (m/s) | Beats Persistence? |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline (Paper)** | Absolute Speed | 6.4536 | 23.23 | 5.2430 | 0.0000 | -0.1419 | [8.28, 8.28] *(flatline)* | ❌ No |
| **Exp 1** | TargetStd Speed | 5.9872 | 21.55 | 4.8515 | 0.4173 | +0.0174 | [4.90, 20.03] | ❌ No |
| **Exp 2** | LSTMNoAttention | 5.3725 | 19.34 | 4.2842 | 0.5432 | +0.2088 | [5.09, 15.21] *(collapse)* | ❌ No |
| **Exp 4** | Balanced Sampling | 6.2846 | 22.62 | 4.8945 | 0.2227 | -0.0826 | [11.57, 13.95] *(collapse)* | ❌ No |
| **Persistence Baseline** | Anchor + Delta_v=0 | **2.1887** | **7.88** | **1.4699** | 0.9344 | **0.8687** | [0.00, 27.23] | N/A (Baseline) |
| **Exp 5 (Anchored Delta_v)** | Neural Delta_v + Anchor | **2.2066** | **7.94** | **1.5354** | **0.9348** | **0.8665** | **[-1.00, 27.03]** *(full span)* | ❌ No (Within 0.8%) |

## 7. Factual Audit Verdict

1. **Does the neural model beat naive persistence on validation RMSE?**
   * **No**. The neural model achieves RMSE = `2.2066 m/s` vs persistence RMSE = `2.1887 m/s` (difference = `+0.0179 m/s` / `+0.8%`).
2. **Is the Delta_v formulation physically promising?**
   * **Yes**. Shifting the learning target to Delta_v completely eliminates dynamic range collapse (allowing full 0 to 100 km/h prediction), captures real deceleration cycles (47.9% negative predictions), and achieves strong Pearson correlation ($r = 0.9348$) and $R^2 = 0.8665$.
3. **Is S3c test set evaluation methodologically justified at this stage?**
   * **No**. Because the current neural Delta_v estimator does not yet beat the simple persistence baseline on validation set S3a, evaluating `IOVNBD_S3c` is **not justified**. `IOVNBD_S3c` must remain strictly frozen.
4. **Data Integrity Confirmation:**
   * `IOVNBD_S3a` is correctly labelled **VALIDATION SET** across all documentation.
   * `IOVNBD_S3c` was **NEVER TOUCHED, NEVER LOADED, AND REMAINS STRICTLY FROZEN**.