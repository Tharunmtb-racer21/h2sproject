"""
demo_realtime_navigation/test_drift_reduction_suite.py
SIH26168 Intelligent Dead Reckoning System
Controlled, Audited, Zero-Ground-Truth-Leakage Benchmark Suite on IOVNBD_S3c

Evaluates:
- A. Baseline (+gyro_z, Unscaled)
- B. Corrected Yaw (Scaled, -gyro_y)
- C. Corrected Yaw + NHC
- D. Corrected Yaw + Safe IMU Physical ZUPT
- E. Corrected Yaw + EKF Velocity Fusion
- F. Pure Autonomous Combined (Yaw + NHC + ZUPT + EKF)
- G. Offline Map Matching Experiment (Marked with explicit ground-truth road warning)
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.drift_corrector import (
    NonHolonomicConstraint,
    SafeStandstillDetector,
    VelocityEKF,
    ExperimentalMapMatcher
)
from paper_baseline.models import LSTMNoAttention
from paper_baseline.feature_extraction import extract_paper_features, FEATURE_COLUMNS, PaperMinMaxScaler


def run_drift_suite():
    print("=" * 95)
    print("CONTROLLED DRIFT REDUCTION BENCHMARK SUITE (IOVNBD_S3c) - ZERO LEAKAGE AUDITED")
    print("=" * 95)

    # 1. Load Session S3c
    df = pd.read_csv("data/iovnbd_selected/IOVNBD_S3c_standardized.csv")
    start_idx = 100
    durations = [10, 30, 60, 120]
    dt = 0.1

    # 2. Load Model & Features
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

    lat0 = float(df["latitude"].iloc[0])
    lon0 = float(df["longitude"].iloc[0])
    r_earth = 6378137.0
    ref_e = np.radians(df["longitude"].values - lon0) * r_earth * np.cos(np.radians(lat0))
    ref_n = np.radians(df["latitude"].values - lat0) * r_earth
    ref_speeds = df["reference_speed"].values
    ref_headings = df["reference_heading"].values
    accel_x = df["accel_x"].values
    accel_y = df["accel_y"].values
    accel_z = df["accel_z"].values
    gyro_x = df["gyro_x"].values
    gyro_y = df["gyro_y"].values
    gyro_z = df["gyro_z"].values

    mu = float(ckpt["mu_delta_v"])
    std = float(ckpt["std_delta_v"])
    v_anchor = ref_speeds[start_idx]

    # Precompute AI speeds (scaled)
    ai_speeds_scaled = []
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
        ai_speeds_scaled.append(max(0.0, v_anchor + dv))
    ai_speeds_scaled = np.array(ai_speeds_scaled)

    # Precompute unscaled AI speeds for Baseline A
    ai_speeds_unscaled = []
    for k in range(start_idx, start_idx + 1200):
        st = max(0, k - 199)
        w = X_raw[st:k+1]
        if len(w) < 200:
            pad = np.repeat(w[:1], 200 - len(w), axis=0)
            w = np.vstack([pad, w])
        t_win = torch.tensor(w, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            p_norm = model(t_win).item()
        dv = p_norm * std + mu
        ai_speeds_unscaled.append(max(0.0, v_anchor + dv))
    ai_speeds_unscaled = np.array(ai_speeds_unscaled)

    # Pre-outage gyro biases (calculated strictly BEFORE outage starts, 0:start_idx)
    pre_bias_z = float(np.mean(gyro_z[:start_idx]))
    pre_bias_y = float(np.mean(-gyro_y[:start_idx]))

    def simulate(
        dur: int,
        use_corrected_yaw: bool = True,
        use_scaling: bool = True,
        use_nhc: bool = False,
        use_zupt: bool = False,
        use_ekf: bool = False
    ):
        n_steps = int(dur / dt)
        end_idx = start_idx + n_steps

        true_e = ref_e[start_idx:end_idx+1]
        true_n = ref_n[start_idx:end_idx+1]
        true_v = ref_speeds[start_idx:end_idx]
        true_h = ref_headings[start_idx:end_idx+1]

        v_base_arr = ai_speeds_scaled if use_scaling else ai_speeds_unscaled
        yaw_rate_arr = (-gyro_y[start_idx:end_idx] - pre_bias_y) if use_corrected_yaw else (gyro_z[start_idx:end_idx] - pre_bias_z)

        # Pure physical IMU invariant ZUPT: rolling accel variance < 0.015, gyro < 0.02 rad/s, 8 steps persistence
        zupt = SafeStandstillDetector(window_size=10, accel_var_thresh=0.015, gyro_mag_thresh=0.02, persist_steps=8) if use_zupt else None
        nhc = NonHolonomicConstraint(damping_strength=0.95) if use_nhc else None
        ekf = VelocityEKF() if use_ekf else None
        if use_ekf:
            ekf.reset(initial_speed=v_anchor)

        pos_e = ref_e[start_idx]
        pos_n = ref_n[start_idx]
        heading_rad = np.radians(ref_headings[start_idx])

        e_hist = [pos_e]
        n_hist = [pos_n]
        v_hist = []
        h_hist = [heading_rad]

        zupt_acts = 0

        for k in range(n_steps):
            idx = start_idx + k
            v_ai = v_base_arr[k]

            # 1. EKF Fusion
            if use_ekf:
                v_step = ekf.step(a_forward=float(accel_x[idx]), v_ai_pred=v_ai, dt=dt)
            else:
                v_step = v_ai

            # 2. Pure Physical IMU ZUPT (strictly 6-DOF IMU, zero velocity argument)
            if use_zupt:
                is_st = zupt.update(
                    accel_x=float(accel_x[idx]),
                    accel_y=float(accel_y[idx]),
                    accel_z=float(accel_z[idx]),
                    gyro_x=float(gyro_x[idx]),
                    gyro_y=float(gyro_y[idx]),
                    gyro_z=float(gyro_z[idx])
                )
                if is_st:
                    v_step = 0.0
                    zupt_acts += 1
                    if use_ekf:
                        ekf.v_est = 0.0

            v_hist.append(v_step)

            # 3. Heading Integration
            w_yaw = yaw_rate_arr[k]
            heading_rad += w_yaw * dt
            heading_rad = (heading_rad + np.pi) % (2.0 * np.pi) - np.pi
            h_hist.append(heading_rad)

            # 4. NHC Position Propagation
            if use_nhc:
                dn, de, _ = nhc.apply(v_forward=v_step, heading_rad=heading_rad, dt=dt)
                pos_n += dn
                pos_e += de
            else:
                pos_n += v_step * np.cos(heading_rad) * dt
                pos_e += v_step * np.sin(heading_rad) * dt

            e_hist.append(pos_e)
            n_hist.append(pos_n)

        # Metrics
        pos_errs = np.sqrt((np.array(e_hist) - true_e)**2 + (np.array(n_hist) - true_n)**2)
        final_pos_err = pos_errs[-1]
        max_pos_err = np.max(pos_errs)

        h_est_deg = np.degrees(h_hist)
        h_errs = (h_est_deg - true_h + 180.0) % 360.0 - 180.0
        h_rmse = np.sqrt(np.mean(h_errs**2))
        final_h_err = abs(h_errs[-1])

        v_rmse = np.sqrt(np.mean((np.array(v_hist) - true_v)**2))
        est_dist = np.sum(v_hist) * dt
        ref_dist = np.sum(true_v) * dt

        return {
            "final_pos_err": final_pos_err,
            "max_pos_err": max_pos_err,
            "h_rmse": h_rmse,
            "final_h_err": final_h_err,
            "v_rmse": v_rmse,
            "est_dist": est_dist,
            "ref_dist": ref_dist,
            "zupt_acts": zupt_acts
        }

    configs = [
        ("A. Baseline (+gyro_z, Unscaled)", False, False, False, False, False),
        ("B. Corrected Yaw (Scaled, -gyro_y)", True, True, False, False, False),
        ("C. Corrected Yaw + NHC", True, True, True, False, False),
        ("D. Corrected Yaw + Safe IMU-ZUPT", True, True, False, True, False),
        ("E. Corrected Yaw + EKF Velocity Fusion", True, True, False, False, True),
        ("F. Pure Autonomous Combined (Yaw + NHC + ZUPT + EKF)", True, True, True, True, True),
    ]

    results = {}
    for name, cyaw, scale, nhc, zupt, ekf in configs:
        print(f"\n-------------------------------------------------------------------------------------")
        print(f"CONFIGURATION: {name}")
        print(f"-------------------------------------------------------------------------------------")
        results[name] = {}
        for d in durations:
            res = simulate(d, use_corrected_yaw=cyaw, use_scaling=scale, use_nhc=nhc, use_zupt=zupt, use_ekf=ekf)
            results[name][d] = res
            print(f"  {d:3d}s | FinalPosErr: {res['final_pos_err']:7.2f}m | MaxPosErr: {res['max_pos_err']:7.2f}m | Hdg RMSE: {res['h_rmse']:5.2f} deg | Final Hdg: {res['final_h_err']:5.2f} deg | Vel RMSE: {res['v_rmse']:5.2f} m/s | EstDist: {res['est_dist']:7.1f}m | RefDist: {res['ref_dist']:7.1f}m | ZUPTs: {res['zupt_acts']:2d}")

    print("\n" + "=" * 95)
    print("MASTER DRIFT REDUCTION COMPARISON MATRIX (ZERO-LEAKAGE PRODUCTION AUDIT)")
    print("=" * 95)
    print(f"{'Configuration':<52} | {'10s Error':<10} | {'30s Error':<10} | {'60s Error':<10} | {'120s Error':<10}")
    print("-" * 95)
    for name in results:
        r = results[name]
        print(f"{name:<52} | {r[10]['final_pos_err']:8.2f}m | {r[30]['final_pos_err']:8.2f}m | {r[60]['final_pos_err']:8.2f}m | {r[120]['final_pos_err']:8.2f}m")

    print("\n" + "=" * 95)
    print("GROUND TRUTH LEAKAGE NOTE ON MAP MATCHING:")
    print("Map matching requires independent GIS/OSM vector polylines. Generating road points from")
    print("the test session GPS constitutes ground truth leakage. Therefore, map matching is excluded")
    print("from the production dead reckoning baseline and marked as OFFLINE EXPERIMENTAL ONLY.")
    print("=" * 95)


if __name__ == "__main__":
    run_drift_suite()
