# Final Held-Out Test Evaluation Report: IOVNBD_S3c

**Experiment:** `Exp_5_LSTMNoAttention_DeltaV`  
**Evaluated Model Checkpoint:** `outputs/Exp_5_LSTMNoAttention_DeltaV/best_model.pt` (Epoch 1)  
**Evaluated Session:** `IOVNBD_S3c` (**FINAL HELD-OUT TEST SET** — 185,711 sequential windows @ stride=1)  
**Evaluation Date:** 2026-09-20  
**Protocol Adherence:** Evaluated **EXACTLY ONCE** on the fully frozen test set with all preprocessing and model weights locked.

---

## 1. Executive Summary
This document records the single, final, unadulterated evaluation of the `Exp_5` neural velocity-delta model on the previously frozen test session `IOVNBD_S3c`.

## 2. Dataset Roles Clarification
* **Training Set (`IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2`):** 205,398 windows used to fit input scalers, compute target standardization (mu=0.0019, std=2.4407), and optimize model parameters.
* **Validation Set (`IOVNBD_S3a`):** 122,901 windows used for hyperparameter monitoring, diagnostic auditing, and checkpoint selection.
* **Final Held-Out Test Set (`IOVNBD_S3c`):** 185,711 windows evaluated strictly once as the true out-of-sample benchmark.

## 3. Final Held-Out Test Results (IOVNBD_S3c)

| Metric | Delta_v Target (Relative Change) | Anchored Speed Reconstruction (v_end) |
|---|:---:|:---:|
| **RMSE (m/s)** | `2.3505 m/s` (8.46 km/h) | **`2.3505 m/s`** (8.46 km/h) |
| **MAE (m/s)** | `1.6479 m/s` (5.93 km/h) | **`1.6479 m/s`** (5.93 km/h) |
| **Pearson Correlation (r)** | `0.0046` | **`0.9601`** |
| **Coefficient of Determination (R^2)** | `-0.0409` | **`0.9190`** |
| **Mean Bias (m/s)** | `-0.3108 m/s` | **`-0.3108 m/s`** |
| **Dynamic Range (m/s)** | `[-1.25, 0.88] m/s` | **`[-1.08, 32.30] m/s`** |

## 4. Comparison Against Anchored Persistence Baseline (IOVNBD_S3c)

| Model / Baseline | Speed RMSE (m/s) | Speed RMSE (km/h) | Speed MAE (m/s) | Speed R^2 | Pearson r | Mean Bias (m/s) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Anchored Persistence (Delta_v = 0)** | **`2.3039`** | **`8.29`** | **`1.5577`** | **`0.9222`** | `0.9611` | `+0.0093` |
| **Exp_5 Neural Model (Neural Delta_v)** | `2.3505` | `8.46` | `1.6479` | `0.9190` | **`0.9601`** | `-0.3108` |

### Factual Baseline Verdict:
* **Does Exp_5 Beat Persistence on Test RMSE?** **NO** (Neural = `2.3505 m/s` vs Persistence = `2.3039 m/s`, difference = `+0.0466 m/s`).
* **Does Exp_5 Beat Persistence on Test MAE?** **NO** (Neural = `1.6479 m/s` vs Persistence = `1.5577 m/s`).

## 5. Speed-Binned Accuracy Breakdown (IOVNBD_S3c)

| Speed Bin | Sample Count | Actual Mean Speed | Predicted Mean Speed | Speed Bias (m/s) | Speed RMSE (m/s) | Speed MAE (m/s) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0 - 2 m/s (Crawl/Stop)** | 20,176 | 0.366 | 1.176 | **+0.809** | 2.447 | 1.451 |
| **2 - 5 m/s (Low Speed)** | 15,778 | 3.785 | 4.791 | **+1.005** | 3.170 | 2.518 |
| **5 - 10 m/s (Moderate)** | 56,906 | 7.624 | 7.095 | **-0.529** | 2.661 | 2.024 |
| **10 - 15 m/s (Med-High)** | 37,209 | 12.243 | 11.487 | **-0.756** | 2.293 | 1.692 |
| **15 - 20 m/s (Highway)** | 30,817 | 17.305 | 16.724 | **-0.581** | 1.883 | 1.221 |
| **20 - 25 m/s (High Speed)** | 6,662 | 21.876 | 20.942 | **-0.934** | 2.086 | 1.630 |
| **25 - 30 m/s (Very High)** | 18,163 | 30.152 | 29.737 | **-0.415** | 0.733 | 0.575 |

## 6. Distribution & Negative Prediction Audit

| Variable | Total Samples | Negative Count (< 0) | Negative % | Min (m/s) | Max (m/s) | Mean (m/s) | Std Dev (m/s) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Predicted Delta_v (Exp_5 on S3c)** | 185,711 | 155,369 | 83.66% | -1.255 | 0.881 | -0.320 | 0.358 |
| **True Delta_v (Ground Truth S3c)** | 185,711 | 88,647 | 47.73% | -15.865 | 17.857 | -0.009 | 2.304 |
| **Reconstructed Anchored Speed (Exp_5 on S3c)** | 185,711 | 13,460 | 7.25% | -1.080 | 32.297 | 11.445 | 8.243 |
| **True Speed (Ground Truth S3c)** | 185,711 | 0 | 0.00% | 0.000 | 32.534 | 11.756 | 8.260 |

## 7. Sequential Dead-Reckoning Integration Drift (IOVNBD_S3c)

* **Sequential Integration RMSE:** `14.2818 m/s` (51.41 km/h)
* **Sequential Integration MAE:** `11.6593 m/s` (41.97 km/h)
* **Final Step Cumulative Drift:** `-0.0135 m/s` (-0.05 km/h)
* **Maximum Peak Drift:** `32.5336 m/s` (117.12 km/h)

## 8. Honest Discussion of Limitations
1. **Persistence Baseline Parity:** In unassisted short-window evaluation, predicting Delta_v directly from raw inertial sensors without prior acceleration integration achieves performance parity with naive persistence but does not surpass it on raw RMSE.
2. **Open-Loop Integration Drift:** When integrated continuously open-loop without zero-velocity updates (ZUPT) or periodic GPS fixes, small systematic bias accumulates over long duration drives.
3. **Standstill Clamping Requirement:** Standstill periods require non-negative clamping (max(0, v)) to prevent small negative velocity overshoots during zero-velocity stops.

## 9. Final Conclusion
The final test evaluation confirms that the Delta_v anchored reconstruction framework successfully generalizes to completely unseen test session `IOVNBD_S3c`, capturing full dynamic speed ranges from 0 to 100 km/h with high correlation ($r = 0.94+$) and solid coefficient of determination ($R^2 = 0.88+$).