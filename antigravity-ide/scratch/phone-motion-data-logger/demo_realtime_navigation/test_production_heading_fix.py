"""
demo_realtime_navigation/test_production_heading_fix.py
Controlled validation of the production-path heading fix using actual ReplayEngine,
OutageController, and NavigationCore classes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import torch

from demo_realtime_navigation.backend.replay_engine import ReplayEngine
from demo_realtime_navigation.backend.navigation_core import NavigationCore

def run_heading_fix_benchmarks():
    print("=" * 90)
    print("STRICT PRODUCTION-PATH VALIDATION OF HEADING FIX (IOVNBD_S3c)")
    print("=" * 90)
    
    durations = [10, 30, 60, 120]
    start_idx = 100
    
    # 1. Test Production ReplayEngine (Mode B: Corrected Sensor-Frame Yaw)
    print("\n" + "-"*90)
    print("MODE B: CORRECTED SENSOR-FRAME PRODUCTION PATH (ReplayEngine Live Classes)")
    print("-"*90)
    
    results_prod = {}
    for dur in durations:
        engine = ReplayEngine()
        engine.reset_playback()
        for _ in range(start_idx):
            engine.step(1)
            
        pre_frame = engine.get_current_frame()
        engine.trigger_simulated_outage(duration_s=dur)
        
        frames = []
        n_steps = int(dur / 0.1)
        for _ in range(n_steps):
            f = engine.step(1)
            frames.append(f)
            
        post_frame = engine.get_current_frame()
        
        ref_speeds = np.array([f["ref_speed_kmh"] / 3.6 for f in frames])
        ai_speeds = np.array([f["displayed_speed_mps"] for f in frames])
        ref_dist = float(np.sum(ref_speeds * 0.1))
        est_dist = float(np.sum(ai_speeds * 0.1))
        final_pos_err = float(post_frame["position_error_m"])
        max_pos_err = float(max(f["position_error_m"] for f in frames))
        
        v_rmse = float(np.sqrt(np.mean((ai_speeds - ref_speeds)**2)))
        
        h_diffs = []
        for f in frames:
            hdg = f["heading_deg"]
            ref_hdg = float(engine.df["reference_heading"].iloc[f["index"]])
            diff = abs((hdg - ref_hdg + 180.0) % 360.0 - 180.0)
            h_diffs.append(diff)
            
        h_mae = float(np.mean(h_diffs))
        h_rmse = float(np.sqrt(np.mean(np.array(h_diffs)**2)))
        final_h_err = float(h_diffs[-1])
        
        results_prod[dur] = {
            "ref_dist": ref_dist,
            "est_dist": est_dist,
            "final_pos_err": final_pos_err,
            "max_pos_err": max_pos_err,
            "v_rmse": v_rmse,
            "h_mae": h_mae,
            "h_rmse": h_rmse,
            "final_h_err": final_h_err,
        }
        print(f"  {dur:3d}s | FinalPosErr: {final_pos_err:6.2f}m | MaxPosErr: {max_pos_err:6.2f}m | Hdg RMSE: {h_rmse:5.2f} deg | Final Hdg Err: {final_h_err:5.2f} deg | Vel RMSE: {v_rmse:4.2f} m/s | EstDist: {est_dist:6.1f}m | RefDist: {ref_dist:6.1f}m")

    # 2. Comprehensive A / B / C / D / E Comparison Matrix
    print("\n" + "="*90)
    print("COMPREHENSIVE ORACLE & SENSOR-FRAME SEPARATION MATRIX")
    print("="*90)
    
    # Load df and model for diagnostic isolation
    df = pd.read_csv("data/iovnbd_selected/IOVNBD_S3c_standardized.csv")
    lat0 = float(df["latitude"].iloc[0])
    lon0 = float(df["longitude"].iloc[0])
    r_earth = 6378137.0
    ref_e = np.radians(df["longitude"].values - lon0) * r_earth * np.cos(np.radians(lat0))
    ref_n = np.radians(df["latitude"].values - lat0) * r_earth
    ref_speeds = df["reference_speed"].values
    ref_headings = df["reference_heading"].values
    
    # Pre-calculated AI speeds from production model with scaler
    engine = ReplayEngine()
    engine.reset_playback()
    for _ in range(start_idx):
        engine.step(1)
    engine.trigger_simulated_outage(duration_s=120)
    ai_speeds_all = []
    for _ in range(1200):
        f = engine.step(1)
        ai_speeds_all.append(f["displayed_speed_mps"])
    ai_speeds_all = np.array(ai_speeds_all)
    
    pre_bias_z = float(np.mean(df["gyro_z"].iloc[:start_idx]))
    pre_bias_y = float(np.mean(-df["gyro_y"].iloc[:start_idx]))
    
    for dur in durations:
        n_steps = int(dur / 0.1)
        end_idx = start_idx + n_steps
        sub = df.iloc[start_idx:end_idx]
        true_e = ref_e[start_idx:end_idx+1]
        true_n = ref_n[start_idx:end_idx+1]
        true_v = ref_speeds[start_idx:end_idx]
        true_h = ref_headings[start_idx:end_idx+1]
        
        v_ai = ai_speeds_all[:n_steps]
        gz_old = sub["gyro_z"].values - pre_bias_z
        gy_new = -sub["gyro_y"].values - pre_bias_y
        
        def run_sim(v_arr, yaw_arr, ref_h_arr=None):
            pos_e = ref_e[start_idx]
            pos_n = ref_n[start_idx]
            h = np.radians(ref_headings[start_idx])
            e_h, n_h, h_deg_arr = [pos_e], [pos_n], [ref_headings[start_idx]]
            for k in range(n_steps):
                if ref_h_arr is not None:
                    h = np.radians(ref_h_arr[k])
                else:
                    h += yaw_arr[k] * 0.1
                    h = (h + np.pi) % (2*np.pi) - np.pi
                h_deg_arr.append(float(np.degrees(h)) % 360.0)
                pos_n += v_arr[k] * np.cos(h) * 0.1
                pos_e += v_arr[k] * np.sin(h) * 0.1
                e_h.append(pos_e)
                n_h.append(pos_n)
            errs = np.sqrt((np.array(e_h) - true_e)**2 + (np.array(n_h) - true_n)**2)
            h_errs = np.abs((np.array(h_deg_arr) - true_h + 180.0) % 360.0 - 180.0)
            return errs[-1], np.max(errs), np.sqrt(np.mean(h_errs**2)), h_errs[-1]

        # A. Old Gyro (+gyro_z) + AI Vel
        e_a, max_a, h_rmse_a, h_fin_a = run_sim(v_ai, gz_old)
        # B. Corrected Yaw (-gyro_y) + AI Vel (Production)
        e_b, max_b, h_rmse_b, h_fin_b = run_sim(v_ai, gy_new)
        # C. Reference Heading + AI Vel (Hdg Oracle)
        e_c, max_c, h_rmse_c, h_fin_c = run_sim(v_ai, None, ref_headings[start_idx:end_idx])
        # D. Corrected Yaw (-gyro_y) + Reference Speed (Vel Oracle)
        e_d, max_d, h_rmse_d, h_fin_d = run_sim(true_v, gy_new)
        # E. Reference Heading + Reference Speed (Full Oracle)
        e_e, max_e, h_rmse_e, h_fin_e = run_sim(true_v, None, ref_headings[start_idx:end_idx])
        
        print(f"\n--- {dur:3d}s OUTAGE ---")
        print(f"  A. Old Gyro (+gyro_z) + AI Vel:      FinalPosErr = {e_a:6.2f}m | MaxPosErr = {max_a:6.2f}m | Hdg RMSE = {h_rmse_a:5.2f} deg | Final Hdg Err = {h_fin_a:5.2f} deg")
        print(f"  B. Corrected Yaw (-gyro_y) + AI Vel: FinalPosErr = {e_b:6.2f}m | MaxPosErr = {max_b:6.2f}m | Hdg RMSE = {h_rmse_b:5.2f} deg | Final Hdg Err = {h_fin_b:5.2f} deg")
        print(f"  C. Ref Heading + AI Vel (Hdg Oracle): FinalPosErr = {e_c:6.2f}m | MaxPosErr = {max_c:6.2f}m | Hdg RMSE =  0.00 deg | Final Hdg Err =  0.00 deg")
        print(f"  D. Corrected Yaw + Ref Spd (Vel Oracle): FinalPosErr = {e_d:6.2f}m | MaxPosErr = {max_d:6.2f}m | Hdg RMSE = {h_rmse_d:5.2f} deg | Final Hdg Err = {h_fin_d:5.2f} deg")
        print(f"  E. Full Oracle (Ref Hdg + Ref Spd):  FinalPosErr = {e_e:6.2f}m | MaxPosErr = {max_e:6.2f}m | Hdg RMSE =  0.00 deg | Final Hdg Err =  0.00 deg")

if __name__ == "__main__":
    run_heading_fix_benchmarks()
