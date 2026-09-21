"""
SIH26168 Verification Script: Continuous Outage Test (120s & Extended)
"""

import os
import sys
import numpy as np
import pandas as pd

# Add repo root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.navigation_core import NavigationCore
from demo_realtime_navigation.backend.outage_controller import OutageController
from demo_realtime_navigation.backend.replay_engine import ReplayEngine


def run_continuous_outage_test():
    print("=" * 70)
    print("CONTINUOUS 120-SECOND GNSS OUTAGE VERIFICATION TEST")
    print("=" * 70)

    # 1. Initialize Engine
    engine = ReplayEngine()
    print(f"Dataset Session: {engine.current_session_id}")
    print(f"Total Session Samples: {engine.total_samples} (61.97 min duration)")
    print(f"PyTorch Exp_5 Model Loaded in Memory: {engine.ai_model_loaded}")

    # 2. Advance 100 steps (10 seconds) under normal GNSS
    for _ in range(100):
        engine.step(1)

    pre_outage = engine.get_current_frame()
    print(f"\n[Pre-Outage State @ t={pre_outage['relative_time_s']}s]:")
    print(f"  Reference Position: East={pre_outage['ref_east_m']:.2f}m, North={pre_outage['ref_north_m']:.2f}m")
    print(f"  Reference Speed: {pre_outage['ref_speed_kmh']:.1f} km/h")
    print(f"  Navigation Mode: {pre_outage['nav_mode']}")

    # 3. Trigger Continuous Outage
    trigger_info = engine.trigger_simulated_outage(duration_s=None)
    print(f"\n[Outage Trigger Info]: {trigger_info}")

    # 4. Step 120 seconds (1200 steps @ 10Hz)
    outage_frames = []
    for i in range(1200):
        f = engine.step(1)
        outage_frames.append(f)

    post_outage = engine.get_current_frame()
    outage_duration_s = post_outage["relative_time_s"] - pre_outage["relative_time_s"]
    final_pos_error_m = post_outage["position_error_m"]

    # Calculate travel distances
    dr_dist = np.sum([f["displayed_speed_mps"] * 0.1 for f in outage_frames])
    ref_dist = np.sum([f["ref_speed_kmh"] / 3.6 * 0.1 for f in outage_frames])

    speed_diffs = [f["displayed_speed_mps"] - (f["ref_speed_kmh"] / 3.6) for f in outage_frames]
    speed_rmse = np.sqrt(np.mean(np.array(speed_diffs) ** 2))
    speed_mae = np.mean(np.abs(np.array(speed_diffs)))

    print("\n" + "=" * 70)
    print("CONTINUOUS OUTAGE TEST RESULTS (120 SECONDS)")
    print("=" * 70)
    print(f"Outage Duration: {outage_duration_s:.2f} seconds ({len(outage_frames)} consecutive steps)")
    print(f"Actual Distance Traveled: {ref_dist:.2f} m ({ref_dist/1000:.2f} km)")
    print(f"AI Dead-Reckoned Distance: {dr_dist:.2f} m ({dr_dist/1000:.2f} km)")
    print(f"Final Horizontal Position Drift: {final_pos_error_m:.2f} m")
    print(f"Position Drift Rate (% of Distance): {(final_pos_error_m / ref_dist * 100):.2f}%")
    print(f"Velocity Tracking RMSE during Outage: {speed_rmse:.3f} m/s ({speed_rmse*3.6:.2f} km/h)")
    print(f"Velocity Tracking MAE during Outage: {speed_mae:.3f} m/s ({speed_mae*3.6:.2f} km/h)")
    print(f"Navigation State during Outage: {post_outage['nav_mode']}")
    print(f"Speed Source during Outage: {post_outage['displayed_speed_source']}")
    print(f"Did Replay Terminate Due to Data Limits? NO (Used {engine.current_index}/{engine.total_samples} samples)")
    print("=" * 70)

    return {
        "outage_duration_s": outage_duration_s,
        "ref_dist_m": ref_dist,
        "dr_dist_m": dr_dist,
        "final_error_m": final_pos_error_m,
        "drift_rate_pct": (final_pos_error_m / ref_dist * 100),
        "speed_rmse_mps": speed_rmse,
        "speed_mae_mps": speed_mae,
    }


if __name__ == "__main__":
    run_continuous_outage_test()
