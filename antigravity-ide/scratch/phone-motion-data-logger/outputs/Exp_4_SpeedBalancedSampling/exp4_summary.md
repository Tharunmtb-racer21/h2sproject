# Exp_4 Summary: LSTMNoAttention + TargetStd + Speed-Balanced Training Sampling

**Execution Date:** 2026-09-20  
**Status:** **Completed 5 Full Epochs**  
**Output Directory:** `outputs/Exp_4_SpeedBalancedSampling/`  
**Test Set Protocol:** `IOVNBD_S3c` remains **STRICTLY FROZEN, UNLOADED, AND NEVER EVALUATED**.

---

## 1. Configuration
* **Architecture:** `LSTMNoAttention` (217,729 parameters, 21 features, sequence length=200, 2 layers, hidden=128, dropout=0.2)
* **Sampling Strategy:** `torch.utils.data.WeightedRandomSampler` (equal 14.2857% probability per speed bin across the 7 speed regimes)
* **Target Preprocessing:** Train-only Z-score standardization ($\mu_{\text{train}} = 8.3119106\text{ m/s}$, $\sigma_{\text{train}} = 5.5192132\text{ m/s}$)
* **Loss Function:** Standard unweighted MSE on standardized targets
* **Optimizer & LR:** Adam ($\text{lr} = 0.0008$), ReduceLROnPlateau
* **Data Splits:** Train on `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2` (205,398 stride-5 windows); Validate on `IOVNBD_S3a` (122,901 stride-1 windows)

---

## 2. Epoch-by-Epoch Validation Results on IOVNBD_S3a

| Epoch | Train Std MSE | Val Std MSE | Val RMSE ($m/s$) | Val RMSE ($km/h$) | Val MAE ($m/s$) | $R^2$ Score | Pearson $r$ | Pred Mean ($m/s$) | Pred Std ($m/s$) | Pred Range ($m/s$) | LR |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1\*** | **2.7278** | **1.2966** | **6.2846** | **22.62** | **4.8945** | **-0.0826** | **+0.2227** | **12.3902** | **0.1541** | **[11.57, 13.95]** | 0.0008 |
| 2 | 2.7168 | 1.3636 | 6.4449 | 23.20 | 5.0461 | -0.1386 | +0.2235 | 12.7932 | 0.0001 | [12.79, 12.79] | 0.0008 |
| 3 | 2.7202 | 1.3307 | 6.3668 | 22.92 | 4.9710 | -0.1112 | +0.1322 | 12.5586 | 0.0000 | [12.56, 12.56] | 0.0008 |
| 4 | 2.7089 | 1.3293 | 6.3634 | 22.91 | 4.9678 | -0.1100 | +0.0561 | 12.5477 | 0.0000 | [12.55, 12.55] | 0.0008 |
| 5 | 2.7185 | 1.3754 | 6.4728 | 23.30 | 5.0737 | -0.1485 | -0.0897 | 12.8719 | 0.0000 | [12.87, 12.87] | 0.0008 |

*\* Best checkpoint saved at Epoch 1 (Val RMSE = 6.2846 m/s).*

---

## 3. Findings & Comparison Against Exp_2

1. **Failure of Balanced Sampling on Static Unanchored Speed:** Over-sampling rare high-speed bins (up to 26.8x multiplier on 25–30 m/s) shifted the model's mean prediction from $9.21\text{ m/s} \to 12.39 - 12.87\text{ m/s}$.
2. **Prediction Dynamic Range Compression Worsened:** Because the network still lacked an absolute velocity anchor, it collapsed even tighter around the new weighted sampling mean ($[11.57, 13.95]\text{ m/s}$ in Epoch 1, collapsing to a single constant point $\approx 12.55\text{ m/s}$ in Epochs 3–5).
3. **Scientific Implication:** Confirms the Stage 5 diagnostic finding: **Target imbalance is not the root cause of dynamic range collapse.** The root cause is the fundamental lack of Galilean absolute velocity observability from local IMU windows.
