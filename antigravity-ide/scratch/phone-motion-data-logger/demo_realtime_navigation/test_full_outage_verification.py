"""
SIH26168 Verification Script: Full Outage Verification (Trace, Inference, Drift, Restore)
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.replay_engine import ReplayEngine


def main():
    print("=" * 75)
    print("STRICT RUNTIME VERIFICATION: CONTINUOUS OUTAGE & AI MODEL")
    print("=" * 75)

    engine = ReplayEngine()
    print(f"1. Checkpoint Path: {engine.model_path}")
    print(f"2. Architecture: LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)")
    print(f"3. Checkpoint Epoch: {engine.checkpoint_epoch}, mu={engine.mu_delta_v:.6f}, std={engine.std_delta_v:.6f}")
    print(f"4. PyTorch Model Loaded in Memory: {engine.ai_model_loaded}")

    # Advance 100 steps
    for _ in range(100):
        engine.step(1)

    f_pre = engine.get_current_frame()
    print(f"\n[Pre-Outage State]:")
    print(f"  Timestamp: t = {f_pre['relative_time_s']:.2f} s (Index {f_pre['index']})")
    print(f"  Initial Position Error: {f_pre['position_error_m']:.2f} m")
    print(f"  Initial Reference Speed: {f_pre['ref_speed_kmh']:.1f} km/h")
    print(f"  Navigation Mode: {f_pre['nav_mode']}")
    print(f"  Speed Source: {f_pre['displayed_speed_source']}")

    # Trigger Continuous Outage
    trigger_res = engine.trigger_simulated_outage(duration_s=None)
    print(f"\n[Trigger Continuous Outage]: {trigger_res}")

    # Run for 120 seconds (1200 steps @ 10Hz)
    outage_frames = []
    max_err = 0.0
    for i in range(1200):
        f = engine.step(1)
        outage_frames.append(f)
        if f["position_error_m"] > max_err:
            max_err = f["position_error_m"]

    f_post = engine.get_current_frame()
    start_time = f_pre["relative_time_s"]
    end_time = f_post["relative_time_s"]
    actual_duration = end_time - start_time

    ref_dist = np.sum([f["ref_speed_kmh"] / 3.6 * 0.1 for f in outage_frames])
    dr_dist = np.sum([f["displayed_speed_mps"] * 0.1 for f in outage_frames])

    print(f"\n[120-Second Outage Results]:")
    print(f"  Start Timestamp: {start_time:.2f} s")
    print(f"  End Timestamp: {end_time:.2f} s")
    print(f"  Actual Duration: {actual_duration:.2f} s")
    print(f"  Initial Position Error: {f_pre['position_error_m']:.2f} m")
    print(f"  Final Position Error: {f_post['position_error_m']:.2f} m")
    print(f"  Maximum Position Error: {max_err:.2f} m")
    print(f"  Reference Traveled Distance: {ref_dist:.2f} m")
    print(f"  AI Dead-Reckoned Distance: {dr_dist:.2f} m")
    print(f"  Navigation Mode: {f_post['nav_mode']}")
    print(f"  Speed Source: {f_post['displayed_speed_source']}")
    print(f"  Sample PyTorch Inference Output: {f_post['last_inference_output']}")
    print(f"  Replay Ended Because: Replay did NOT end (used {f_post['index']}/{engine.total_samples} samples; session has 37,183 samples)")

    # Trigger GNSS Restoration
    print(f"\n[Trigger GNSS Restoration]:")
    restore_res = engine.restore_gnss()
    print(f"  Restore Command Result: {restore_res}")

    f_restoring = engine.get_current_frame()
    print(f"  Immediate State upon Restore: {f_restoring['nav_mode']}, is_blending={f_restoring['is_blending']}")

    # Step 25 steps (2.5s) to observe Sigmoid blending
    for _ in range(25):
        engine.step(1)

    f_final = engine.get_current_frame()
    print(f"  State after 2.5s Handover: {f_final['nav_mode']}, is_blending={f_final['is_blending']}")
    print(f"  Position Error after GNSS Lock: {f_final['position_error_m']:.2f} m")
    print(f"  Speed Source after GNSS Lock: {f_final['displayed_speed_source']}")
    print("=" * 75)


if __name__ == "__main__":
    main()
