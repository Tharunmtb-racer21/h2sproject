"""
SIH26168 Three-Mode Navigation Performance Evaluation
Evaluates identical 120-second GNSS outages under three distinct operating modes:
  Mode A: AI Speed (PyTorch Exp_5 LSTM) + Calibrated Gyro Heading
  Mode B: Constant Anchor Speed (v0) + Calibrated Gyro Heading
  Mode C: Reference Diagnostic (Ground-Truth Speed & Heading - Evaluation Diagnostic ONLY)

Prints explicit performance metrics: Final Error, Max Error, Mean Error, Speed MAE/RMSE, Heading MAE/RMSE.
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.replay_engine import ReplayEngine


def run_mode_eval(session_name="IOVNBD_S3c", mode="A", outage_start_s=100.0, duration_s=120.0):
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "iovnbd_selected"))
    eng = ReplayEngine(data_dir=data_dir)
    eng.load_session(session_name)
    
    # Fast forward to outage start
    start_idx = 0
    for i in range(eng.total_samples - 1):
        if float(eng.df["relative_time_s"].iloc[i]) >= outage_start_s:
            start_idx = i
            break
        eng.step(stride=1)
        
    rel_t = float(eng.df["relative_time_s"].iloc[start_idx])
    v_anchor = float(eng.df["reference_speed"].iloc[start_idx])
    
    eng.trigger_simulated_outage(duration_s=duration_s)
    
    num_steps = int(round(duration_s / 0.1))
    
    pos_errors = []
    east_errors = []
    north_errors = []
    speed_diffs = []
    heading_diffs = []
    
    for step_i in range(num_steps):
        idx = start_idx + step_i
        if idx >= eng.total_samples - 1:
            break
            
        row = eng.df.iloc[idx]
        ref_e = float(row["ref_east_m"])
        ref_n = float(row["ref_north_m"])
        ref_v = float(row["reference_speed"])
        ref_h = float(row["reference_heading"])
        
        if mode == "A":
            # Mode A: AI Speed + Calibrated Gyro Heading
            frame = eng.step(stride=1)
            dr_e = frame["active_east_m"]
            dr_n = frame["active_north_m"]
            dr_v = frame["displayed_speed_mps"]
            dr_h = frame["heading_deg"]
            
        elif mode == "B":
            # Mode B: Constant Anchor Speed + Calibrated Gyro Heading
            accel_x = float(row['accel_x'])
            accel_y = float(row['accel_y'])
            accel_z = float(row['accel_z'])
            gyro_y = float(row['gyro_y']) if 'gyro_y' in row else 0.0
            yaw_rate_raw = -gyro_y
            
            yaw_debiased = yaw_rate_raw - eng.online_gyro_bias
            yaw_scaled = yaw_debiased * eng.online_yaw_scale
            eng.yaw_rate_ema = 0.4 * yaw_scaled + 0.6 * eng.yaw_rate_ema
            yaw_corrected = float(np.clip(eng.yaw_rate_ema, -np.radians(90), np.radians(90)))
            eng.nav_core.update_heading(yaw_corrected, dt=0.1)
            
            dr_state = eng.nav_core.propagate_step(speed_mps=v_anchor, heading_deg=None, dt=0.1)
            dr_e = dr_state["pos_east_m"]
            dr_n = dr_state["pos_north_m"]
            dr_v = v_anchor
            dr_h = dr_state["heading_deg"]
            eng.current_index = idx + 1
            
        elif mode == "C":
            # Mode C: Reference Diagnostic (Evaluation Diagnostic ONLY)
            dr_state = eng.nav_core.propagate_step(speed_mps=ref_v, heading_deg=ref_h, dt=0.1)
            dr_e = dr_state["pos_east_m"]
            dr_n = dr_state["pos_north_m"]
            dr_v = ref_v
            dr_h = ref_h
            eng.current_index = idx + 1
            
        err = float(np.sqrt((dr_e - ref_e)**2 + (dr_n - ref_n)**2))
        pos_errors.append(err)
        east_errors.append(abs(dr_e - ref_e))
        north_errors.append(abs(dr_n - ref_n))
        speed_diffs.append(dr_v - ref_v)
        
        h_diff = abs((dr_h - ref_h + 180.0) % 360.0 - 180.0)
        heading_diffs.append(h_diff)

    speed_mae = float(np.mean(np.abs(speed_diffs)))
    speed_rmse = float(np.sqrt(np.mean(np.square(speed_diffs))))
    
    hdg_mae = float(np.mean(heading_diffs))
    hdg_rmse = float(np.sqrt(np.mean(np.square(heading_diffs))))
    
    return {
        "mode": mode,
        "session": session_name,
        "final_err_m": round(pos_errors[-1], 2),
        "max_err_m": round(float(np.max(pos_errors)), 2),
        "mean_err_m": round(float(np.mean(pos_errors)), 2),
        "east_err_m": round(float(np.mean(east_errors)), 2),
        "north_err_m": round(float(np.mean(north_errors)), 2),
        "speed_mae_mps": round(speed_mae, 2),
        "speed_rmse_mps": round(speed_rmse, 2),
        "hdg_mae_deg": round(hdg_mae, 2),
        "hdg_rmse_deg": round(hdg_rmse, 2),
    }


def main():
    print("=======================================================================================================================")
    print("THREE-MODE NAVIGATION PERFORMANCE COMPARISON MATRIX (120s OUTAGE EVALUATION)")
    print("=======================================================================================================================")
    print(f"{'Session':<12} | {'Mode':<6} | {'FinalErr':<8} | {'MaxErr':<8} | {'MeanErr':<8} | {'EastErr':<7} | {'NorthErr':<8} | {'Speed MAE/RMSE':<15} | {'Hdg MAE/RMSE'}")
    print("-----------------------------------------------------------------------------------------------------------------------")
    
    for sess in ["IOVNBD_S3c", "IOVNBD_S3a"]:
        for mode, name in [("A", "Mode A (AI Speed + Gyro)"), ("B", "Mode B (Anchor Speed + Gyro)"), ("C", "Mode C (Ref Diag - EVAL ONLY)")]:
            res = run_mode_eval(sess, mode=mode, outage_start_s=100.0, duration_s=120.0)
            print(f"{sess:<12} | {mode:<6} | {res['final_err_m']:<7.2f}m | {res['max_err_m']:<7.2f}m | {res['mean_err_m']:<7.2f}m | {res['east_err_m']:<6.2f}m | {res['north_err_m']:<7.2f}m | {res['speed_mae_mps']:.2f} / {res['speed_rmse_mps']:.2f} m/s | {res['hdg_mae_deg']:.2f} / {res['hdg_rmse_deg']:.2f} deg")
        print("-----------------------------------------------------------------------------------------------------------------------")

    print("=======================================================================================================================")


if __name__ == "__main__":
    main()
