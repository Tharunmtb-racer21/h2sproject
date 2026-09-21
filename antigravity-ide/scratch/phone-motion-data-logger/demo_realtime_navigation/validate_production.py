"""
demo_realtime_navigation/validate_production.py
Strict production-path validation script for SIH26168.
Runs A/B/C/D evaluations, ablation tests, and reports exact metrics.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import torch

from paper_baseline.models import LSTMNoAttention
from paper_baseline.feature_extraction import extract_paper_features, FEATURE_COLUMNS, PaperMinMaxScaler
from paper_baseline.dataset import TRAIN_SESSIONS, load_and_preprocess_session

def run_all_validations():
    # 1. Load Session S3c
    data_path = os.path.join("data", "iovnbd_selected", "IOVNBD_S3c_standardized.csv")
    df = pd.read_csv(data_path)
    
    # 2. Load Checkpoint
    ckpt_path = os.path.join("outputs", "Exp_5_LSTMNoAttention_DeltaV", "best_model.pt")
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model = LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    # 3. Features
    df_feat = extract_paper_features(df, window_size=200)
    feat_cols = [c for c in FEATURE_COLUMNS if c in df_feat.columns]
    X_raw = df_feat[feat_cols].values
    
    train_dfs = [load_and_preprocess_session(sid, window_size=200) for sid in TRAIN_SESSIONS]
    scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
    X_train_concat = np.concatenate([d[FEATURE_COLUMNS].values for d in train_dfs], axis=0)
    scaler.fit(X_train_concat)
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
    accel_x = df["accel_x"].values
    accel_y = df["accel_y"].values
    accel_z = df["accel_z"].values
    
    start_idx = 100
    durations = [10, 30, 60, 120]
    
    def simulate(mode="A", dur=10, use_scaler=False, use_alignment=False, use_zupt=False, use_damping=False):
        dt = 0.1
        n_steps = int(dur / dt)
        end_idx = start_idx + n_steps
        
        pos_e = ref_e[start_idx]
        pos_n = ref_n[start_idx]
        heading_rad = np.radians(ref_headings[start_idx])
        v_anchor = ref_speeds[start_idx]
        
        e_hist = [pos_e]
        n_hist = [pos_n]
        v_hist = []
        h_hist = [heading_rad]
        
        for k in range(start_idx, end_idx):
            # Speed determination
            if mode in ["A", "B"]:
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
                v_est = max(0.0, v_anchor + dv)
                
                # Ablations
                if use_damping and (accel_x[k] < -0.5):
                    v_est = max(0.0, v_est + accel_x[k] * dt)
                
                acc_norm_sq = accel_x[k]**2 + accel_y[k]**2 + (accel_z[k] - 9.81)**2
                if use_zupt and (acc_norm_sq < 0.02 and v_est < 0.3):
                    v_est = 0.0
                    
                v_step = v_est
            else:
                v_step = ref_speeds[k]
                
            v_hist.append(v_step)
            
            # Heading determination
            if mode in ["A", "C"]:
                gz = gyro_z[k]
                heading_rad += gz * dt
                heading_rad = (heading_rad + np.pi) % (2.0 * np.pi) - np.pi
            else:
                heading_rad = np.radians(ref_headings[k])
                
            h_hist.append(heading_rad)
            
            # Position step
            pos_n += v_step * np.cos(heading_rad) * dt
            pos_e += v_step * np.sin(heading_rad) * dt
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
        
        return {
            "dur": dur,
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

    modes = [
        ("A", "A: Real Production (AI vel [unscaled as deployed] + IMU gyro)"),
        ("B", "B: Diagnostic (AI vel + Ref heading)"),
        ("C", "C: Diagnostic (Ref speed + IMU gyro)"),
        ("D", "D: Oracle (Ref speed + Ref heading)"),
    ]
    
    print("\n" + "="*90)
    print("STRICT A/B/C/D RESULTS (AS CURRENTLY DEPLOYED IN PRODUCTION)")
    print("="*90)
    
    for m_code, m_title in modes:
        print(f"\n### {m_title}")
        for d in durations:
            r = simulate(mode=m_code, dur=d, use_scaler=False)
            print(f"  {d:3d}s | RefDist: {r['ref_dist']:6.2f}m | EstDist: {r['est_dist']:6.2f}m | FinalPosErr: {r['final_pos_err']:7.2f}m | MaxPosErr: {r['max_pos_err']:7.2f}m | VelMAE: {r['v_mae']:5.2f}m/s | VelRMSE: {r['v_rmse']:5.2f}m/s | HdgMAE: {r['h_mae']:5.2f} deg | HdgRMSE: {r['h_rmse']:5.2f} deg | FinalHdgErr: {r['final_h_err']:5.2f} deg")

    print("\n" + "="*90)
    print("ABLATION OF RECENT CHANGES (ON REAL PRODUCTION PIPELINE MODE A)")
    print("="*90)
    
    ablations = [
        ("Baseline (Deployed Unscaled)", False, False, False, False),
        ("Baseline + Scaler Correction", True, False, False, False),
        ("Baseline + Scaler + ZUPT", True, False, True, False),
        ("Baseline + Scaler + Damping", True, False, False, True),
        ("Baseline + Scaler + ZUPT + Damping", True, False, True, True),
    ]
    
    for abl_name, use_sc, use_al, use_zp, use_dp in ablations:
        print(f"\n### {abl_name}")
        for d in durations:
            r = simulate(mode="A", dur=d, use_scaler=use_sc, use_alignment=use_al, use_zupt=use_zp, use_damping=use_dp)
            print(f"  {d:3d}s | RefDist: {r['ref_dist']:6.2f}m | EstDist: {r['est_dist']:6.2f}m | FinalPosErr: {r['final_pos_err']:7.2f}m | MaxPosErr: {r['max_pos_err']:7.2f}m | VelMAE: {r['v_mae']:5.2f}m/s | VelRMSE: {r['v_rmse']:5.2f}m/s")

if __name__ == "__main__":
    run_all_validations()
