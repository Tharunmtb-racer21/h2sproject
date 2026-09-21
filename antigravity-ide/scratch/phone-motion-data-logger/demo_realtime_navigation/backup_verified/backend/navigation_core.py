"""
SIH26168 Intelligent Dead Reckoning System
Module: Navigation Core Engine (2D Kinematic Dead Reckoning)

Handles:
- Local East-North-Up (ENU) coordinate tracking in metres
- Gyroscope heading angle integration
- Non-Holonomic Constraints (lateral velocity = 0)
- Physical Non-Negative velocity clamping: v = max(0, v)
- Zero-Velocity Updates (ZUPT) for standstill drift prevention
"""

import numpy as np


class NavigationCore:
    def __init__(self, earth_radius=6378137.0):
        self.R_earth = earth_radius
        self.reset()

    def reset(self, origin_lat=52.37938, origin_lon=-1.261814, origin_heading_deg=0.0):
        """Reset the dead reckoning state to origin coordinates."""
        self.origin_lat = float(origin_lat)
        self.origin_lon = float(origin_lon)
        self.heading_rad = float(np.radians(origin_heading_deg))
        
        # Local tangent plane positions (metres)
        self.pos_east_m = 0.0
        self.pos_north_m = 0.0
        self.total_distance_m = 0.0
        
        # Velocity and standstill state
        self.current_speed_mps = 0.0
        self.is_standstill = False
        
        # Trajectory trace buffers
        self.trajectory_history = []

    def update_heading(self, gyro_z_rad_s, dt=0.1):
        """Integrate angular yaw velocity to advance heading angle."""
        self.heading_rad += gyro_z_rad_s * dt
        # Wrap heading to [-pi, pi]
        self.heading_rad = (self.heading_rad + np.pi) % (2.0 * np.pi) - np.pi
        return np.degrees(self.heading_rad)

    def set_heading_deg(self, heading_deg):
        """Explicitly set or align heading angle in degrees."""
        self.heading_rad = float(np.radians(heading_deg))
        self.heading_rad = (self.heading_rad + np.pi) % (2.0 * np.pi) - np.pi

    def propagate_step(self, speed_mps, heading_deg=None, dt=0.1, accel_var=None):
        """
        Advance vehicle position by one kinematic time-step (dt seconds).
        
        Args:
            speed_mps: AI-estimated or sensor-derived forward velocity in m/s.
            heading_deg: Optional current heading in degrees (if directly available).
            dt: Delta time in seconds (default 0.1s for 10Hz).
            accel_var: Optional IMU acceleration variance for ZUPT standstill check.
        """
        if heading_deg is not None:
            self.set_heading_deg(heading_deg)

        # 1. Non-Negative Clamping
        v_forward = max(0.0, float(speed_mps))

        # 2. Zero-Velocity Update (ZUPT)
        if accel_var is not None and accel_var < 0.02 and v_forward < 0.3:
            self.is_standstill = True
            v_forward = 0.0
        elif v_forward < 0.1:
            self.is_standstill = True
            v_forward = 0.0
        else:
            self.is_standstill = False

        self.current_speed_mps = v_forward

        # 3. Kinematic 2D Displacement under Non-Holonomic Constraints
        # Heading 0 deg = North (Y), 90 deg = East (X)
        # dNorth = v * cos(psi) * dt, dEast = v * sin(psi) * dt
        d_north = v_forward * np.cos(self.heading_rad) * dt
        d_east = v_forward * np.sin(self.heading_rad) * dt

        self.pos_north_m += d_north
        self.pos_east_m += d_east
        self.total_distance_m += v_forward * dt

        # 4. Convert local ENU to WGS84 Lat/Lon
        d_lat_rad = self.pos_north_m / self.R_earth
        d_lon_rad = self.pos_east_m / (self.R_earth * np.cos(np.radians(self.origin_lat)))

        curr_lat = self.origin_lat + np.degrees(d_lat_rad)
        curr_lon = self.origin_lon + np.degrees(d_lon_rad)

        state = {
            "pos_east_m": round(self.pos_east_m, 3),
            "pos_north_m": round(self.pos_north_m, 3),
            "speed_mps": round(self.current_speed_mps, 3),
            "speed_kmh": round(self.current_speed_mps * 3.6, 2),
            "heading_deg": round(float(np.degrees(self.heading_rad)) % 360.0, 2),
            "total_distance_m": round(self.total_distance_m, 2),
            "latitude": round(curr_lat, 7),
            "longitude": round(curr_lon, 7),
            "is_standstill": self.is_standstill,
        }
        
        self.trajectory_history.append(state)
        return state

    def set_position_enu(self, east_m, north_m):
        """Anchor or reset position in local ENU frame."""
        self.pos_east_m = float(east_m)
        self.pos_north_m = float(north_m)
