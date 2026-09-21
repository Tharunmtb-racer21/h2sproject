import sys
import os
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from outage_simulator import GNSSOutageSimulator

class TestGNSSOutageSimulator(unittest.TestCase):

    def setUp(self):
        # Create dummy dataframe with relative_time_s from 0 to 60s
        times = np.linspace(0, 60, 600)
        self.df = pd.DataFrame({
            'relative_time_s': times,
            'latitude': 11.0168 + times * 0.0001,
            'longitude': 76.9558 + times * 0.0001,
            'gnss_speed_m_s': np.ones(600) * 5.0,
            'gnss_accuracy': np.ones(600) * 3.0,
            'flag_gnss_valid': np.ones(600, dtype=int)
        })

    def test_outage_masking(self):
        simulator = GNSSOutageSimulator(start_time_s=15.0, duration_s=20.0)
        masked_df = simulator.apply_outage_mask(self.df)
        
        # Check non-outage period (t < 15s)
        self.assertEqual(masked_df['flag_gnss_valid'].iloc[50], 1)
        self.assertFalse(np.isnan(masked_df['latitude'].iloc[50]))
        
        # Check outage period (15s <= t <= 35s)
        outage_rows = masked_df[(masked_df['relative_time_s'] >= 15.0) & (masked_df['relative_time_s'] <= 35.0)]
        self.assertTrue(outage_rows['latitude'].isnull().all())
        self.assertTrue((outage_rows['flag_gnss_valid'] == 0).all())
        self.assertTrue((outage_rows['flag_simulated_outage'] == 1).all())

if __name__ == "__main__":
    unittest.main()
