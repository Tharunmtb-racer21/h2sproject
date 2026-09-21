"""
paper_baseline/feature_extraction.py
SIH26168 - Paper-Aligned Feature Extraction Module (Shin et al., 2025)

Implements:
1. 50 Hz linear resampling of smartphone IMU and vehicle speed reference signals.
2. 21-dimensional input feature matrix computation:
   - 7 raw features: accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, accel_mag
   - 14 statistical features: backward-looking rolling mean and rolling variance over T=200 window.
3. Anti-leakage MinMax Scaler fitted strictly on training data.
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional


FEATURE_COLUMNS = [
    'accel_x', 'accel_y', 'accel_z',
    'gyro_x', 'gyro_y', 'gyro_z',
    'accel_mag',
    'accel_x_mean', 'accel_y_mean', 'accel_z_mean',
    'gyro_x_mean', 'gyro_y_mean', 'gyro_z_mean',
    'accel_mag_mean',
    'accel_x_var', 'accel_y_var', 'accel_z_var',
    'gyro_x_var', 'gyro_y_var', 'gyro_z_var',
    'accel_mag_var'
]

RAW_SENSOR_COLS = ['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z']


def synchronize_s_and_v_streams(
    df_s: pd.DataFrame, 
    df_v: pd.DataFrame, 
    max_tolerance_sec: float = 0.05
) -> pd.DataFrame:
    """
    Synchronizes smartphone IMU stream (S) with vehicle CAN/VBOX stream (V) using nearest-neighbor merge_asof.
    
    Safeguards:
    1. Converts timestamps to relative seconds starting from t=0.0.
    2. Applies strict tolerance (default 50 ms = 0.05 s).
    3. Rejects records where time difference exceeds max_tolerance_sec.
    """
    df_s = df_s.copy()
    df_v = df_v.copy()
    
    s_ts_col = [c for c in df_s.columns if 'time' in c.lower() or 'ms' in c.lower()][0]
    v_ts_col = [c for c in df_v.columns if 'time' in c.lower() or 'sec' in c.lower()][0]
    
    s_raw = df_s[s_ts_col].values.astype(float)
    v_raw = df_v[v_ts_col].values.astype(float)
    
    s_scale = 1000.0 if ('ms' in s_ts_col.lower() or s_raw.max() > 1e5) else 1.0
    v_scale = 1000.0 if ('ms' in v_ts_col.lower() or v_raw.max() > 1e5) else 1.0

    
    s_t_sec = s_raw / s_scale
    v_t_sec = v_raw / v_scale
    
    s_t0 = s_t_sec[0]
    v_t0 = v_t_sec[0]
    
    # If both streams are in the same absolute reference frame (difference < 1 hour)
    if abs(s_t0 - v_t0) < 3600.0:
        common_t0 = min(s_t0, v_t0)
        df_s['rel_time_s'] = s_t_sec - common_t0
        df_v['rel_time_s'] = v_t_sec - common_t0
    else:
        df_s['rel_time_s'] = s_t_sec - s_t0
        df_v['rel_time_s'] = v_t_sec - v_t0



    
    df_s_sorted = df_s.sort_values(by='rel_time_s')
    df_v_sorted = df_v.sort_values(by='rel_time_s')
    
    merged = pd.merge_asof(
        df_s_sorted,
        df_v_sorted,
        on='rel_time_s',
        direction='nearest',
        tolerance=max_tolerance_sec,
        suffixes=('_s', '_v')
    )
    
    # Identify target column in V dataframe
    v_target_col = [c for c in merged.columns if 'velocity' in c.lower() or 'reference_speed' in c.lower()][0]
    
    # Reject records exceeding tolerance
    valid_mask = ~merged[v_target_col].isna()
    synced_df = merged[valid_mask].copy()
    synced_df = synced_df.rename(columns={'rel_time_s': 'relative_time_s'})
    
    return synced_df



def resample_to_50hz(df: pd.DataFrame, target_freq_hz: float = 50.0) -> pd.DataFrame:
    """
    Resamples dataframe to a uniform target frequency grid (default 50 Hz = 20ms step).
    Uses linear interpolation for sensor readings and target speed.
    """
    if 'relative_time_s' not in df.columns:
        if 'timestamp' in df.columns:
            # Normalize timestamp to seconds relative to start
            t0 = df['timestamp'].iloc[0]
            # Handle timestamps in ms vs seconds
            if df['timestamp'].max() > 1e6:
                df['relative_time_s'] = (df['timestamp'] - t0) / 1000.0
            else:
                df['relative_time_s'] = df['timestamp'] - t0
        else:
            raise ValueError("Dataframe must contain 'relative_time_s' or 'timestamp' column.")

    dt = 1.0 / target_freq_hz
    t_start = df['relative_time_s'].min()
    t_end = df['relative_time_s'].max()
    grid_time = np.arange(t_start, t_end, dt)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if 'relative_time_s' in numeric_cols:
        numeric_cols.remove('relative_time_s')

    resampled_data = {'relative_time_s': grid_time}
    for col in numeric_cols:
        resampled_data[col] = np.interp(grid_time, df['relative_time_s'].values, df[col].values)

    resampled_df = pd.DataFrame(resampled_data)
    return resampled_df


def extract_paper_features(df: pd.DataFrame, window_size: int = 200) -> pd.DataFrame:
    """
    Extracts 21 paper-aligned features:
    - 7 raw features (accel x,y,z, gyro x,y,z, accel_mag)
    - 14 rolling statistics (rolling mean & rolling sample variance over backward-looking window)

    Crucial leakage prevention:
    rolling window is strictly backward-looking (rolling(window=window_size, min_periods=1)).
    """
    df = df.copy()

    # Ensure acceleration magnitude exists
    if 'accel_mag' not in df.columns:
        df['accel_mag'] = np.sqrt(df['accel_x']**2 + df['accel_y']**2 + df['accel_z']**2)

    base_7 = ['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'accel_mag']

    # Compute backward-looking rolling mean and variance
    for col in base_7:
        roll = df[col].rolling(window=window_size, min_periods=1)
        df[f'{col}_mean'] = roll.mean()
        # pandas rolling var requires min_periods >= 2 for ddof=1, fill NaN at t=0 with 0.0
        df[f'{col}_var'] = roll.var(ddof=1).fillna(0.0)

    # Return only the 21 target features plus reference speed if present
    out_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    if 'reference_speed' in df.columns:
        out_cols.append('reference_speed')

    return df[out_cols]


class PaperMinMaxScaler:
    """
    Min-Max Feature Scaler that strictly fits ONLY on training data
    and transforms validation / test data without data leakage.
    """
    def __init__(self, feature_range: Tuple[float, float] = (0.0, 1.0)):
        self.feature_range = feature_range
        self.min_val: Optional[np.ndarray] = None
        self.max_val: Optional[np.ndarray] = None
        self.is_fitted: bool = False

    def fit(self, X: np.ndarray) -> 'PaperMinMaxScaler':
        """
        Fit scaler on training array X of shape (N, num_features) or (N, T, num_features).
        """
        if X.ndim == 3:
            # Flatten N, T dimensions for fitting
            X_flat = X.reshape(-1, X.shape[-1])
        else:
            X_flat = X

        self.min_val = np.min(X_flat, axis=0)
        self.max_val = np.max(X_flat, axis=0)

        # Handle zero-variance features to prevent division by zero
        range_val = self.max_val - self.min_val
        range_val[range_val == 0.0] = 1.0

        self.is_fitted = True
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Transform array X using fitted min and max bounds.
        """
        if not self.is_fitted or self.min_val is None or self.max_val is None:
            raise RuntimeError("PaperMinMaxScaler must be fitted on training data before transforming.")

        range_val = self.max_val - self.min_val
        range_val[range_val == 0.0] = 1.0

        low, high = self.feature_range
        X_scaled = low + (X - self.min_val) / range_val * (high - low)
        return X_scaled

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)
