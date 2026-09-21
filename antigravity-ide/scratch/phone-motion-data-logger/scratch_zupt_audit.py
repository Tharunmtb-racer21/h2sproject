import os
import sys
import numpy as np
import pandas as pd
import torch
import json

from demo_realtime_navigation.backend.drift_corrector import (
    NonHolonomicConstraint,
    SafeStandstillDetector,
    VelocityEKF,
    ExperimentalMapMatcher
)
from paper_baseline.models import LSTMNoAttention
from paper_baseline.feature_extraction import extract_paper_features, FEATURE_COLUMNS, PaperMinMaxScaler

def audit_ai_zupt():
    df = pd.read_csv("data/iovnbd_selected/IOVNBD_S3c_standardized.csv")
    ref_v = df["reference_speed"].values
    ax = df["accel_x"].values
    ay = df["accel_y"].values
    az = df["accel_z"].values
    gx = df["gyro_x"].values
    gy = df["gyro_y"].values
    gz = df["gyro_z"].values
    
    ckpt = torch.load("outputs/Exp_5_LSTMNoAttention_DeltaV/best_model.pt", map_location="cpu", weights_only=False)
    model = LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    df_feat = extract_paper_features(df, window_size=200)
    feat_cols = [c for c in FEATURE_COLUMNS if c in df_feat.columns]
    X_raw = df_feat[feat_cols].values.astype(np.float32)

    with open("demo_realtime_navigation/backend/scaler_params.json") as f:
        s_data = json.load(f)
    scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
    scaler.min_val = np.array(s_data["min_val"], dtype=np.float32)
    scaler.max_val = np.array(s_data["max_val"], dtype=np.float32)
    scaler.is_fitted = True
    X_scaled = scaler.transform(X_raw)

    mu = float(ckpt["mu_delta_v"])
    std = float(ckpt["std_delta_v"])

    start_idx = 100
    v_anchor = ref_v[start_idx]

    # Precompute AI speeds
    ai_speeds = []
    for k in range(start_idx, start_idx + 1200):
        st = max(0, k - 199)
        w = X_scaled[st:k+1]
        if len(w) < 200:
            pad = np.repeat(w[:1], 200 - len(w), axis=0)
            w = np.vstack([pad, w])
        t_win = torch.tensor(w, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            p_norm = model(t_win).item()
        dv = p_norm * std + mu
        ai_speeds.append(max(0.0, v_anchor + dv))

    ai_speeds = np.array(ai_speeds)
    
    gt_standstill_win = (ref_v[start_idx:start_idx+1200] < 0.1)

    print("\n--- AI SPEED PREDICTIONS DURING OUTAGE (100:1300) ---")
    print(f"Ground Truth Standstill count in window: {np.sum(gt_standstill_win)}")
    print(f"AI speed min in window: {ai_speeds.min():.3f} m/s, max: {ai_speeds.max():.3f} m/s, mean: {ai_speeds.mean():.3f} m/s")
    
    # Standstill indices
    st_idxs = np.where(gt_standstill_win)[0]
    if len(st_idxs) > 0:
        print(f"When vehicle is ACTUALLY stationary (GT speed < 0.1 m/s), AI neural model predicts:")
        print(f"  AI speed min: {ai_speeds[st_idxs].min():.3f} m/s")
        print(f"  AI speed max: {ai_speeds[st_idxs].max():.3f} m/s")
        print(f"  AI speed mean: {ai_speeds[st_idxs].mean():.3f} m/s")
        print(f"  Number of samples where AI predicted speed < 0.5 m/s: {np.sum(ai_speeds[st_idxs] < 0.5)} out of {len(st_idxs)}")
        print(f"  Sample AI speeds during actual standstill: {ai_speeds[st_idxs][:10]}")

    # Test ZUPT using purely AI estimated speed (ZERO GT LEAKAGE)
    zupt = SafeStandstillDetector(window_size=10, accel_var_thresh=0.04, gyro_mag_thresh=0.04, speed_thresh=0.5, persist_steps=5)
    
    zupt_triggers = 0
    zupt_rejections = 0
    rejection_reasons = {}

    for k in range(1200):
        idx = start_idx + k
        v_est = ai_speeds[k]
        is_st = zupt.update(
            accel_x=ax[idx],
            accel_y=ay[idx],
            accel_z=az[idx],
            gyro_x=gx[idx],
            gyro_y=gy[idx],
            gyro_z=gz[idx],
            v_est=v_est
        )
        if is_st:
            zupt_triggers += 1
        else:
            zupt_rejections += 1
            r = zupt.last_rejection_reason
            rejection_reasons[r] = rejection_reasons.get(r, 0) + 1

    print(f"\nZUPT triggers during outage: {zupt_triggers}")
    print(f"ZUPT rejections: {zupt_rejections}")
    print(f"Rejection reasons: {rejection_reasons}")

if __name__ == "__main__":
    audit_ai_zupt()
