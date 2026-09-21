import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dead_reckoning import DeadReckoningIntegrator

class TestDeadReckoningIntegrator(unittest.TestCase):

    def setUp(self):
        self.dr = DeadReckoningIntegrator()

    def test_straight_line_integration(self):
        # 10 seconds of straight motion at 5 m/s facing North (heading = 0)
        speeds = np.ones(1000) * 5.0
        yaw_rates = np.zeros(1000)
        
        dr_df = self.dr.integrate_sequence(speeds, yaw_rates, dt=0.01, start_heading=0.0)
        
        # Distance should be 50.0 meters along North
        self.assertAlmostEqual(self.dr.distance_traveled, 50.0, delta=0.5)
        self.assertAlmostEqual(self.dr.pos_north, 50.0, delta=0.5)
        self.assertAlmostEqual(self.dr.pos_east, 0.0, delta=0.1)

    def test_circular_turn_trajectory(self):
        # 90-degree turn
        speeds = np.ones(500) * 2.0
        yaw_rates = np.ones(500) * (np.pi / 10.0) # Turn pi/2 rad over 5 seconds
        
        dr_df = self.dr.integrate_sequence(speeds, yaw_rates, dt=0.01, start_heading=0.0)
        self.assertGreater(self.dr.distance_traveled, 9.5)
        self.assertNotEqual(dr_df['pos_east_m'].iloc[-1], 0.0)

if __name__ == "__main__":
    unittest.main()
