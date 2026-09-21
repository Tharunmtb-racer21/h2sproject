"""
SIH26168 - Reconciled Benchmark Suite
Executes reproducible evaluation of GNSS outages on IO-VNBD datasets.
Prints explicit metrics for every session and outage length.
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.replay_engine import ReplayEngine


def reconcile_outage_benchmark(session_name="IOVNBD_S3c", outage_start_s=100.0, duration_s=120.0):
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "iovnbd_selected"))
    eng = ReplayEngine(data_dir=data_dir)
    eng.load_session(session_name)
    
    # Fast forward to outage start time
    start_idx = 0
    for i in range(eng.total_samples - 1):
        if float(eng.df["relative_time_s"].iloc[i]) >= outage_start_s:
            start_idx = i
            break
        eng.step(stride=1)
        
    rel_t = float(eng.df["relative_time_s"].iloc[start_idx])
    eng.trigger_simulated_outage(
        duration_s=duration_s,
    )
    
    num_steps = int(round(duration_s / 0.1))
    
    pos_errors = []
    heading_errors = []
    speed_errors = []
    
    for _ in range(num_steps):
        if eng.current_index >= eng.total_samples - 1:
            break
        idx = eng.current_index
        frame = eng.step(stride=1)
        if frame:
            pos_errors.append(frame["position_error_m"])
            ref_hdg = float(eng.df["reference_heading"].iloc[idx])
            dr_hdg = frame["heading_deg"]
            hdg_err = abs((dr_hdg - ref_hdg + 180.0) % 360.0 - 180.0)
            heading_errors.append(hdg_err)
            
            ref_v = float(eng.df["reference_speed"].iloc[idx])
            dr_v = frame["displayed_speed_mps"]
            speed_errors.append(abs(dr_v - ref_v))

    start_e = float(eng.df["ref_east_m"].iloc[start_idx])
    start_n = float(eng.df["ref_north_m"].iloc[start_idx])
    end_idx = min(start_idx + len(pos_errors), eng.total_samples - 1)
    end_e = float(eng.df["ref_east_m"].iloc[end_idx])
    end_n = float(eng.df["ref_north_m"].iloc[end_idx])
    
    dist_traveled = float(np.sqrt((end_e - start_e)**2 + (end_n - start_n)**2))
    
    return {
        "session": session_name,
        "start_time_s": rel_t,
        "start_idx": start_idx,
        "duration_s": duration_s,
        "freq_hz": 10.0,
        "steps": len(pos_errors),
        "final_error_m": round(pos_errors[-1], 2) if pos_errors else 0.0,
        "max_error_m": round(float(np.max(pos_errors)), 2) if pos_errors else 0.0,
        "mean_error_m": round(float(np.mean(pos_errors)), 2) if pos_errors else 0.0,
        "dist_traveled_m": round(dist_traveled, 2),
        "heading_error_mean_deg": round(float(np.mean(heading_errors)), 2) if heading_errors else 0.0,
        "speed_mae_mps": round(float(np.mean(speed_errors)), 2) if speed_errors else 0.0,
        "ref_only_for_eval": True
    }


def main():
    print("==========================================================================================================")
    print("RECONCILED BENCHMARK REPORT (REPRODUCIBLE AUDIT DATA)")
    print("==========================================================================================================")
    print(f"{'Session':<12} | {'Dur':<4} | {'Steps':<5} | {'FinalErr':<8} | {'MaxErr':<8} | {'MeanErr':<8} | {'DistTraveled':<12} | {'HdgErr':<7} | {'SpeedMAE':<8} | {'EvalOnly'}")
    print("----------------------------------------------------------------------------------------------------------")
    
    configs = [
        ("IOVNBD_S3c", 100.0, 10.0),
        ("IOVNBD_S3c", 100.0, 30.0),
        ("IOVNBD_S3c", 100.0, 60.0),
        ("IOVNBD_S3c", 100.0, 120.0),
        ("IOVNBD_S3a", 100.0, 30.0),
        ("IOVNBD_S3a", 100.0, 60.0),
        ("IOVNBD_S3a", 100.0, 120.0),
    ]
    
    for sess, st, dur in configs:
        res = reconcile_outage_benchmark(sess, st, dur)
        print(f"{res['session']:<12} | {res['duration_s']:<4.0f}s | {res['steps']:<5d} | {res['final_error_m']:<7.2f}m | {res['max_error_m']:<7.2f}m | {res['mean_error_m']:<7.2f}m | {res['dist_traveled_m']:<10.2f}m | {res['heading_error_mean_deg']:<5.2f} deg | {res['speed_mae_mps']:<6.2f} m/s | {res['ref_only_for_eval']}")

    print("==========================================================================================================")


if __name__ == "__main__":
    main()
