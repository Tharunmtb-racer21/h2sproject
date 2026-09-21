import numpy as np
import pandas as pd

class DisturbanceDetector:
    """
    Module B: Signal Processing Disturbance & Road Anomaly Detector.
    
    Detects road bumps, speed breakers, sudden hard braking, sharp acceleration,
    turning maneuvers, and engine/chassis structural vibrations.
    
    Outputs a disturbance flag (0/1) and confidence score (0.0 - 1.0).
    """
    
    def __init__(self, g_ref=9.81):
        self.g_ref = g_ref

    def analyze_frame(self, accel_v, gyro_v, window_acc_z=None):
        """
        Analyze single 100 Hz frame in vehicle frame (accel_v, gyro_v).
        accel_v: [ax, ay, az] in m/s^2
        gyro_v: [wx, wy, wz] in rad/s
        window_acc_z: optional history vector of az for rolling variance calculation.
        """
        ax, ay, az = accel_v
        wx, wy, wz = gyro_v
        
        # Thresholds
        vertical_dev = abs(az - self.g_ref)
        is_bump = vertical_dev > 3.0
        is_braking = ax < -2.5
        is_accel = ax > 1.8
        is_turning = abs(wz) > 0.35
        
        vib_var = float(np.var(window_acc_z)) if window_acc_z is not None and len(window_acc_z) > 10 else 0.0
        is_vibration = vib_var > 2.0
        
        # Combine into overall disturbance flag
        is_disturbance = is_bump or is_vibration or is_braking or is_turning
        
        # Calculate confidence score (0.0 to 1.0)
        conf_bump = min(vertical_dev / 8.0, 1.0)
        conf_brake = min(abs(ax) / 5.0, 1.0) if is_braking else 0.0
        conf_turn = min(abs(wz) / 1.5, 1.0) if is_turning else 0.0
        conf_vib = min(vib_var / 5.0, 1.0) if is_vibration else 0.0
        
        confidence = float(max(conf_bump, conf_brake, conf_turn, conf_vib))
        
        return {
            'is_disturbance': bool(is_disturbance),
            'confidence': round(confidence, 3),
            'is_bump': bool(is_bump),
            'is_braking': bool(is_braking),
            'is_acceleration': bool(is_accel),
            'is_turning': bool(is_turning),
            'is_vibration': bool(is_vibration),
            'vertical_dev_m_s2': round(float(vertical_dev), 3),
            'vibration_variance': round(vib_var, 3)
        }

    def process_sequence(self, df):
        """
        Process dataframe sequence and append disturbance flags.
        """
        results = []
        acc_z_vals = df['accel_z'].values
        
        for i in range(len(df)):
            ax = df['accel_x'].iloc[i]
            ay = df['accel_y'].iloc[i]
            az = df['accel_z'].iloc[i]
            wx = df['gyro_x'].iloc[i]
            wy = df['gyro_y'].iloc[i]
            wz = df['gyro_z'].iloc[i]
            
            w_start = max(0, i - 50)
            window_z = acc_z_vals[w_start : i + 1]
            
            res = self.analyze_frame([ax, ay, az], [wx, wy, wz], window_acc_z=window_z)
            results.append(res)
            
        res_df = pd.DataFrame(results)
        return pd.concat([df.reset_index(drop=True), res_df], axis=1)
