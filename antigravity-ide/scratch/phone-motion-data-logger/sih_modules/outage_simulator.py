import numpy as np
import pandas as pd

class GNSSOutageSimulator:
    """
    Module C: GNSS Outage Simulation Engine.
    
    Artificially masks GNSS measurements over configurable time windows,
    simulating tunnels, underground parking garages, flyovers, and urban canyons.
    
    Ensures that ONLY realistic dead-reckoning inputs (IMU, AI speed, Cell ID)
    are available to the navigation engine during outage periods.
    """
    
    def __init__(self, start_time_s=10.0, duration_s=30.0):
        self.start_time_s = start_time_s
        self.duration_s = duration_s
        self.end_time_s = start_time_s + duration_s

    def apply_outage_mask(self, df):
        """
        Apply artificial blackout mask to dataframe based on relative_time_s.
        Sets GNSS features to NaN and flag_gnss_valid to 0 during outage interval.
        """
        masked_df = df.copy()
        
        # Outage condition
        is_outage = (masked_df['relative_time_s'] >= self.start_time_s) & (masked_df['relative_time_s'] <= self.end_time_s)
        
        # Mask GNSS columns
        gnss_cols = ['latitude', 'longitude', 'altitude', 'gnss_speed_m_s', 'gnss_speed_km_h', 'gnss_accuracy', 'gnss_bearing']
        for col in gnss_cols:
            if col in masked_df.columns:
                masked_df.loc[is_outage, col] = np.nan
                
        # Set flags
        masked_df.loc[is_outage, 'flag_gnss_valid'] = 0
        masked_df.loc[is_outage, 'flag_speed_ref_valid'] = 0
        masked_df['flag_simulated_outage'] = is_outage.astype(int)
        
        return masked_df

    def get_outage_bounds(self, df):
        """
        Return start index, end index, and duration of the simulated outage.
        """
        is_outage = (df['relative_time_s'] >= self.start_time_s) & (df['relative_time_s'] <= self.end_time_s)
        outage_indices = df.index[is_outage].tolist()
        
        if not outage_indices:
            return 0, 0, 0.0
            
        idx_start = outage_indices[0]
        idx_end = outage_indices[-1]
        actual_duration = df['relative_time_s'].iloc[idx_end] - df['relative_time_s'].iloc[idx_start]
        return idx_start, idx_end, actual_duration
