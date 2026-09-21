# SIH26168 — Model V2 Training & Artifacts Report

## 1. Model Architecture & Hyperparameters

- **Model Identifier**: `Exp_6_LSTM_AbsoluteSpeedRatio`
- **Class Name**: `LSTMAbsoluteSpeedRatio`
- **Parameter Count**: **217,729 trainable parameters**
- **Input Dimension**: `(Batch, T=200, 21)` (200 samples @ 50 Hz = 4.0 second sliding window)
- **Target Dimension**: `(Batch, 1)` representing bounded speed ratio $r_t = \frac{v_t}{\max(v_{anchor}, 1.0\text{ m/s})} \in [0.0, 3.0]$
- **Loss Function**: Mean Squared Error (`nn.MSELoss`)
- **Optimizer**: Adam (`lr=0.001`)
- **Batch Size**: 128
- **Epochs Trained**: 10
- **Output Activation Head**: $r_{pred} = 3.0 \cdot \text{Sigmoid}(W_{out} \cdot h_{64} + b_{out})$

---

## 2. Dataset Split & Sample Statistics

| Split | Sessions | Windows ($T=200, \text{Stride}=5$) | Role |
| :--- | :--- | :--- | :--- |
| **Train** | `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2` | **50,143** | Fit Scaler & Train Model Weights |
| **Validation** | `IOVNBD_S3a` | **4,885** | Early Stopping & Hyperparameter Selection |
| **Test** | `IOVNBD_S3c` | **7,397** | Unseen Held-out Evaluation |

---

## 3. Training Convergence Trajectory

| Epoch | Train MSE Loss | Validation MSE Loss |
| :---: | :---: | :---: |
| **01** | 0.703977 | 0.528077 |
| **02** | 0.521104 | 0.528077 |
| **03** | 0.521104 | 0.528077 |
| **04** | 0.521104 | 0.528077 |
| **05** | 0.521104 | 0.528077 |
| **06** | 0.521104 | 0.528077 |
| **07** | 0.521104 | 0.528077 |
| **08** | 0.521104 | 0.528077 |
| **09** | 0.521104 | 0.528077 |
| **10** | 0.521104 | 0.528077 |

**Best Validation Loss**: **0.528077** (Saved to `outputs/Exp_6_LSTM_AbsoluteSpeedRatio/best_model.pt`).

---

## 4. Scaler Configuration & Artifact Locations

- **Checkpoint Path**: `outputs/Exp_6_LSTM_AbsoluteSpeedRatio/best_model.pt`
- **Scaler JSON Path**: `outputs/Exp_6_LSTM_AbsoluteSpeedRatio/scaler_params.json`
- **Scaler Range**: MinMax normalized $[0.0, 1.0]$ across 21 input features fitted strictly on the training set.
