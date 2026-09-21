# Diagnostic Report: Exp_2 (LSTMNoAttention + TargetStd) on IOVNBD_S3a

**Date:** 2026-09-20  
**Audit Type:** Read-Only Model Diagnostic  
**Subject:** `Exp_2_LSTMNoAttention_TargetStd` (`outputs/Exp_2_LSTMNoAttention_TargetStd/best_model.pt`)  
**Evaluation Set:** `IOVNBD_S3a` (Full validation set: 122,901 sequences, stride=1, sequence length=200)  
**Test Set Protocol:** `IOVNBD_S3c` remains **STRICTLY FROZEN, UNLOADED, AND UNTOUCHED**  

---

## 1. Prediction Distribution (Physical m/s and km/h)
* **Mean:** `9.2109 m/s` (33.16 km/h)
* **Standard Deviation ($\sigma$):** `2.1113 m/s` (7.60 km/h)
* **Minimum:** `5.0948 m/s` (18.34 km/h)
* **Maximum:** `15.2076 m/s` (54.75 km/h)
* **Dynamic Span:** `10.1128 m/s` (36.41 km/h)

## 2. Actual Target Distribution (Physical m/s and km/h)
* **Mean:** `10.5447 m/s` (37.96 km/h)
* **Standard Deviation ($\sigma$):** `6.0400 m/s` (21.74 km/h)
* **Minimum:** `0.0000 m/s` (0.00 km/h)
* **Maximum:** `27.2269 m/s` (98.02 km/h)
* **Dynamic Span:** `27.2269 m/s` (98.02 km/h)

---

## 3. Prediction vs. Actual Scatter Regression Line (OLS)
* **Slope ($\beta_1$):** `0.189878` (Ideal calibration: `1.0000`)
* **Intercept ($\beta_0$):** `7.208678 m/s` (Ideal calibration: `0.0000 m/s`)
* **Regression Equation:** $\hat{y} = 0.1899 \cdot y_{\text{actual}} + 7.2087\text{ m/s}$

---

## 4. Bias, RMSE, and MAE by Speed Bins

| Speed Bin | Sequence Count ($N$) | True Mean ($m/s$) | Pred Mean ($m/s$) | Mean Bias ($m/s$) | RMSE ($m/s$) | RMSE ($km/h$) | MAE ($m/s$) | MAE ($km/h$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0 – 2 m/s** (Crawl / Stop) | 14,199 | 0.3182 | 6.6662 | **+6.3480** | 6.5107 | 23.44 | 6.3480 | 22.85 |
| **2 – 5 m/s** (Low Speed) | 7,951 | 3.8958 | 8.2642 | **+4.3685** | 4.8794 | 17.57 | 4.3685 | 15.73 |
| **5 – 10 m/s** (Moderate) | 32,532 | 7.6917 | 8.8748 | **+1.1830** | 2.5746 | 9.27 | 2.1026 | 7.57 |
| **10 – 15 m/s** (Medium-High) | 44,036 | 12.3611 | 9.5711 | **-2.7900** | 3.4956 | 12.58 | 2.9258 | 10.53 |
| **15 – 20 m/s** (Highway) | 15,306 | 17.0564 | 10.6292 | **-6.4273** | 6.7184 | 24.19 | 6.4273 | 23.14 |
| **20 – 25 m/s** (High Speed) | 6,826 | 22.3067 | 11.0341 | **-11.2727** | 11.4624 | 41.26 | 11.2727 | 40.58 |
| **25 – 30 m/s** (Very High) | 2,051 | 25.6319 | 11.4436 | **-14.1883** | 14.2203 | 51.19 | 14.1883 | 51.08 |
| **Total / Overall** | **122,901** | **10.5447** | **9.2109** | **-1.3338** | **5.3725** | **19.34** | **4.2842** | **15.42** |

---

## 5. Global Correlation and Goodness-of-Fit
* **Pearson Correlation ($r$):** `0.543207`  
  * *Interpretation:* Demonstrates moderate-to-strong monotonic tracking of acceleration and deceleration dynamics.
* **Coefficient of Determination ($R^2$):** `0.208803`  
  * *Interpretation:* Best $R^2$ among all baseline models, but severely penalized by the compressed dynamic range.

---

## 6. Dynamic Range Compression Assessment
* **Status:** **HEAVILY COMPRESSED (Regression-to-the-Mean)**
* **Evidence:**
  1. Actual ground truth spans `0.0000` to `27.2269 m/s` ($\Delta = 27.23\text{ m/s}$ / $98.02\text{ km/h}$).
  2. Exp_2 predictions only span `5.0948` to `15.2076 m/s` ($\Delta = 10.11\text{ m/s}$ / $36.41\text{ km/h}$).
  3. The model only utilizes **$37.1\%$** of the actual physical dynamic span.
  4. The standard deviation of predictions ($\sigma_{\text{pred}} = 2.11\text{ m/s}$) is only **$35.0\%$** of the true standard deviation ($\sigma_{\text{actual}} = 6.04\text{ m/s}$).

---

## 7. Root Technical Cause & Target for Future Experiments
* **Single Most Likely Technical Cause:**
  **Target Distribution Skew combined with Standard Uniform MSE Loss.**
  * In the training dataset (`IOVNBD_M`, `S1`, `S2`), **63.1%** of samples are concentrated between $5\text{ m/s}$ and $15\text{ m/s}$.
  * Under standard uniform MSE loss, optimizing for global squared error causes gradient descent to minimize penalty by predicting the conditional expectation near the dataset mean ($\approx 8.3 - 9.2\text{ m/s}$).
  * The network is effectively "disincentivized" from predicting extreme tails ($0-2\text{ m/s}$ stops and $>20\text{ m/s}$ highway sprints) because errors in rare bins contribute minimally to the global unweighted loss.
