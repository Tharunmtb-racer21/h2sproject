import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from disturbance import DisturbanceDetector

class TestDisturbanceDetector(unittest.TestCase):

    def setUp(self):
        self.detector = DisturbanceDetector(g_ref=9.81)

    def test_smooth_driving_no_disturbance(self):
        # Smooth driving: 1g vertical, zero gyro
        res = self.detector.analyze_frame([0.5, 0.0, 9.81], [0.0, 0.0, 0.0])
        self.assertFalse(res['is_bump'])
        self.assertFalse(res['is_braking'])
        self.assertFalse(res['is_turning'])
        self.assertFalse(res['is_disturbance'])

    def test_road_bump_detection(self):
        # Bump: Vertical spike az = 14.5 m/s^2 (dev > 3.0)
        res = self.detector.analyze_frame([0.0, 0.0, 14.5], [0.0, 0.0, 0.0])
        self.assertTrue(res['is_bump'])
        self.assertTrue(res['is_disturbance'])
        self.assertGreater(res['confidence'], 0.5)

    def test_hard_braking_detection(self):
        # Hard braking: ax = -3.2 m/s^2
        res = self.detector.analyze_frame([-3.2, 0.0, 9.81], [0.0, 0.0, 0.0])
        self.assertTrue(res['is_braking'])
        self.assertTrue(res['is_disturbance'])

    def test_sharp_turn_detection(self):
        # Sharp turn: wz = 0.55 rad/s
        res = self.detector.analyze_frame([0.0, 0.5, 9.81], [0.0, 0.0, 0.55])
        self.assertTrue(res['is_turning'])
        self.assertTrue(res['is_disturbance'])

if __name__ == "__main__":
    unittest.main()
