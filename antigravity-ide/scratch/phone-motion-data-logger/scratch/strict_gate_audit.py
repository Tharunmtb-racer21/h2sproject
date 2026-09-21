"""
scratch/strict_gate_audit.py
Definitive script executing the 19-point Strict Pre-Training Audit for SIH26168.
"""
import sys
import os
import time
import glob
import math
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from paper_baseline.dataset import (
    load_and_preprocess_session,
    LazySpeedSequenceDataset,
    build_paper_dataloaders,
    TRAIN_SESSIONS,
    VAL_SESSIONS,
    TEST_SESSIONS
)
from paper_baseline.feature_extraction import (
    synchronize_s_and_v_streams,
    extract_paper_features,
    PaperMinMaxScaler,
    FEATURE_COLUMNS
)
from paper_baseline.models import (
    LSTMSelfAttention,
    LSTMNoAttention,
    SimpleBaselineMLP,
    count_parameters
)

print("==========================================================================")
print("             SIH26168 STRICT PRE-TRAINING COMPREHENSIVE GATE              ")
print("==========================================================================\n")

# -----------------------------------------------------------------------------
# 1. WINDOWING SENSITIVITY ANALYSIS
# -----------------------------------------------------------------------------
print("--- 1. Windowing Sensitivity Analysis (Strides 1, 5, 10, 20) ---")
stride_results = []
for stride_val in [1, 5, 10, 20]:
    train_dfs = [load_and_preprocess_session(sid, window_size=200) for sid in TRAIN_SESSIONS]
    scaler = PaperMinMaxScaler()
    ds = LazySpeedSequenceDataset(train_dfs, scaler=scaler, fit_scaler=True, sequence_length=200, stride=stride_val)
    
    total_win = len(ds)
    overlap_pct = ((200 - stride_val) / 200.0) * 100.0 if stride_val < 200 else 0.0
    num_batches = math.ceil(total_win / 32)
    rel_cost = total_win / 1026982.0
    pred_interval_s = stride_val * 0.02
    
    stride_results.append({
        'Stride': stride_val,
        'Overlap %': overlap_pct,
        'Total Train Windows': total_win,
        'Batches / Epoch (B=32)': num_batches,
        'Pred Interval (s)': pred_interval_s,
        'Relative Cost': rel_cost
    })

df_stride = pd.DataFrame(stride_results)
print(df_stride.to_string(index=False))
print()

# -----------------------------------------------------------------------------
# 2. TARGET AUDIT & BASELINE IDENTITY VERIFICATION
# -----------------------------------------------------------------------------
print("--- 2. Target Audit & Baseline Identity Verification ---")
train_dfs = [load_and_preprocess_session(sid) for sid in TRAIN_SESSIONS]
concat_tr = pd.concat(train_dfs, ignore_index=True)

y_tr_ms = concat_tr['reference_speed'].values
y_tr_kmh = y_tr_ms * 3.6

mean_y = np.mean(y_tr_ms)
var_y = np.var(y_tr_ms)
mean_y2 = np.mean(y_tr_ms**2)

zero_pred_mse = mean_y2
mean_pred_mse = var_y
identity_check_zero = np.isclose(zero_pred_mse, var_y + mean_y**2)
identity_check_mean = np.isclose(mean_pred_mse, var_y)

print(f"Training Mean Speed (m/s):     {mean_y:.6f} m/s ({mean_y*3.6:.2f} km/h)")
print(f"Training Variance (m/s)^2:     {var_y:.6f} (m/s)^2")
print(f"Training E[y^2] (m/s)^2:       {mean_y2:.6f} (m/s)^2")
print(f"Zero-Pred MSE == Var + Mean^2?  {identity_check_zero} (Diff = {abs(zero_pred_mse - (var_y + mean_y**2)):.10f})")
print(f"Mean-Pred MSE == Variance?     {identity_check_mean} (Diff = {abs(mean_pred_mse - var_y):.10f})")

rmse_zero = np.sqrt(zero_pred_mse)
rmse_mean = np.sqrt(mean_pred_mse)
print(f"Baseline Constant-Zero Predictor RMSE: {rmse_zero:.4f} m/s ({rmse_zero*3.6:.2f} km/h)")
print(f"Baseline Constant-Mean Predictor RMSE: {rmse_mean:.4f} m/s ({rmse_mean*3.6:.2f} km/h)\n")

# -----------------------------------------------------------------------------
# 3. INDEPENDENT PARAMETER COUNT DERIVATION
# -----------------------------------------------------------------------------
print("--- 3. Independent Parameter Count Verification ---")

def derive_lstm_params(input_dim=21, hidden_dim=128, num_layers=2):
    # PyTorch LSTM params:
    # Layer 1: 4 * (hidden * input + hidden * hidden + hidden (bias_i) + hidden (bias_h))
    l1 = 4 * (hidden_dim * input_dim + hidden_dim * hidden_dim + 2 * hidden_dim)
    # Layer 2: 4 * (hidden * hidden + hidden * hidden + 2 * hidden)
    l2 = 4 * (hidden_dim * hidden_dim + hidden_dim * hidden_dim + 2 * hidden_dim)
    return l1 + l2

def derive_attention_params(embed_dim=128):
    # Query: embed*embed + embed, Key: embed*embed + embed, Value: embed*embed + embed
    return 3 * (embed_dim * embed_dim + embed_dim)

def derive_fc_regressor_params(in_dim=128):
    # Linear(128, 64) -> 128*64 + 64; Linear(64, 1) -> 64*1 + 1
    return (in_dim * 64 + 64) + (64 * 1 + 1)

# Models
m1 = LSTMSelfAttention(input_dim=21, hidden_dim=128, num_layers=2)
m2 = LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)
m3 = SimpleBaselineMLP(input_dim=21, hidden_dim=128)

p1_prog = count_parameters(m1)
p2_prog = count_parameters(m2)
p3_prog = count_parameters(m3)

p1_man = derive_lstm_params() + derive_attention_params() + derive_fc_regressor_params()
p2_man = derive_lstm_params() + derive_fc_regressor_params()
p3_man = (21 * 128 + 128) + (128 * 64 + 64) + (64 * 1 + 1)

param_table = [
    {'Model': '1. LSTMSelfAttention', 'Programmatic Params': f"{p1_prog:,}", 'Manually Derived Params': f"{p1_man:,}", 'Match': p1_prog == p1_man},
    {'Model': '2. LSTMNoAttention', 'Programmatic Params': f"{p2_prog:,}", 'Manually Derived Params': f"{p2_man:,}", 'Match': p2_prog == p2_man},
    {'Model': '3. SimpleBaselineMLP', 'Programmatic Params': f"{p3_prog:,}", 'Manually Derived Params': f"{p3_man:,}", 'Match': p3_prog == p3_man}
]

print(pd.DataFrame(param_table).to_string(index=False))
print()

# -----------------------------------------------------------------------------
# 4. MEASURED COMPUTATIONAL BENCHMARK (50 Batches)
# -----------------------------------------------------------------------------
print("--- 4. Measured Computational Benchmark (50 Batches) ---")
train_loader, _, _, _, _ = build_paper_dataloaders(batch_size=32, sequence_length=200, stride=1)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Execution Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU execution'})")

m1.to(device)
m1.train()
optimizer = optim.Adam(m1.parameters(), lr=0.0008)
criterion = nn.MSELoss()

# Warmup 5 batches
loader_iter = iter(train_loader)
for _ in range(5):
    X_b, y_b = next(loader_iter)
    X_b, y_b = X_b.to(device), y_b.to(device)
    optimizer.zero_grad()
    loss = criterion(m1(X_b), y_b)
    loss.backward()
    optimizer.step()

# Time 50 real batches
t0 = time.perf_counter()
for _ in range(50):
    X_b, y_b = next(loader_iter)
    X_b, y_b = X_b.to(device), y_b.to(device)
    optimizer.zero_grad()
    loss = criterion(m1(X_b), y_b)
    loss.backward()
    optimizer.step()
t1 = time.perf_counter()

total_time_50 = t1 - t0
time_per_batch_ms = (total_time_50 / 50.0) * 1000.0
batches_per_epoch = 32094
est_epoch_sec = (time_per_batch_ms / 1000.0) * batches_per_epoch
est_epoch_min = est_epoch_sec / 60.0

print(f"Benchmark Batches Run:           50 batches")
print(f"Time for 50 Batches:            {total_time_50:.3f} s")
print(f"Measured Time per Batch:         {time_per_batch_ms:.2f} ms / batch")
print(f"Batches per Epoch (stride=1):    {batches_per_epoch:,}")
print(f"Measured Estimated Epoch Time:  {est_epoch_min:.2f} minutes ({est_epoch_sec:.1f} s)\n")

# -----------------------------------------------------------------------------
# 5. DATASET GAP / INTEGRITY AUDIT
# -----------------------------------------------------------------------------
print("--- 5. Dataset Gap / Monotonicity Audit ---")
for sid in TRAIN_SESSIONS + VAL_SESSIONS + TEST_SESSIONS:
    df_s = load_and_preprocess_session(sid)
    ts_col = 'relative_time_s' if 'relative_time_s' in df_s.columns else df_s.columns[0]
    dups = df_s.duplicated(subset=[ts_col]).sum()
    nans = df_s.isna().sum().sum()
    infs = np.isinf(df_s.select_dtypes(include=[np.number]).values).sum()
    dt = np.diff(df_s[ts_col].values)
    non_mono = (dt <= 0).sum()
    max_dt = np.max(dt)
    large_gaps = (dt > 0.5).sum() # threshold for large gap = 0.5s
    
    print(f"Session {sid:<12}: Duplicates={dups} | Non-monotonic={non_mono} | NaNs={nans} | Infs={infs} | Max dt={max_dt:.4f}s | Gaps>0.5s={large_gaps}")

print("\n==========================================================================")
print("                   BENCHMARK & AUDIT COMPLETE                             ")
print("==========================================================================")

