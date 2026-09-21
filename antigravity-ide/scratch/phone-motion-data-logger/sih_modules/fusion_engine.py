import numpy as np
import pandas as pd

class GNSSIMUFusionEngine:
    """
    Module E: Baseline GNSS/IMU Fusion & Handover Blending Engine.
    
    1. During GNSS availability: Fuses GNSS fix and IMU predictions.
    2. During GNSS Outage (Blackout): Seamlessly switches to Dead Reckoning (DR mode).
    3. Upon GNSS Signal Restoration: Applies Sigmoid Temporal Blending (T_blend = 2.0s)
       to smoothly blend DR trajectory back to GNSS position, eliminating visual position snapping.
    4. Map Matching is kept strictly decoupled as a downstream module.
    """
    
    def __init__(self, t_blend_s=2.0, R_earth=6378137.0):
        self.t_blend_s = t_blend_s
        self.R_earth = R_earth
        self.k_sigmoid = 6.0 / t_blend_s # Steepness parameter

    def fuse_trajectory(self, df_processed, dr_df, simulated_outage_start=10.0, simulated_outage_duration=30.0):
        """
        Execute fusion over sequence with simulated blackout and smooth handover.
        """
        outage_end = simulated_outage_start + simulated_outage_duration
        
        fused_records = []
        
        N = len(df_processed)
        for i in range(N):
            t_s = df_processed['relative_time_s'].iloc[i]
            
            dr_lat = dr_df['dr_latitude'].iloc[i]
            dr_lon = dr_df['dr_longitude'].iloc[i]
            
            raw_gnss_lat = df_processed['latitude'].iloc[i]
            raw_gnss_lon = df_processed['longitude'].iloc[i]
            gnss_valid = df_processed['flag_gnss_valid'].iloc[i] == 1 and not np.isnan(raw_gnss_lat)
            
            is_in_outage = simulated_outage_start <= t_s <= outage_end
            
            if is_in_outage or not gnss_valid:
                # Mode 1: Pure Dead Reckoning during Outage / Invalid GNSS
                mode = "DEAD_RECKONING"
                fused_lat = dr_lat
                fused_lon = dr_lon
                blend_weight = 0.0
            elif t_s > outage_end and (t_s - outage_end) <= self.t_blend_s:
                # Mode 2: Sigmoid Handover Blending upon GNSS restoration
                mode = "SIGMOID_HANDOVER"
                t_rel = t_s - outage_end
                # Sigmoid weight from 0.0 to 1.0
                blend_weight = 1.0 / (1.0 + np.exp(-self.k_sigmoid * (t_rel - self.t_blend_s / 2.0)))
                
                fused_lat = (1.0 - blend_weight) * dr_lat + blend_weight * raw_gnss_lat
                fused_lon = (1.0 - blend_weight) * dr_lon + blend_weight * raw_gnss_lon
            else:
                # Mode 3: Normal GNSS Fix
                mode = "GNSS_FIX"
                fused_lat = raw_gnss_lat
                fused_lon = raw_gnss_lon
                blend_weight = 1.0

            fused_records.append({
                'relative_time_s': t_s,
                'fused_latitude': fused_lat,
                'fused_longitude': fused_lon,
                'fusion_mode': mode,
                'handover_blend_weight': round(float(blend_weight), 4),
                'dr_latitude': dr_lat,
                'dr_longitude': dr_lon,
                'gnss_latitude': raw_gnss_lat if gnss_valid else np.nan,
                'gnss_longitude': raw_gnss_lon if gnss_valid else np.nan
            })
            
        return pd.DataFrame(fused_records)
