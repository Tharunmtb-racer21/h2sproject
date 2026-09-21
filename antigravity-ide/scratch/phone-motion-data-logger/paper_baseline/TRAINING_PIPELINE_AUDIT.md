# PHASE 3 — SPEED ESTIMATION TRAINING PIPELINE AUDIT REPORT

**Module**: SIH26168 AI Speed Estimation Pipeline Verification  
**Dataset**: IO-VNBD Benchmark Dataset (Synchronized 50 Hz IMU & Racelogic VBOX Velocity Target)  

---

## 1. DATASET CONSTRUCTION & WINDOWING BREAKDOWN

Dataset sequence windows are constructed independently per session file to prevent cross-session boundary leakage:

| Split Assignment | Session ID | Driver & Category | 50 Hz Resampled Samples | Sequence Length ($T$) | Valid Windows ($T=200, \text{stride}=1$) | Input Tensor Shape | Target Tensor Shape |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TRAINING** | `IOVNBD_M` | Driver B (Defensive) | $308,799$ | $200$ ($4.0\text{ s}$) | $308,600$ | $(B, 200, 21)$ | $(B, 1)$ |
| **TRAINING** | `IOVNBD_S1` | Driver A (Defensive) | $258,725$ | $200$ ($4.0\text{ s}$) | $258,526$ | $(B, 200, 21)$ | $(B, 1)$ |
| **TRAINING** | `IOVNBD_S2` | Driver A (Defensive) | $460,055$ | $200$ ($4.0\text{ s}$) | $459,856$ | $(B, 200, 21)$ | $(B, 1)$ |
| **VALIDATION** | `IOVNBD_S3a` | Driver A (Defensive) | $123,100$ | $200$ ($4.0\text{ s}$) | $122,901$ | $(B, 200, 21)$ | $(B, 1)$ |
| **TESTING** | `IOVNBD_S3c` | Driver A (Defensive) | $185,910$ | $200$ ($4.0\text{ s}$) | **$185,711$ (FROZEN)** | $(B, 200, 21)$ | $(B, 1)$ |

### Aggregated Window Counts:
- **Total Training Set ($M + S1 + S2$)**: **$1,026,982\text{ windows}$**
- **Total Validation Set ($S3a$)**: **$122,901\text{ windows}$**
- **Total Testing Set ($S3c$)**: **$185,711\text{ windows}$ (Held out strictly until final evaluation)**

---

## 2. DATA LEAKAGE AUDIT & SAFEGUARDS VERIFICATION

- [x] **NaN / Inf Check**: $0$ NaNs or Infs present in input feature matrices or target vectors across all split loaders.
- [x] **Session Boundary Leakage**: Sliding windows are constructed *within* individual session matrices. No window spans across session boundaries.
- [x] **Target Label Exclusion**: Ground-truth `reference_speed` is stored strictly as the target label $y \in \mathbb{R}^{B \times 1}$; it is **completely excluded** from the input feature matrix $X \in \mathbb{R}^{B \times 200 \times 21}$.
- [x] **Normalization Scaler Isolation**: `PaperMinMaxScaler` bounds are fitted **strictly on the Training set** ($X_{\text{train}}$) and applied to Validation and Test sets without modifying fitted min/max bounds.
- [x] **Test Set Freeze**: Session `IOVNBD_S3c` is completely isolated from training, model selection, hyperparameter tuning, and scaler fitting.

---

## 3. MODEL ARCHITECTURES & TRAINABLE PARAMETER COUNTS

Three models were implemented in [`paper_baseline/models.py`](file:///c:/Users/Keerthana%20N/.gemini/antigravity-ide/scratch/phone-motion-data-logger/paper_baseline/models.py):

| Model Name | Class Name | Architecture Summary | Hidden Dims / Layers | Attention Mechanism | Dropout | Trainable Parameter Count |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. LSTMSelfAttention** | `LSTMSelfAttention` | LSTM Encoder + Temporal Self-Attention + FC Regressor | 2 LSTM Layers ($h=128$) + FC ($128 \to 64 \to 1$) | Temporal Scaled Dot-Product Self-Attention over $T=200$ | $0.2$ | **267,265** |
| **2. LSTMNoAttention** | `LSTMNoAttention` | LSTM Encoder (Final Hidden State $h_T$) + FC Regressor | 2 LSTM Layers ($h=128$) + FC ($128 \to 64 \to 1$) | None (Final timestep state $h_{200}$) | $0.2$ | **217,729** |
| **3. SimpleBaselineMLP** | `SimpleBaselineMLP` | Temporal Global Average Pooling + FC Regressor | Global Avg Pool ($T \to 1$) + FC ($21 \to 128 \to 64 \to 1$) | None (Temporal Average Pooling) | $0.2$ | **11,137** |

*Note on Specifications*: Any unspecified hyperparameters (such as hidden dimension $h=128$ and dropout $=0.2$) are labeled as: *"Implementation assumption — not explicitly specified in the source."*

---

## 4. FORWARD & BACKWARD PASS VERIFICATION RESULTS

Executed on a real training batch of $32$ sequence windows ($X \in \mathbb{R}^{32 \times 200 \times 21}$, $y \in \mathbb{R}^{32 \times 1}$):

| Model Name | Forward Output Shape | MSE Loss ($\text{m/s}^2$) | Backward Pass Gradients | Optimizer Step | Gate Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LSTMSelfAttention`** | `torch.Size([32, 1])` | $65.4797$ | **Valid (Non-null, Finite, No NaN/Inf)** | **Successful** | **PASS** |
| **`LSTMNoAttention`** | `torch.Size([32, 1])` | $65.3838$ | **Valid (Non-null, Finite, No NaN/Inf)** | **Successful** | **PASS** |
| **`SimpleBaselineMLP`** | `torch.Size([32, 1])` | $65.9142$ | **Valid (Non-null, Finite, No NaN/Inf)** | **Successful** | **PASS** |

---

## 5. GATE DECISION SUMMARY

```
DATASET: PASS
LEAKAGE: PASS
MODELS: PASS
FORWARD PASS: PASS
READY FOR TRAINING: YES
```
