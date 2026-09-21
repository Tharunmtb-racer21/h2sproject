"""
SIH26168 Synthetic Kinematic & Frontend Arrow Orientation Suite
Tests:
1. North motion for 10s (Hdg 0 deg): pos_n increases, pos_e = 0.
2. East motion for 10s (Hdg 90 deg): pos_e increases, pos_n const.
3. South motion for 10s (Hdg 180 deg): pos_n decreases, pos_e const.
4. West motion for 10s (Hdg 270 deg): pos_e decreases, pos_n const.
5. Full 40s Square loop returning to origin (0,0).
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.navigation_core import NavigationCore


def test_synthetic_square_trajectory():
    nav = NavigationCore()
    nav.reset(origin_lat=52.37938, origin_lon=-1.261814, origin_heading_deg=0.0)
    
    speed_mps = 10.0  # 10 m/s = 36 km/h
    dt = 0.1         # 10 Hz
    
    # 1. North for 10 seconds (100 steps) -> Hdg 0 deg
    for _ in range(100):
        nav.propagate_step(speed_mps=speed_mps, heading_deg=0.0, dt=dt)
        
    print(f"Segment 1 (North 100m) : Pos=(E:{nav.pos_east_m:.2f}m, N:{nav.pos_north_m:.2f}m), Hdg={np.degrees(nav.heading_rad):.1f} deg")
    assert abs(nav.pos_east_m - 0.0) < 1e-3, f"East error in North segment: {nav.pos_east_m}"
    assert abs(nav.pos_north_m - 100.0) < 1e-3, f"North error in North segment: {nav.pos_north_m}"
    
    # 2. East for 10 seconds (100 steps) -> Hdg 90 deg
    for _ in range(100):
        nav.propagate_step(speed_mps=speed_mps, heading_deg=90.0, dt=dt)
        
    print(f"Segment 2 (East 100m)  : Pos=(E:{nav.pos_east_m:.2f}m, N:{nav.pos_north_m:.2f}m), Hdg={np.degrees(nav.heading_rad):.1f} deg")
    assert abs(nav.pos_east_m - 100.0) < 1e-3, f"East error in East segment: {nav.pos_east_m}"
    assert abs(nav.pos_north_m - 100.0) < 1e-3, f"North error in East segment: {nav.pos_north_m}"
    
    # 3. South for 10 seconds (100 steps) -> Hdg 180 deg
    for _ in range(100):
        nav.propagate_step(speed_mps=speed_mps, heading_deg=180.0, dt=dt)
        
    print(f"Segment 3 (South 100m) : Pos=(E:{nav.pos_east_m:.2f}m, N:{nav.pos_north_m:.2f}m), Hdg={np.degrees(nav.heading_rad):.1f} deg")
    assert abs(nav.pos_east_m - 100.0) < 1e-3, f"East error in South segment: {nav.pos_east_m}"
    assert abs(nav.pos_north_m - 0.0) < 1e-3, f"North error in South segment: {nav.pos_north_m}"
    
    # 4. West for 10 seconds (100 steps) -> Hdg 270 deg
    for _ in range(100):
        nav.propagate_step(speed_mps=speed_mps, heading_deg=270.0, dt=dt)
        
    print(f"Segment 4 (West 100m)  : Pos=(E:{nav.pos_east_m:.2f}m, N:{nav.pos_north_m:.2f}m), Hdg={np.degrees(nav.heading_rad):.1f} deg")
    assert abs(nav.pos_east_m - 0.0) < 1e-3, f"East error in West segment: {nav.pos_east_m}"
    assert abs(nav.pos_north_m - 0.0) < 1e-3, f"North error in West segment: {nav.pos_north_m}"
    
    print("\n[SUCCESS] SYNTHETIC SQUARE TRAJECTORY TEST PASSED: Kinematic coordinate convention verified.")


if __name__ == "__main__":
    test_synthetic_square_trajectory()
