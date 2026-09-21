"""
SIH26168 Dead-Reckoning Drift Diagnostic Script
Evaluates 10s, 30s, 60s, and 120s outages using exact PyTorch Exp_5 inference.
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.replay_engine import ReplayEngine


def run_drift_diagnostics():
    print("=" * 80)
    print("SIH26168 DEAD-RECKONING DRIFT DIAGNOSTIC TEST (10s, 30s, 60s, 120s)")
    print("=" * 80)

    durations = [10, 30, 60, 120]
    results = {}

    for dur in durations:
        # Re-initialize clean engine for each test
        engine = ReplayEngine()
        
        # Advance 100 steps (10 seconds) under normal GNSS
        for _ in range(100):
            engine.step(1)
            
        pre_outage = engine.get_current_frame()
        start_time = pre_outage["relative_time_s"]
        
        # Trigger outage
        engine.trigger_simulated_outage(duration_s=dur)
        
        n_steps = int(dur / 0.1)
        outage_frames = []
        max_err = 0.0
        
        for _ in range(n_steps):
            f = engine.step(1)
            outage_frames.append(f)
            if f["position_error_m"] > max_err:
                max_err = f["position_error_m"]
                
        post_outage = engine.get_current_frame()
        end_time = post_outage["relative_time_s"]
        
        ref_speeds = np.array([f["ref_speed_kmh"] / 3.6 for f in outage_frames])
        ai_speeds = np.array([f["displayed_speed_mps"] for f in outage_frames])
        
        ref_dist = np.sum(ref_speeds * 0.1)
        dr_dist = np.sum(ai_speeds * 0.1)
        
        final_err = post_outage["position_error_m"]
        mean_v_ai = np.mean(ai_speeds)
        mean_v_ref = np.mean(ref_speeds)
        
        heading_start = pre_outage["heading_deg"]
        heading_end = post_outage["heading_deg"]
        heading_change = (heading_end - heading_start + 180.0) % 360.0 - 180.0
        
        delta_v_vals = [f["last_inference_output"]["delta_v_mps"] for f in outage_frames if f.get("last_inference_output")]
        mean_delta_v = np.mean(delta_v_vals) if delta_v_vals else 0.0
        
        print(f"\n--- OUTAGE DURATION: {dur}s ({n_steps} steps @ dt=0.1s) ---")
        print(f"  Actual / Reference Distance: {ref_dist:.2f} m")
        print(f"  AI Estimated Distance:       {dr_dist:.2f} m (Distance Diff: {abs(dr_dist - ref_dist):.2f} m)")
        print(f"  Initial Position Error:      0.00 m")
        print(f"  Final Position Error:        {final_err:.2f} m")
        print(f"  Maximum Position Error:      {max_err:.2f} m")
        print(f"  Mean AI Velocity:            {mean_v_ai:.2f} m/s ({mean_v_ai*3.6:.1f} km/h)")
        print(f"  Mean Reference Velocity:     {mean_v_ref:.2f} m/s ({mean_v_ref*3.6:.1f} km/h)")
        print(f"  Mean AI Predicted Delta-V:   {mean_delta_v:.4f} m/s")
        print(f"  Heading Change:              {heading_change:.2f}° (Start: {heading_start:.1f}°, End: {heading_end:.1f}°)")
        print(f"  Sampling dt:                 0.1 s")
        
        results[dur] = {
            "ref_dist_m": ref_dist,
            "dr_dist_m": dr_dist,
            "final_error_m": final_err,
            "max_error_m": max_err,
            "mean_v_ai": mean_v_ai,
            "mean_v_ref": mean_v_ref,
            "mean_delta_v": mean_delta_v,
            "heading_change": heading_change,
            "dt": 0.1
        }
        
    print("\n" + "=" * 80)
    print("DIAGNOSTIC TEST COMPLETE")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_drift_diagnostics()
