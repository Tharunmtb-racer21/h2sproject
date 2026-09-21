import numpy as np

class PhoneToVehicleAligner:
    """
    Module A: Phone-to-Vehicle Frame Alignment & Mounting Shift Detector.
    
    Transforms IMU sensor readings from arbitrary phone body frame (b)
    to standard vehicle body frame (v):
      +X_v : Forward (Longitudinal)
      +Y_v : Right (Lateral)
      +Z_v : Down (Vertical)
    
    Assumptions & Limitations:
    1. Phone is rigidly mounted in a holder attached to dashboard/windshield during driving.
    2. Static gravity vector isolates Pitch & Roll.
    3. Forward vehicle acceleration isolates Yaw offset angle (dynamic PCA).
    4. Rapid hand-held phone movement during driving violates rigid mount assumption.
    """
    
    def __init__(self, g_ref=9.81):
        self.g_ref = g_ref
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
        self.R_b_v = np.eye(3)
        self.calibrated_gravity = None

    def calibrate_static_pitch_roll(self, accel_static_mean):
        """
        Estimate pitch (theta) and roll (phi) from static gravity vector.
        accel_static_mean: array-like (3,) in m/s^2.
        """
        ax, ay, az = accel_static_mean
        g_norm = np.linalg.norm(accel_static_mean)
        if g_norm == 0:
            g_norm = self.g_ref
            
        ax_n = np.clip(ax / g_norm, -1.0, 1.0)
        
        # Pitch theta and Roll phi
        self.pitch = float(np.arcsin(-ax_n))
        self.roll = float(np.arctan2(ay, az))
        self.calibrated_gravity = np.array(accel_static_mean) / g_norm
        self._update_rotation_matrix()
        return self.pitch, self.roll

    def calibrate_dynamic_yaw(self, accel_horiz_samples, gnss_heading_rad):
        """
        Estimate yaw offset (psi) during forward vehicle acceleration using PCA.
        accel_horiz_samples: (N, 2) horizontal accelerations [ax, ay].
        """
        if len(accel_horiz_samples) < 10:
            return self.yaw
            
        cov = np.cov(accel_horiz_samples, rowvar=False)
        eigvals, eigvecs = np.linalg.eigh(cov)
        principal_axis = eigvecs[:, np.argmax(eigvals)]
        
        pca_angle = float(np.arctan2(principal_axis[1], principal_axis[0]))
        self.yaw = float(gnss_heading_rad - pca_angle)
        self._update_rotation_matrix()
        return self.yaw

    def _update_rotation_matrix(self):
        """
        Compute standard 3D rotation matrix R_b_v = R_z(yaw) * R_y(pitch) * R_x(roll).
        """
        cp, sp = np.cos(self.pitch), np.sin(self.pitch)
        cr, sr = np.cos(self.roll), np.sin(self.roll)
        cy, sy = np.cos(self.yaw), np.sin(self.yaw)
        
        Rx = np.array([
            [1, 0, 0],
            [0, cr, -sr],
            [0, sr, cr]
        ])
        
        Ry = np.array([
            [cp, 0, sp],
            [0, 1, 0],
            [-sp, 0, cp]
        ])
        
        Rz = np.array([
            [cy, -sy, 0],
            [sy, cy, 0],
            [0, 0, 1]
        ])
        
        self.R_b_v = Rz @ Ry @ Rx

    def transform_to_vehicle_frame(self, accel_b, gyro_b):
        """
        Transform 3-axis accelerometer and gyroscope vectors from body to vehicle frame.
        """
        accel_v = self.R_b_v @ np.array(accel_b)
        gyro_v = self.R_b_v @ np.array(gyro_b)
        return accel_v, gyro_v

    def detect_mounting_shift(self, current_gravity_vec, threshold_deg=12.0):
        """
        Detect if phone mount orientation shifted during driving by comparing gravity vector change.
        Returns: (bool is_shifted, float angular_change_deg)
        """
        if self.calibrated_gravity is None:
            return False, 0.0
            
        g_curr_norm = np.linalg.norm(current_gravity_vec)
        if g_curr_norm == 0:
            return False, 0.0
            
        g_curr = np.array(current_gravity_vec) / g_curr_norm
        dot_prod = np.clip(np.dot(self.calibrated_gravity, g_curr), -1.0, 1.0)
        angle_rad = np.arccos(dot_prod)
        angle_deg = float(np.degrees(angle_rad))
        
        is_shifted = angle_deg > threshold_deg
        return is_shifted, angle_deg
