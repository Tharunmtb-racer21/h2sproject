# Design & Pre-Flight Report: Exp_4 (Speed-Balanced Training Sampling)

**Experiment Identifier:** `Exp_4_LSTMNoAttention_TargetStd_BalancedSampling`  
**Purpose:** Address the severe training target distribution skew and prediction dynamic range compression documented in Exp_2 by enforcing speed-balanced training sampling without modifying the standard MSE loss function.  
**Date:** 2026-09-20  
**Status:** **DESIGN & PRE-FLIGHT ONLY (NO TRAINING RUN)**  

---

## 1. Locked Pipeline Constants & Controlled Variable

| Component | Status | Specification |
|---|:---:|---|
| **Architecture** | **LOCKED (Exp 2)** | `LSTMNoAttention` (2 LSTM layers, hidden_dim=128, dropout=0.2, linear projection $\to$ 1) |
| **Parameter Count** | **LOCKED (Exp 2)** | **217,729 parameters** |
| **Input Features** | **LOCKED (Exp 2)** | **21 features** (IMU linear accelerations, angular velocities, orientations, derived magnitudes, cell tower signal metrics) |
| **Target Preprocessing** | **LOCKED (Exp 2)** | Train-only Z-score standardization ($\mu_{\text{train}} = 8.3119106\text{ m/s}$, $\sigma_{\text{train}} = 5.5192132\text{ m/s}$) |
| **Loss Function** | **LOCKED (Standard MSE)** | Standard Mean Squared Error ($\mathcal{L} = \frac{1}{B} \sum (y_{std} - \hat{y}_{std})^2$). **No loss weighting applied.** |
| **Optimizer & LR** | **LOCKED (Exp 2)** | Adam ($\text{lr} = 0.0008$), ReduceLROnPlateau (factor=0.5, patience=3, min_lr=1e-5) |
| **Training Split** | **LOCKED** | `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2` (100% isolated) |
| **Validation Split** | **LOCKED** | `IOVNBD_S3a` (**122,901 windows**, stride=1, sequential inference) |
| **Test Split Safeguard** | **FROZEN** | `IOVNBD_S3c` is **NEVER LOADED, NEVER ACCESSED, NEVER TOUCHED** |
| **Controlled Variable** | **NEW IN EXP_4** | **Speed-Balanced Training Sampling (`WeightedRandomSampler`)** |

---

## 2. Training Dataset Speed Bin Distribution (M + S1 + S2)

Across the three training sessions (`IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2`), the exact number of sequence windows ($T=200$, $dt=0.02\text{ s}$) available in each speed bin is:

| Speed Bin ($m/s$) | Speed Bin ($km/h$) | Regime Description | Stride 1 Windows | Stride 1 Share | Stride 5 Windows | Stride 5 Share |
|---|---|---|:---:|:---:|:---:|:---:|
| **0 – 2** | 0 – 7.2 | Crawl / Stop | 175,579 | 17.10% | 35,099 | 17.09% |
| **2 – 5** | 7.2 – 18 | Low Speed | 101,124 | 9.85% | 20,241 | 9.85% |
| **5 – 10** | 18 – 36 | Moderate Speed | 385,473 | 37.53% | 77,097 | 37.54% |
| **10 – 15** | 36 – 54 | Medium-High Speed | 262,711 | 25.58% | 52,544 | 25.58% |
| **15 – 20** | 54 – 72 | Highway Speed | 68,491 | 6.67% | 13,692 | 6.67% |
| **20 – 25** | 72 – 90 | High Speed | 28,141 | 2.74% | 5,633 | 2.74% |
| **25 – 30** | 90 – 108 | Very High Speed | 5,463 | 0.53% | 1,092 | 0.53% |
| **Total** | **0 – 108 km/h** | **Full Training Set** | **1,026,982** | **100.00%** | **205,398** | **100.00%** |

> [!IMPORTANT]
> In the natural training distribution, **63.12%** of all data is concentrated in the $5–15\text{ m/s}$ band, whereas high-speed driving ($>20\text{ m/s}$) accounts for only **3.27%** (and $>25\text{ m/s}$ is a mere **0.53%**). Under uniform sampling, the network sees a $>25\text{ m/s}$ window only once every 188 samples.

---

## 3. Proposed Balanced-Sampling Mechanism

### Mathematical Formulation
Let $B = 7$ denote the number of discrete speed bins $b \in \{1, \dots, 7\}$.  
Let $N_b$ be the total count of training sequence windows falling into bin $b$, and $N = \sum_{b=1}^B N_b$.

Each training sample $i \in \{1, \dots, N\}$ with raw physical speed target $y_i$ is mapped to bin $b(i)$. The sample selection weight $w_i$ is defined as:
$$w_i = \frac{1}{N_{b(i)}}$$

Under `torch.utils.data.WeightedRandomSampler(weights=w, num_samples=N, replacement=True, generator=torch.Generator().manual_seed(42))`, the probability $p_i$ of drawing sample $i$ at any step is:
$$p_i = \frac{w_i}{\sum_{j=1}^N w_j} = \frac{\frac{1}{N_{b(i)}}}{\sum_{k=1}^B N_k \cdot \frac{1}{N_k}} = \frac{1}{B \cdot N_{b(i)}}$$

The aggregate probability $P(\text{Bin } b)$ of selecting *any* sample from bin $b$ is:
$$P(\text{Bin } b) = \sum_{i \in \text{Bin } b} p_i = N_b \cdot \frac{1}{B \cdot N_b} = \frac{1}{B} = \frac{1}{7} \approx 14.2857\%$$

### Probability & Odds-Ratio Shift Table (Stride=5, $N=205,398$)

| Speed Bin ($m/s$) | Raw Window Count ($N_b$) | Standard Uniform Probability $P(b)$ | Balanced Sampling Probability $P(b)$ | Sampling Multiplier (Odds Ratio) | Expected Windows / Epoch (Batch 32) |
|---|:---:|:---:|:---:|:---:|:---:|
| **0 – 2** | 35,099 | 17.09% | **14.29%** | **0.84x** | 29,343 |
| **2 – 5** | 20,241 | 9.85% | **14.29%** | **1.45x** | 29,343 |
| **5 – 10** | 77,097 | 37.54% | **14.29%** | **0.38x** *(Downsampled)* | 29,343 |
| **10 – 15** | 52,544 | 25.58% | **14.29%** | **0.56x** *(Downsampled)* | 29,343 |
| **15 – 20** | 13,692 | 6.67% | **14.29%** | **2.14x** *(Oversampled)* | 29,343 |
| **20 – 25** | 5,633 | 2.74% | **14.29%** | **5.21x** *(Oversampled)* | 29,343 |
| **25 – 30** | 1,092 | 0.53% | **14.29%** | **26.87x** *(Oversampled)* | 29,343 |

---

## 4. Empirical Pre-Flight Verification

The sampling mechanism was tested in a read-only trial over the first 100 mini-batches ($3,200$ windows drawn with fixed seed `42`):

```text
=== EMPIRICAL SAMPLING VERIFICATION (First 100 Batches = 3,200 Windows) ===
0-2 m/s      | Theoretical: 14.29% | Empirical: 14.03% ( 449 windows)
2-5 m/s      | Theoretical: 14.29% | Empirical: 14.56% ( 466 windows)
5-10 m/s     | Theoretical: 14.29% | Empirical: 13.97% ( 447 windows)
10-15 m/s    | Theoretical: 14.29% | Empirical: 15.88% ( 508 windows)
15-20 m/s    | Theoretical: 14.29% | Empirical: 13.66% ( 437 windows)
20-25 m/s    | Theoretical: 14.29% | Empirical: 14.22% ( 455 windows)
25-30 m/s    | Theoretical: 14.29% | Empirical: 13.69% ( 438 windows)
```

---

## 5. Leakage & Isolation Safeguards Verification

1. **Zero Validation Leakage:**
   * Training sampler weights $w_i$ are computed strictly from the training dataset targets (`IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2`).
   * `IOVNBD_S3a` is never passed to `WeightedRandomSampler` and is evaluated sequentially with `shuffle=False`, `stride=1` (122,901 windows).
2. **Zero Test Leakage:**
   * `IOVNBD_S3c` is strictly excluded from `TRAIN_SESSIONS`, `VAL_SESSIONS`, and is never loaded into memory.
3. **Reproducibility:**
   * Sampler uses a dedicated PyTorch generator seeded with `torch.Generator().manual_seed(42)`.
