import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from alignment import PhoneToVehicleAligner

class TestPhoneToVehicleAligner(unittest.TestCase):

    def setUp(self):
        self.aligner = PhoneToVehicleAligner(g_ref=9.81)

    def test_static_pitch_roll_calculation(self):
        # Static gravity pointing along +Z (phone flat on table face up)
        accel_flat = [0.0, 0.0, 9.81]
        pitch, roll = self.aligner.calibrate_static_pitch_roll(accel_flat)
        self.assertAlmostEqual(pitch, 0.0, places=2)
        self.assertAlmostEqual(roll, 0.0, places=2)

        # Phone mounted upright at pitch 90 deg (ax = -9.81, ay=0, az=0)
        accel_upright = [-9.81, 0.0, 0.0]
        pitch_upright, roll_upright = self.aligner.calibrate_static_pitch_roll(accel_upright)
        self.assertAlmostEqual(pitch_upright, np.pi/2, places=2)

    def test_mounting_orientation_shift_detection(self):
        # Initial calibration flat
        self.aligner.calibrate_static_pitch_roll([0.0, 0.0, 9.81])
        
        # Small noise (no shift)
        is_shifted, angle = self.aligner.detect_mounting_shift([0.2, 0.1, 9.80], threshold_deg=12.0)
        self.assertFalse(is_shifted)
        
        # Large bump tilt shift (30 deg shift)
        accel_tilted = [0.0, 4.905, 8.495] # ~30 deg roll tilt
        is_shifted, angle = self.aligner.detect_mounting_shift(accel_tilted, threshold_deg=12.0)
        self.assertTrue(is_shifted)
        self.assertGreater(angle, 25.0)

    def test_transform_vector(self):
        self.aligner.calibrate_static_pitch_roll([0.0, 0.0, 9.81])
        accel_v, gyro_v = self.aligner.transform_to_vehicle_frame([1.0, 0.5, 9.81], [0.1, 0.0, 0.0])
        self.assertEqual(len(accel_v), 3)
        self.assertEqual(len(gyro_v), 3)

if __name__ == "__main__":
    unittest.main()
