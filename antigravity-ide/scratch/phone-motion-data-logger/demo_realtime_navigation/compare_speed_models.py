"""
demo_realtime_navigation/compare_speed_models.py
SIH26168 Speed Model Benchmark & Evaluation Suite

Evaluates 4 Operating Speed Modes on IOVNBD_S3c and IOVNBD_S3a sessions:
1. PERSISTENCE_PRODUCTION (Anchor Speed + Gyro Kinematics + ZUPT - Production Default)
2. AI_RATIO_DIAGNOSTIC (Model V2: Bounded Absolute Speed Ratio r_pred * v_anchor)
3. DELTA_V_DIAGNOSTIC (Model V1: Legacy Delta-V Model)
4. REFERENCE_DIAGNOSTIC (Evaluation Ground-Truth Baseline - EVAL ONLY)

Calculates:
- Speed MAE (m/s) & Speed RMSE (m/s)
- Final Position Error (m), Max Position Error (m), Mean Position Error (m)
- Heading MAE (deg) & Heading RMSE (deg)
"""

import sys
import os
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.replay_engine import ReplayEngine


def run_outage_benchmark(session_name="IOVNBD_S3c", speed_mode="PERSISTENCE_PRODUCTION", outage_start_s=100.0, duration_s=120.0):
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "iovnbd_selected"))
    eng = ReplayEngine(data_dir=data_dir)
    eng.speed_mode = speed_mode
    eng.load_session(session_name)
    
    # Fast-forward to outage start
    start_idx = 0
    for i in range(eng.total_samples - 1):
        if float(eng.df["relative_time_s"].iloc[i]) >= outage_start_s:
            start_idx = i
            break
        eng.step(stride=1)
        
    eng.trigger_simulated_outage(duration_s=duration_s)
    num_steps = int(round(duration_s / 0.1))
    
    pos_errors = []
    speed_errors = []
    heading_errors = []
    
    for step_i in range(num_steps):
        idx = start_idx + step_i
        if idx >= eng.total_samples - 1:
            break
            
        row = eng.df.iloc[idx]
        ref_e = float(row["ref_east_m"])
        ref_n = float(row["ref_north_m"])
        ref_v = float(row["reference_speed"])
        ref_h = float(row["reference_heading"])
        
        frame = eng.step(stride=1)
        dr_e = frame["active_east_m"]
        dr_n = frame["active_north_m"]
        dr_v = frame["displayed_speed_mps"]
        dr_h = frame["heading_deg"]
        
        pos_err = float(np.sqrt((dr_e - ref_e)**2 + (dr_n - ref_n)**2))
        speed_err = float(abs(dr_v - ref_v))
        
        # Angular difference wrapped to [-180, 180]
        h_diff = float((dr_h - ref_h + 180.0) % 360.0 - 180.0)
        
        pos_errors.append(pos_err)
        speed_errors.append(speed_err)
        heading_errors.append(abs(h_diff))
        
    pos_errors = np.array(pos_errors)
    speed_errors = np.array(speed_errors)
    heading_errors = np.array(heading_errors)
    
    return {
        "session": session_name,
        "speed_mode": speed_mode,
        "outage_duration_s": duration_s,
        "steps_evaluated": len(pos_errors),
        "final_position_error_m": round(float(pos_errors[-1]), 2) if len(pos_errors) > 0 else 0.0,
        "max_position_error_m": round(float(np.max(pos_errors)), 2) if len(pos_errors) > 0 else 0.0,
        "mean_position_error_m": round(float(np.mean(pos_errors)), 2) if len(pos_errors) > 0 else 0.0,
        "speed_mae_ms": round(float(np.mean(speed_errors)), 4) if len(speed_errors) > 0 else 0.0,
        "speed_rmse_ms": round(float(np.sqrt(np.mean(speed_errors**2))), 4) if len(speed_errors) > 0 else 0.0,
        "heading_mae_deg": round(float(np.mean(heading_errors)), 2) if len(heading_errors) > 0 else 0.0,
        "heading_rmse_deg": round(float(np.sqrt(np.mean(heading_errors**2))), 2) if len(heading_errors) > 0 else 0.0,
    }


def run_full_suite():
    sessions = ["IOVNBD_S3c", "IOVNBD_S3a"]
    durations = [10.0, 30.0, 60.0, 120.0]
    modes = ["PERSISTENCE_PRODUCTION", "AI_RATIO_DIAGNOSTIC", "DELTA_V_DIAGNOSTIC", "REFERENCE_DIAGNOSTIC"]
    
    all_results = []
    print("======================================================================", flush=True)
    print("SIH26168 COMPREHENSIVE SPEED MODEL COMPARISON BENCHMARK", flush=True)
    print("======================================================================", flush=True)
    
    for session in sessions:
        print(f"\n--- SESSION: {session} ---", flush=True)
        for dur in durations:
            print(f"\nOutage Duration: {dur}s", flush=True)
            print(f"{'Mode':<25} | {'Final Err (m)':<13} | {'Max Err (m)':<12} | {'Speed MAE (m/s)':<15} | {'Hdg MAE (deg)':<13}", flush=True)
            print("-" * 88, flush=True)
            for mode in modes:
                res = run_outage_benchmark(session_name=session, speed_mode=mode, outage_start_s=100.0, duration_s=dur)
                all_results.append(res)
                print(f"{res['speed_mode']:<25} | {res['final_position_error_m']:<13.2f} | {res['max_position_error_m']:<12.2f} | {res['speed_mae_ms']:<15.4f} | {res['heading_mae_deg']:<13.2f}", flush=True)
                
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "Exp_6_LSTM_AbsoluteSpeedRatio", "evaluation"))
    os.makedirs(output_dir, exist_ok=True)
    report_file = os.path.join(output_dir, "trajectory_comparison_benchmark.json")
    with open(report_file, "w") as f:
        json.dump(all_results, f, indent=2)
        
    print(f"\n[OK] Benchmark completed successfully. Saved to: {report_file}", flush=True)


if __name__ == "__main__":
    run_full_suite()
