# Stage 4: Experiment 3 (Exp_3) Design & Investigation Report

**Subject:** Investigation & Formal Proposal for `Exp_3` to Reduce Speed-Estimation Bias  
**Objective:** Mitigate the regression-to-the-mean failure modes identified on `IOVNBD_S3a`:
* Overestimation at low speeds ($0 - 2\text{ m/s}$) by $+6.1\text{ to }+7.2\text{ m/s}$
* Underestimation at high speeds ($>15 - 20\text{ m/s}$) by $-7.6\text{ to }-16.6\text{ m/s}$
* Dynamic range compression around the training set mean ($8.31\text{ m/s}$)

**Strict Anti-Leakage Safeguard:** `IOVNBD_S3c` is **100% FROZEN, NEVER ACCESSED, AND NEVER EVALUATED**.

---

## 1. Phase A — Empirical Investigation Findings

### 1.1 Training Target Distribution & Severe Class Imbalance
Analysis of all **1,026,982 training sequences** (`IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2`) reveals extreme density concentration in the moderate speed band ($5 - 15\text{ m/s}$):

| Speed Regime (True Speed) | Training Count | Training Pct (%) | S3a Validation Count | S3a Validation Pct (%) | Empirical Imbalance Ratio |
|---|:---:|:---:|:---:|:---:|:---:|
| **0 – 2 m/s (Crawl / Stop)** | 175,579 | 17.10% | 14,199 | 11.55% | $1.0\times$ (Baseline) |
| **2 – 5 m/s (Low Speed)** | 101,126 | 9.85% | 7,951 | 6.47% | $0.58\times$ |
| **5 – 10 m/s (Moderate Urban)** | **385,471** | **37.53%** | 32,532 | 26.47% | **$2.20\times$ (DOMINANT MODE)** |
| **10 – 15 m/s (Medium-High)** | **262,711** | **25.58%** | 44,036 | 35.83% | **$1.50\times$ (SUB-DOMINANT)** |
| **15 – 20 m/s (Highway)** | 68,491 | 6.67% | 15,306 | 12.45% | $0.39\times$ (Sparse) |
| **20 – 25 m/s (High Speed)** | 28,141 | 2.74% | 6,826 | 5.55% | $0.16\times$ (Rare) |
| **25 – 30 m/s (Very High)** | 5,463 | 0.53% | 2,051 | 1.67% | **$0.03\times$ (EXTREMELY RARE)** |
| **Total** | **1,026,982** | **100.0%** | **122,901** | **100.0%** | — |

**Finding:** **63.1%** of all training samples reside between $5 - 15\text{ m/s}$, whereas high speeds ($>20\text{ m/s}$) represent only **3.27%** of the data. Under standard unweighted MSE loss, the gradient signals from the dominant $5 - 15\text{ m/s}$ regime overwhelmingly dominate optimization, forcing the network to minimize aggregate loss by predicting near the training mean ($8.31\text{ m/s}$).

---

### 1.2 Stationary Detection & The Severe Hazard of Post-Processing ZUPT
We investigated whether stationary periods ($v < 0.5\text{ m/s}$) can be reliably classified from smartphone IMU rolling variance features on the training set:

```
+-------------------------------------------------------------------------------+
|              TRAINING SPLIT STATIONARY CLASSIFICATION PERFORMANCE             |
+-------------------+----------------+---------------+--------------------------+
| Variance Threshold| Precision (%)  | Recall (%)    | False Stationary (Stops) |
+-------------------+----------------+---------------+--------------------------+
| accel_mag_var < 0.005 | 35.1%      | 11.5%         | 26,040 samples           |
| accel_mag_var < 0.010 | 38.3%      | 23.7%         | 47,020 samples           |
| accel_mag_var < 0.020 | 35.1%      | 29.7%         | 67,694 samples           |
| accel_mag_var < 0.050 | 27.2%      | 39.0%         | 128,260 samples          |
+-------------------+----------------+---------------+--------------------------+
```

#### Why Naive ZUPT Post-Processing is Catastrophic:
1. **The Highway Cruising Confounder:** When a vehicle cruises at constant speed on a smooth paved highway ($20 - 25\text{ m/s}$), acceleration variance $\text{accel\_mag\_var}$ and gyroscope variance can be as low as when the car is idling at a red light.
2. **False Stop Injections:** A hard rule that clamps speed to $0\text{ m/s}$ whenever $\text{accel\_mag\_var} < 0.01$ causes **47,020 false stops** in the training data, collapsing valid highway cruising to $0\text{ m/s}$.
3. **Discontinuous Prediction Jumps:** Post-processing clamps create non-physical step discontinuities ($20\text{ m/s} \rightarrow 0\text{ m/s} \rightarrow 20\text{ m/s}$), destroying downstream dead-reckoning trajectory integration.
4. **Conclusion:** ZUPT **must NOT be applied as an ad-hoc post-processing clamp** based solely on IMU magnitude variance.

---

### 1.3 Loss Function Comparative Evaluation

| Loss Function | Mathematical Form | Gradient Behavior | Suitability for Speed Bias Mitigation |
|---|---|---|---|
| **1. Standard MSE** | $L = (y_{std} - \hat{y}_{std})^2$ | $\frac{\partial L}{\partial \hat{y}} = -2(y - \hat{y})$ | **Poor:** Suffers from dominant-mode pull ($8.31\text{ m/s}$); ignores rare high-speed bins. |
| **2. Huber / Smooth L1** | $L_\delta = \begin{cases} \frac{1}{2}e^2 & \|e\| \le \delta \\ \delta(\|e\| - \frac{1}{2}\delta) & \text{else} \end{cases}$ | Constant gradient for large errors | **Insufficient:** Robust against outliers, but actually *reduces* gradient for extreme high-speed errors, worsening underestimation. |
| **3. Smoothed Speed-Weighted MSE (Proposed)** | $L = w(y) \cdot (y_{std} - \hat{y}_{std})^2$ | Scaled by sample rarity $w(y)$ | **OPTIMAL:** Actively counterbalances sample imbalance without altering network architecture or introducing inference latency. |

---

## 2. Phase B — Formal Experiment Proposal for Exp_3

### 2.1 Proposed Experiment Title
**`Exp_3 — Balanced Smooth Speed-Weighted Loss (BW-MSE) for Dynamic Range Expansion`**

### 2.2 Exact Loss Function Formulation
Let $y_{raw} \in [0, 32.5\text{ m/s}]$ be the reference speed, and $y_{std} = (y_{raw} - 8.3119106) / 5.5192132$ be the standardized target.

The loss for sequence sample $i$ is:
$$\mathcal{L}_i = w(y_{raw, i}) \cdot \left( \hat{y}_{std, i} - y_{std, i} \right)^2$$

Where the sample weight $w(y_{raw})$ is determined by a continuous power-law smoothed inverse frequency derived **strictly from the training distribution**:
$$w(y) = \frac{1}{\mathcal{Z}} \cdot \left( \frac{\bar{f}}{f_{\text{train}}(y)} \right)^\gamma$$

* **Smoothing Exponent ($\gamma$):** $\gamma = 0.35$ (dampens raw inverse-frequency to prevent extreme gradient spikes on rare bins).
* **Normalization Constant ($\mathcal{Z}$):** Chosen such that the expected weight across the training split is exactly $1.0$:
  $$\mathbb{E}_{y \sim \mathcal{D}_{\text{train}}}[w(y)] = 1.0000$$

### Verified Training Bin Weights ($\gamma = 0.35$):
* **0 – 2 m/s:** $w = \mathbf{1.0414}$
* **2 – 5 m/s:** $w = \mathbf{1.2632}$
* **5 – 10 m/s:** $w = \mathbf{0.7908}$ (downweighted dominant mode)
* **10 – 15 m/s:** $w = \mathbf{0.9044}$
* **15 – 20 m/s:** $w = \mathbf{1.4478}$ (boosted highway transition)
* **20 – 25 m/s:** $w = \mathbf{1.9766}$ (boosted high speed)
* **25 – 30 m/s:** $w = \mathbf{3.5082}$ (boosted extreme speed)

---

### 2.3 Locked Configuration & Controls
To ensure a strictly controlled single-variable experiment:

1. **Architecture:** `LSTMNoAttention` (217,729 parameters) — identical to `Exp_2b`.
2. **Target Standardization:** RETAINED ($\mu_{\text{train}} = 8.3119106\text{ m/s}$, $\sigma_{\text{train}} = 5.5192132\text{ m/s}$).
3. **Training Grid & Window:** 50 Hz, $T=200$, 21 input features.
4. **Training Stride & Batch Size:** Stride = 5 (205,398 windows), Batch Size = 32.
5. **Optimizer & Learning Rate:** Adam, $\text{lr} = 0.0008$, ReduceLROnPlateau (factor=0.5, patience=3).
6. **Seed:** 42.
7. **Training Budget:** Controlled 5-epoch pilot.
8. **Validation Protocol:** `IOVNBD_S3a` evaluated with stride=1 (all 122,901 sequences, 481 batches @ batch size 256).
9. **Test Set Safeguard:** `IOVNBD_S3c` remains **100% frozen and unloaded**.
10. **Output Isolation:** `outputs/Exp_3_BalancedWeightedMSE/` (isolated from all prior runs).

---

### 2.4 Expected Benefits, Risks & Mitigation

| Potential Risk | Technical Cause | Built-in Mitigation Strategy |
|---|---|---|
| **Gradient Explosion on Rare High Speeds** | Extreme inverse frequency weights ($>25\times$) on 25–30 m/s bin | Power-law dampening ($\gamma=0.35$) caps the maximum weight to $3.51\times$; gradient clipping ($\text{max\_norm}=1.0$). |
| **Error Inflation in 5–10 m/s Regime** | Downweighting dominant mode ($0.79\times$) could slightly raise urban RMSE | The weight reduction is mild ($0.79\times$), preserving strong supervision while unlocking highway speed gradients. |
| **Overfitting on Validation Set** | Loss weighting might alter convergence speed | Checkpointing automatically preserves the minimum S3a validation loss model (`best_model.pt`). |

---

### 2.5 Planned Ablation Matrix (Exp_3 Suite)

1. **`Exp_3a (Main Proposed)`:** `LSTMNoAttention` + TargetStd + Stride 5 + **Smoothed Bin-Weighted MSE ($\gamma=0.35$)**
2. **`Exp_3b (Ablation)`:** `LSTMNoAttention` + TargetStd + Stride 5 + **Huber Loss ($\delta=1.0$)** (evaluates whether outlier robustness alone helps)
3. **`Exp_3c (Ablation)`:** `LSTMSelfAttention` + TargetStd + Stride 5 + **Smoothed Bin-Weighted MSE** (tests loss weighting on self-attention architecture)

---

## 3. Recommended Next Action

**RECOMMENDATION:** Proceed with **`Exp_3a` (Smoothed Bin-Weighted MSE on `LSTMNoAttention` with Stride 5)** as the next strictly controlled 5-epoch pilot.

This provides the cleanest, safest method to directly target the verified root cause (training class density imbalance) without modifying architecture or risking highway false-stops.
