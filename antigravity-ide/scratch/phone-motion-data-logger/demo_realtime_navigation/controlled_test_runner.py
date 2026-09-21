"""
demo_realtime_navigation/controlled_test_runner.py
Step-by-step controlled evaluation of verified fixes:
1. Baseline
2. Feature Scaling Fix
3. Verified Delta_v Reconstruction
4. Pre-outage Gyro Bias Calibration Fix
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import torch

from demo_realtime_navigation.backend.replay_engine import ReplayEngine
from demo_realtime_navigation.backend.navigation_core import NavigationCore
from paper_baseline.feature_extraction import extract_paper_features, FEATURE_COLUMNS, PaperMinMaxScaler

def run_benchmarks():
    durations = [10, 30, 60, 120]
    start_idx = 100
    
    # Load test session df
    df = pd.read_csv("data/iovnbd_selected/IOVNBD_S3c_standardized.csv")
    
    # Load model
    ckpt_path = "outputs/Exp_5_LSTMNoAttention_DeltaV/best_model.pt"
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    
    from paper_baseline.models import LSTMNoAttention
    model = LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    # Raw features
    df_feat = extract_paper_features(df, window_size=200)
    feat_cols = [c for c in FEATURE_COLUMNS if c in df_feat.columns]
    X_raw = df_feat[feat_cols].values.astype(np.float32)
    
    # Scaled features using saved params
    import json
    with open("demo_realtime_navigation/backend/scaler_params.json", "r") as f:
        s_data = json.load(f)
    scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
    scaler.min_val = np.array(s_data["min_val"], dtype=np.float32)
    scaler.max_val = np.array(s_data["max_val"], dtype=np.float32)
    scaler.is_fitted = True
    X_scaled = scaler.transform(X_raw)
    
    mu = float(ckpt["mu_delta_v"])
    std = float(ckpt["std_delta_v"])
    
    lat0 = float(df["latitude"].iloc[0])
    lon0 = float(df["longitude"].iloc[0])
    r_earth = 6378137.0
    
    ref_e = np.radians(df["longitude"].values - lon0) * r_earth * np.cos(np.radians(lat0))
    ref_n = np.radians(df["latitude"].values - lat0) * r_earth
    ref_speeds = df["reference_speed"].values
    ref_headings = df["reference_heading"].values
    gyro_z = df["gyro_z"].values
    
    # Check if pre-outage gyro bias exists
    # Pre-outage interval 0 to 100
    pre_outage_gz = gyro_z[:start_idx]
    gyro_bias_straight = float(np.mean(pre_outage_gz))
    
    def simulate_pipeline(use_scaler=False, gyro_bias=0.0):
        results = {}
        for dur in durations:
            dt = 0.1
            n_steps = int(dur / dt)
            end_idx = start_idx + n_steps
            
            # Initial state immediately before outage (at start_idx)
            pos_e = ref_e[start_idx]
            pos_n = ref_n[start_idx]
            heading_rad = np.radians(ref_headings[start_idx])
            v_anchor = ref_speeds[start_idx]
            
            e_hist = [pos_e]
            n_hist = [pos_n]
            v_hist = []
            h_hist = [heading_rad]
            
            for k in range(start_idx, end_idx):
                # 1. Feature window
                st = max(0, k - 199)
                X_mat = X_scaled if use_scaler else X_raw
                w = X_mat[st:k+1]
                if len(w) < 200:
                    pad = np.repeat(w[:1], 200 - len(w), axis=0)
                    w = np.vstack([pad, w])
                t_win = torch.tensor(w, dtype=torch.float32).unsqueeze(0)
                with torch.no_grad():
                    p_norm = model(t_win).item()
                dv = p_norm * std + mu
                
                # Speed reconstruction
                v_est = max(0.0, v_anchor + dv)
                v_hist.append(v_est)
                
                # Heading integration with bias correction
                gz_corrected = gyro_z[k] - gyro_bias
                heading_rad += gz_corrected * dt
                heading_rad = (heading_rad + np.pi) % (2.0 * np.pi) - np.pi
                h_hist.append(heading_rad)
                
                # Position step
                pos_n += v_est * np.cos(heading_rad) * dt
                pos_e += v_est * np.sin(heading_rad) * dt
                e_hist.append(pos_e)
                n_hist.append(pos_n)
                
            e_hist = np.array(e_hist)
            n_hist = np.array(n_hist)
            v_hist = np.array(v_hist)
            h_hist = np.array(h_hist)
            
            true_e = ref_e[start_idx:end_idx+1]
            true_n = ref_n[start_idx:end_idx+1]
            true_v = ref_speeds[start_idx:end_idx]
            true_h = np.radians(ref_headings[start_idx:end_idx+1])
            
            pos_errs = np.sqrt((e_hist - true_e)**2 + (n_hist - true_n)**2)
            ref_dist = float(np.sum(true_v * dt))
            est_dist = float(np.sum(v_hist * dt))
            
            final_pos_err = float(pos_errs[-1])
            max_pos_err = float(np.max(pos_errs))
            
            v_mae = float(np.mean(np.abs(v_hist - true_v)))
            v_rmse = float(np.sqrt(np.mean((v_hist - true_v)**2)))
            
            h_errs_deg = np.degrees((h_hist - true_h + np.pi) % (2.0 * np.pi) - np.pi)
            h_mae = float(np.mean(np.abs(h_errs_deg)))
            h_rmse = float(np.sqrt(np.mean(h_errs_deg**2)))
            final_h_err = float(np.abs(h_errs_deg[-1]))
            
            results[dur] = {
                "ref_dist": ref_dist,
                "est_dist": est_dist,
                "final_pos_err": final_pos_err,
                "max_pos_err": max_pos_err,
                "v_mae": v_mae,
                "v_rmse": v_rmse,
                "h_mae": h_mae,
                "h_rmse": h_rmse,
                "final_h_err": final_h_err
            }
        return results

    experiments = [
        ("A. Baseline (Unscaled, No Gyro Calibration)", False, 0.0),
        ("B. Fix 1: Feature Scaling Applied", True, 0.0),
        ("C. Fix 1 + Fix 3: Scaling + Pre-Outage Gyro Calibration", True, gyro_bias_straight),
    ]
    
    for title, use_sc, g_bias in experiments:
        print(f"\n==========================================================================")
        print(f"{title}")
        if g_bias != 0.0:
            print(f"Pre-outage straight-line Gyro Bias Subtracted: {g_bias:.6f} rad/s ({np.degrees(g_bias):.4f} deg/s)")
        print(f"==========================================================================")
        res = simulate_pipeline(use_scaler=use_sc, gyro_bias=g_bias)
        for dur, r in res.items():
            print(f"  {dur:3d}s | RefDist: {r['ref_dist']:6.2f}m | EstDist: {r['est_dist']:6.2f}m | FinalPosErr: {r['final_pos_err']:7.2f}m | MaxPosErr: {r['max_pos_err']:7.2f}m | VelMAE: {r['v_mae']:5.2f}m/s | VelRMSE: {r['v_rmse']:5.2f}m/s | HdgMAE: {r['h_mae']:5.2f} deg | HdgRMSE: {r['h_rmse']:5.2f} deg | FinalHdgErr: {r['final_h_err']:5.2f} deg")

if __name__ == "__main__":
    run_benchmarks()
