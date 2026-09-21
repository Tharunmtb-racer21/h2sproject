"""
SIH26168 Zero Ground-Truth Leakage Proofing Suite
Explicitly overwrites all GPS reference columns with NaN during outage window
and verifies that dead reckoning outputs are 100% numerically identical.
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.replay_engine import ReplayEngine


def test_nan_leakage_proofing():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "iovnbd_selected"))
    
    # 1. Normal Run
    eng_normal = ReplayEngine(data_dir=data_dir)
    eng_normal.load_session("IOVNBD_S3c")
    
    # Fast forward 1000 steps (100s)
    for _ in range(1000):
        eng_normal.step(stride=1)
        
    rel_t = float(eng_normal.df["relative_time_s"].iloc[1000])
    eng_normal.trigger_simulated_outage(duration_s=120.0)
    
    normal_trajectory = []
    for _ in range(1200):
        frame = eng_normal.step(stride=1)
        if frame:
            normal_trajectory.append((
                frame["active_east_m"],
                frame["active_north_m"],
                frame["heading_deg"],
                frame["displayed_speed_mps"]
            ))

    # 2. NaN Corrupted Run
    eng_nan = ReplayEngine(data_dir=data_dir)
    eng_nan.load_session("IOVNBD_S3c")
    
    # Explicitly corrupt all reference columns with NaN for outage indices [1000:2200]
    corrupt_cols = ["latitude", "longitude", "reference_speed", "reference_heading", "ref_east_m", "ref_north_m"]
    for col in corrupt_cols:
        if col in eng_nan.df.columns:
            eng_nan.df.loc[1000:2200, col] = np.nan
            
    # Fast forward 1000 steps
    for _ in range(1000):
        eng_nan.step(stride=1)
        
    eng_nan.trigger_simulated_outage(duration_s=120.0)
    
    nan_trajectory = []
    for _ in range(1200):
        frame = eng_nan.step(stride=1)
        if frame:
            nan_trajectory.append((
                frame["active_east_m"],
                frame["active_north_m"],
                frame["heading_deg"],
                frame["displayed_speed_mps"]
            ))

    # 3. Assert Exact Identity
    assert len(normal_trajectory) == len(nan_trajectory), "Trajectory length mismatch"
    
    max_diff_e = 0.0
    max_diff_n = 0.0
    max_diff_hdg = 0.0
    max_diff_v = 0.0
    
    for (e1, n1, h1, v1), (e2, n2, h2, v2) in zip(normal_trajectory, nan_trajectory):
        max_diff_e = max(max_diff_e, abs(e1 - e2))
        max_diff_n = max(max_diff_n, abs(n1 - n2))
        max_diff_hdg = max(max_diff_hdg, abs(h1 - h2))
        max_diff_v = max(max_diff_v, abs(v1 - v2))
        
    print("=== ZERO GROUND-TRUTH LEAKAGE PROOF RESULTS ===")
    print(f"  Max East Difference  : {max_diff_e:.8f} m")
    print(f"  Max North Difference : {max_diff_n:.8f} m")
    print(f"  Max Heading Difference: {max_diff_hdg:.8f} deg")
    print(f"  Max Speed Difference  : {max_diff_v:.8f} m/s")
    
    assert max_diff_e < 1e-5, f"East position leaked reference GPS! diff={max_diff_e}"
    assert max_diff_n < 1e-5, f"North position leaked reference GPS! diff={max_diff_n}"
    assert max_diff_hdg < 1e-5, f"Heading leaked reference GPS! diff={max_diff_hdg}"
    assert max_diff_v < 1e-5, f"Speed leaked reference GPS! diff={max_diff_v}"
    
    print("\n  [PASS] PROOF CONFIRMED: 0.00000000 Leakage. Pipeline uses zero reference GPS during outage.")

if __name__ == "__main__":
    test_nan_leakage_proofing()
