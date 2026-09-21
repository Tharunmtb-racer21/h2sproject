import sys
import os
import unittest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fusion_engine import GNSSIMUFusionEngine

class TestGNSSIMUFusionEngine(unittest.TestCase):

    def setUp(self):
        self.fusion = GNSSIMUFusionEngine(t_blend_s=2.0)
        
        times = np.linspace(0, 50, 500)
        self.df_proc = pd.DataFrame({
            'relative_time_s': times,
            'latitude': 11.0 + times * 0.0001,
            'longitude': 76.9 + times * 0.0001,
            'flag_gnss_valid': np.ones(500, dtype=int)
        })
        
        self.dr_df = pd.DataFrame({
            'dr_latitude': 11.0 + times * 0.00012,
            'dr_longitude': 76.9 + times * 0.00012
        })

    def test_fusion_modes_and_sigmoid_handover(self):
        fused_df = self.fusion.fuse_trajectory(self.df_proc, self.dr_df, simulated_outage_start=10.0, simulated_outage_duration=15.0)
        
        # Check GNSS_FIX before outage (t = 5s)
        row_gnss = fused_df[np.isclose(fused_df['relative_time_s'], 5.0, atol=0.2)].iloc[0]
        self.assertEqual(row_gnss['fusion_mode'], 'GNSS_FIX')
        self.assertEqual(row_gnss['handover_blend_weight'], 1.0)
        
        # Check DEAD_RECKONING during outage (t = 15s)
        row_dr = fused_df[np.isclose(fused_df['relative_time_s'], 15.0, atol=0.2)].iloc[0]
        self.assertEqual(row_dr['fusion_mode'], 'DEAD_RECKONING')
        self.assertEqual(row_dr['handover_blend_weight'], 0.0)
        
        # Check SIGMOID_HANDOVER right after outage (t = 26.0s, outage ends at 25s)
        row_handover = fused_df[(fused_df['relative_time_s'] >= 25.5) & (fused_df['relative_time_s'] <= 26.5)].iloc[0]
        self.assertEqual(row_handover['fusion_mode'], 'SIGMOID_HANDOVER')
        self.assertGreater(row_handover['handover_blend_weight'], 0.0)
        self.assertLess(row_handover['handover_blend_weight'], 1.0)

if __name__ == "__main__":
    unittest.main()
