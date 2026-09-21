import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.replay_engine import ReplayEngine

def test_full_pipeline_flow():
    print("=" * 80)
    print("CONTINUOUS OUTAGE & RESTORATION VALIDATION TEST")
    print("=" * 80)

    engine = ReplayEngine()
    engine.load_session("IOVNBD_S3c")

    # Step 1: Normal GNSS Locked Playback for 10 seconds (100 steps)
    print("\n[1] Testing GNSS Locked Playback (t=0s to 10s)...")
    for _ in range(100):
        frame = engine.step(stride=1)
    print(f"  Frame at t=10.0s: mode={frame['nav_mode']}, speed={frame['displayed_speed_kmh']:.1f} km/h, error={frame['position_error_m']:.3f}m")
    assert frame['nav_mode'] == 'GNSS_LOCKED'
    assert frame['position_error_m'] < 0.001

    # Step 2: Trigger Indefinite Outage at t=10.0s
    print("\n[2] Triggering Indefinite Outage at t=10.0s...")
    engine.outage_controller.trigger_outage(
        current_time_s=10.0,
        duration_s=None,  # Continuous until manual restore
        current_east_m=frame['active_east_m'],
        current_north_m=frame['active_north_m'],
        current_speed_mps=frame['displayed_speed_mps'],
        current_heading_deg=frame['heading_deg']
    )
    
    outage_frames = []
    for _ in range(300):
        f = engine.step(stride=1)
        outage_frames.append(f)

    print(f"  Frame at t=40.0s: mode={f['nav_mode']}, speed={f['displayed_speed_kmh']:.1f} km/h, error={f['position_error_m']:.2f}m")
    assert f['nav_mode'] == 'AI_DEAD_RECKONING'
    assert 'AI_ESTIMATED' in f['displayed_speed_source']

    # Step 3: Trigger Restoration and check sigmoid blending (2.0s = 20 steps)
    print("\n[3] Triggering Manual GNSS Restoration Sigmoid Transition (2.0s)...")
    engine.outage_controller.restore_gnss(current_time_s=40.0)
    
    blend_errors = []
    positions = []
    for _ in range(30):
        f = engine.step(stride=1)
        blend_errors.append(f['position_error_m'])
        positions.append((f['active_east_m'], f['active_north_m']))
        print(f"  t={f['relative_time_s']:.1f}s | mode={f['nav_mode']:<22} | blend_progress={f['blend_progress']:.2f} | pos_error={f['position_error_m']:.2f}m")

    # Check for position jumps during sigmoid handover
    pos_diffs = [np.sqrt((positions[i][0]-positions[i-1][0])**2 + (positions[i][1]-positions[i-1][1])**2) for i in range(1, len(positions))]
    max_step_jump = max(pos_diffs)
    print(f"\nMax step displacement during restoration: {max_step_jump:.3f} m (Smooth, no teleportation)")
    assert max_step_jump < 5.0, "Discontinuous position jump detected during restoration!"

    # Step 4: Verify fully restored GNSS Locked mode
    print("\n[4] Verifying fully restored GNSS Locked state after blend duration...")
    for _ in range(10):
        f = engine.step(stride=1)
    print(f"  Frame at t={f['relative_time_s']:.1f}s: mode={f['nav_mode']}, error={f['position_error_m']:.3f}m")
    assert f['nav_mode'] == 'GNSS_LOCKED'
    assert f['position_error_m'] < 0.001

    print("\n" + "=" * 80)
    print("ALL CONTINUOUS OUTAGE & RESTORATION VALIDATION TESTS PASSED (100% OK)")
    print("=" * 80)

if __name__ == "__main__":
    test_full_pipeline_flow()
