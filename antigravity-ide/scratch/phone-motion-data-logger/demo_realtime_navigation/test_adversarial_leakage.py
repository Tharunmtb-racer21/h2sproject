"""
SIH26168 - Adversarial Ground-Truth Leakage Proof Suite
Verifies that during GNSS-off operation (steps 1000-2200):
  Run A: Original Reference Telemetry
  Run B: NaN Corrupted Reference Telemetry during outage
  Run C: Adversarial Fake Reference Telemetry during outage (+10km pos, 3x speed, +180 deg hdg)

All three runs start from the identical pre-outage state at step 1000, and must produce 
100% numerically identical dead reckoning navigation outputs during the 120s outage.
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.replay_engine import ReplayEngine


def run_single_leakage_experiment(data_dir, mode="original", session_name="IOVNBD_S3c"):
    eng = ReplayEngine(data_dir=data_dir)
    eng.load_session(session_name)
    
    outage_start_idx = 1000
    outage_num_steps = 1200
    outage_end_idx = outage_start_idx + outage_num_steps
    
    # 1. Advance through GNSS-locked pre-outage phase (identical for all runs)
    for _ in range(outage_start_idx):
        eng.step(stride=1)
        
    rel_t = float(eng.df["relative_time_s"].iloc[outage_start_idx])
    eng.trigger_simulated_outage(duration_s=120.0)
    
    # 2. Corrupt DataFrame ONLY for the outage interval AFTER trigger anchor is saved
    if mode == "nan":
        corrupt_cols = ["latitude", "longitude", "reference_speed", "reference_heading", "ref_east_m", "ref_north_m"]
        for col in corrupt_cols:
            if col in eng.df.columns:
                eng.df.loc[outage_start_idx:outage_end_idx, col] = np.nan

    elif mode == "adversarial":
        if "ref_east_m" in eng.df.columns:
            eng.df.loc[outage_start_idx:outage_end_idx, "ref_east_m"] += 10000.0
        if "ref_north_m" in eng.df.columns:
            eng.df.loc[outage_start_idx:outage_end_idx, "ref_north_m"] += 10000.0
        if "latitude" in eng.df.columns:
            eng.df.loc[outage_start_idx:outage_end_idx, "latitude"] += 0.1
        if "longitude" in eng.df.columns:
            eng.df.loc[outage_start_idx:outage_end_idx, "longitude"] += 0.1
        if "reference_speed" in eng.df.columns:
            eng.df.loc[outage_start_idx:outage_end_idx, "reference_speed"] *= 3.0
        if "reference_heading" in eng.df.columns:
            eng.df.loc[outage_start_idx:outage_end_idx, "reference_heading"] = (
                eng.df.loc[outage_start_idx:outage_end_idx, "reference_heading"] + 180.0
            ) % 360.0

    # 3. Propagate 120s GNSS outage and record dead reckoning outputs
    trajectory = []
    for _ in range(outage_num_steps):
        frame = eng.step(stride=1)
        if frame:
            trajectory.append((
                frame["active_east_m"],
                frame["active_north_m"],
                frame["heading_deg"],
                frame["displayed_speed_mps"]
            ))
            
    return trajectory


def test_adversarial_leakage():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "iovnbd_selected"))
    
    print("Executing Run A (Original Reference Telemetry)...")
    traj_a = run_single_leakage_experiment(data_dir, mode="original")
    
    print("Executing Run B (NaN Corrupted Reference Telemetry during outage)...")
    traj_b = run_single_leakage_experiment(data_dir, mode="nan")
    
    print("Executing Run C (Adversarial Fake Telemetry: +10km pos, 3x speed, +180 deg hdg)...")
    traj_c = run_single_leakage_experiment(data_dir, mode="adversarial")
    
    assert len(traj_a) == len(traj_b) == len(traj_c), "Trajectory step count mismatch"
    
    max_ab_e = max(abs(a[0] - b[0]) for a, b in zip(traj_a, traj_b))
    max_ab_n = max(abs(a[1] - b[1]) for a, b in zip(traj_a, traj_b))
    max_ab_h = max(abs(a[2] - b[2]) for a, b in zip(traj_a, traj_b))
    max_ab_v = max(abs(a[3] - b[3]) for a, b in zip(traj_a, traj_b))
    
    max_ac_e = max(abs(a[0] - c[0]) for a, c in zip(traj_a, traj_c))
    max_ac_n = max(abs(a[1] - c[1]) for a, c in zip(traj_a, traj_c))
    max_ac_h = max(abs(a[2] - c[2]) for a, c in zip(traj_a, traj_c))
    max_ac_v = max(abs(a[3] - c[3]) for a, c in zip(traj_a, traj_c))
    
    print("\n======================================================================")
    print("ADVERSARIAL LEAKAGE PROOF MATRIX (1200 Timesteps @ 10Hz)")
    print("======================================================================")
    print(f"Run A (Original) vs Run B (NaN Corrupted):")
    print(f"  Max East Difference    : {max_ab_e:.10f} m")
    print(f"  Max North Difference   : {max_ab_n:.10f} m")
    print(f"  Max Heading Difference : {max_ab_h:.10f} deg")
    print(f"  Max Speed Difference   : {max_ab_v:.10f} m/s")
    print("----------------------------------------------------------------------")
    print(f"Run A (Original) vs Run C (Adversarial +10km / 3x Speed / +180 deg Hdg):")
    print(f"  Max East Difference    : {max_ac_e:.10f} m")
    print(f"  Max North Difference   : {max_ac_n:.10f} m")
    print(f"  Max Heading Difference : {max_ac_h:.10f} deg")
    print(f"  Max Speed Difference   : {max_ac_v:.10f} m/s")
    print("======================================================================")
    
    assert max_ab_e < 1e-6 and max_ab_n < 1e-6 and max_ab_h < 1e-6 and max_ab_v < 1e-6, "Run B NaN leakage detected"
    assert max_ac_e < 1e-6 and max_ac_n < 1e-6 and max_ac_h < 1e-6 and max_ac_v < 1e-6, "Run C Adversarial leakage detected"
    
    print("\n[SUCCESS] ADVERSARIAL LEAKAGE TEST PASSED: 100% Numerical Identity Across Runs A, B, and C.")


if __name__ == "__main__":
    test_adversarial_leakage()
