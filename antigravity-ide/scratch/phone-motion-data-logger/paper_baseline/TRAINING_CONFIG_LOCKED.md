# LOCKED TRAINING CONFIGURATION FILE

**Module**: SIH26168 Phase 3 Speed Estimation Training  
**File Path**: `paper_baseline/TRAINING_CONFIG_LOCKED.md`  
**Status**: LOCKED & FROZEN  

---

## 1. DATASET & PREPROCESSING CONFIGURATION

| Parameter | Configuration Value | Classification |
| :--- | :--- | :--- |
| **Training Sessions** | `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2` | **SOURCE-SUPPORTED** |
| **Validation Session** | `IOVNBD_S3a` | **SOURCE-SUPPORTED** |
| **Testing Session** | `IOVNBD_S3c` (Held-out & Frozen) | **SOURCE-SUPPORTED** |
| **Native Sampling Rate** | $10\text{ Hz}$ ($dt = 100\text{ ms}$) | **SOURCE-SUPPORTED** |
| **Model Input Rate** | $50\text{ Hz}$ ($dt = 20\text{ ms}$, linear interpolation) | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Sequence Length ($T$)** | $200$ timesteps ($4.0\text{ s}$ duration) | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Window Stride** | $\text{stride} = 1$ ($20\text{ ms}$ step, $99.5\%$ overlap) | **IMPLEMENTATION ASSUMPTION** |
| **Synchronization Tolerance** | $50\text{ ms}$ (`merge_asof`, `tolerance=0.05s`) | **SOURCE-SUPPORTED** (VBOX 10 Hz period) |
| **Input Features (D)** | 21 features (7 raw IMU + 14 rolling stats) | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Feature Formulas** | 7 raw: $a_x, a_y, a_z, g_x, g_y, g_z, \|a\|$<br>14 rolling: $\text{mean}_{200}, \text{var}_{200}$ (backward-looking) | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Feature Scaling** | `PaperMinMaxScaler` $[0.0, 1.0]$ | **IMPLEMENTATION ASSUMPTION** |
| **Scaler Fitting Scope** | **Strictly Training Set ($M + S1 + S2$) Only** | **SOURCE-SUPPORTED** (Anti-leakage rule) |
| **Target Variable** | `reference_speed` | **SOURCE-SUPPORTED** (*README_1.pdf* VBOX Velocity) |
| **Target Unit** | $\text{m/s}$ (converted from CAN $\text{km/h}$ via $/ 3.6$) | **SOURCE-SUPPORTED** |

---

## 2. MODEL & HYPERPARAMETER CONFIGURATION

| Parameter | Configuration Value | Classification |
| :--- | :--- | :--- |
| **Model 1 (Primary)** | `LSTMSelfAttention` (267,265 params) | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Model 2 (Ablation)** | `LSTMNoAttention` (217,729 params) | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Model 3 (Baseline)** | `SimpleBaselineMLP` (11,137 params) | **IMPLEMENTATION ASSUMPTION** |
| **LSTM Layers** | 2 layers | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Hidden Dimension** | $128$ hidden units | **IMPLEMENTATION ASSUMPTION** |
| **Attention Mechanism** | Scaled Dot-Product Self-Attention ($Q, K, V \in \mathbb{R}^{128}$) | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Attention Softmax Dim**| Temporal sequence dimension ($T=200$) | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Dropout** | $0.2$ | **IMPLEMENTATION ASSUMPTION** |
| **FC Regressor Head** | `Linear(128, 64) -> ReLU() -> Dropout(0.2) -> Linear(64, 1)` | **IMPLEMENTATION ASSUMPTION** |
| **Optimizer** | Adam | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Initial Learning Rate**| $0.0008$ | **IMPLEMENTATION ASSUMPTION** |
| **Learning Rate Scheduler**| `ReduceLROnPlateau(factor=0.5, patience=3)` | **IMPLEMENTATION ASSUMPTION** |
| **Batch Size** | $32$ | **IMPLEMENTATION ASSUMPTION** |
| **Max Epochs** | $35$ epochs | **IMPLEMENTATION ASSUMPTION** |
| **Loss Function** | Mean Squared Error (MSE) Loss | **SOURCE-SUPPORTED** (*Shin et al., 2025*) |
| **Loss Target Unit** | $(\text{m/s})^2$ | **SOURCE-SUPPORTED** |
| **Checkpoint Protocol** | Save best model based on `IOVNBD_S3a` Validation loss | **SOURCE-SUPPORTED** (Validation rule) |
| **Test Protocol** | Evaluate on `IOVNBD_S3c` ONCE after model selection | **SOURCE-SUPPORTED** (Test freeze rule) |
| **Random Seed** | `42` (Python, NumPy, PyTorch CPU/CUDA) | **IMPLEMENTATION ASSUMPTION** |
| **Test Set Freeze Flag**| `TEST_SET_FROZEN = True` | **SOURCE-SUPPORTED** (Anti-leakage rule) |
