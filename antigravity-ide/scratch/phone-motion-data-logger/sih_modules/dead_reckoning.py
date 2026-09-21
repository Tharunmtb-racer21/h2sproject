import numpy as np
import pandas as pd

class DeadReckoningIntegrator:
    """
    Module D: Modular 2D Dead Reckoning (DR) Motion Integrator.
    
    Integrates AI predicted speed (v_fwd) and gyroscope yaw rate (gyro_z)
    to update 2D position (North, East) and Heading angle (psi).
    
    Explicit Note on Mechanics:
    Speed alone cannot determine 2D position. Position requires combining 
    scalar speed with estimated orientation (heading) and integrating along 
    the vehicle motion direction under Non-Holonomic Constraints (NHC).
    """
    
    def __init__(self, R_earth=6378137.0):
        self.R_earth = R_earth
        self.reset()

    def reset(self, initial_lat=0.0, initial_lon=0.0, initial_heading_rad=0.0):
        self.origin_lat = initial_lat
        self.origin_lon = initial_lon
        self.heading = initial_heading_rad
        self.pos_north = 0.0
        self.pos_east = 0.0
        self.distance_traveled = 0.0
        self.history = []

    def update(self, speed_m_s, yaw_rate_rad_s, dt=0.01):
        """
        Single-step kinematic integration over interval dt (seconds).
        - speed_m_s: AI estimated forward speed v_fwd (m/s)
        - yaw_rate_rad_s: gyro_z in vehicle frame (rad/s)
        """
        # Non-negative speed enforcement
        speed = max(0.0, float(speed_m_s))
        
        # Heading integration
        self.heading += yaw_rate_rad_s * dt
        # Normalize heading to [-pi, pi]
        self.heading = (self.heading + np.pi) % (2 * np.pi) - np.pi
        
        # 2D Position Integration under NHC (v_lateral = 0)
        dN = speed * np.cos(self.heading) * dt
        dE = speed * np.sin(self.heading) * dt
        
        self.pos_north += dN
        self.pos_east += dE
        self.distance_traveled += speed * dt
        
        # Convert local NE meters to WGS84 Lat/Lon
        dlat = self.pos_north / self.R_earth
        dlon = self.pos_east / (self.R_earth * np.cos(np.radians(self.origin_lat)))
        
        curr_lat = self.origin_lat + np.degrees(dlat)
        curr_lon = self.origin_lon + np.degrees(dlon)
        
        entry = {
            'pos_north_m': self.pos_north,
            'pos_east_m': self.pos_east,
            'heading_rad': self.heading,
            'heading_deg': float(np.degrees(self.heading)),
            'distance_traveled_m': self.distance_traveled,
            'dr_latitude': curr_lat,
            'dr_longitude': curr_lon
        }
        self.history.append(entry)
        return entry

    def integrate_sequence(self, speeds_m_s, yaw_rates_rad_s, dt=0.01, start_lat=11.016845, start_lon=76.955812, start_heading=0.0):
        """
        Batch integrate full sequence.
        """
        self.reset(initial_lat=start_lat, initial_lon=start_lon, initial_heading_rad=start_heading)
        for v, wz in zip(speeds_m_s, yaw_rates_rad_s):
            self.update(v, wz, dt=dt)
        return pd.DataFrame(self.history)

    def compute_drift_metrics(self, dr_df, ref_df, outage_mask=None):
        """
        Calculate positioning error (meters) and cumulative drift rate (%) relative to GNSS reference.
        """
        if 'latitude' not in ref_df.columns or ref_df['latitude'].isnull().all():
            return {'error_mean_m': None, 'error_max_m': None, 'drift_rate_pct': None}
            
        ref_valid = ref_df.dropna(subset=['latitude', 'longitude']).copy()
        if ref_valid.empty:
            return {'error_mean_m': None, 'error_max_m': None, 'drift_rate_pct': None}

        # Calculate planar meter offsets from origin for reference
        lat0 = ref_valid['latitude'].iloc[0]
        lon0 = ref_valid['longitude'].iloc[0]
        
        ref_n = np.radians(ref_valid['latitude'] - lat0) * self.R_earth
        ref_e = np.radians(ref_valid['longitude'] - lon0) * self.R_earth * np.cos(np.radians(lat0))
        
        dr_n = dr_df['pos_north_m'].iloc[:len(ref_n)].values
        dr_e = dr_df['pos_east_m'].iloc[:len(ref_e)].values
        
        errors = np.sqrt((dr_n - ref_n.values)**2 + (dr_e - ref_e.values)**2)
        
        if outage_mask is not None and np.sum(outage_mask) > 0:
            outage_errs = errors[outage_mask[:len(errors)]]
            dist_outage = dr_df['distance_traveled_m'].iloc[np.where(outage_mask)[0][-1]] - dr_df['distance_traveled_m'].iloc[np.where(outage_mask)[0][0]]
            final_err = outage_errs[-1] if len(outage_errs) > 0 else errors[-1]
            drift_pct = (final_err / dist_outage * 100.0) if dist_outage > 0 else 0.0
        else:
            final_err = errors[-1]
            dist_total = dr_df['distance_traveled_m'].iloc[-1]
            drift_pct = (final_err / dist_total * 100.0) if dist_total > 0 else 0.0

        return {
            'error_mean_m': round(float(np.mean(errors)), 3),
            'error_rmse_m': round(float(np.sqrt(np.mean(errors**2))), 3),
            'error_max_m': round(float(np.max(errors)), 3),
            'drift_rate_pct': round(float(drift_pct), 3)
        }
