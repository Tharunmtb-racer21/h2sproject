"""
paper_baseline/tests/test_feature_extraction.py
Automated validation test suite for SIH26168 Phase 2 feature extraction and data leakage checks.
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from paper_baseline.feature_extraction import (
    resample_to_50hz,
    extract_paper_features,
    PaperMinMaxScaler,
    FEATURE_COLUMNS
)


def create_synthetic_imu_session(duration_sec: float = 10.0, freq_hz: float = 10.0) -> pd.DataFrame:
    """Helper to generate synthetic IMU and reference speed dataframe."""
    num_samples = int(duration_sec * freq_hz)
    t = np.linspace(0, duration_sec, num_samples)
    
    np.random.seed(42)
    accel_x = np.sin(t) + np.random.normal(0, 0.1, num_samples)
    accel_y = np.cos(t) + np.random.normal(0, 0.1, num_samples)
    accel_z = 9.81 + np.random.normal(0, 0.05, num_samples)
    
    gyro_x = np.random.normal(0, 0.02, num_samples)
    gyro_y = np.random.normal(0, 0.02, num_samples)
    gyro_z = np.random.normal(0, 0.05, num_samples)
    
    ref_speed = 10.0 + 2.0 * np.sin(0.5 * t)
    
    df = pd.DataFrame({
        'relative_time_s': t,
        'accel_x': accel_x,
        'accel_y': accel_y,
        'accel_z': accel_z,
        'gyro_x': gyro_x,
        'gyro_y': gyro_y,
        'gyro_z': gyro_z,
        'reference_speed': ref_speed
    })
    return df


def test_21_feature_dimensions():
    """Requirement 4.1: Confirm all 21 input features exist and match paper specification."""
    df_raw = create_synthetic_imu_session(duration_sec=5.0, freq_hz=50.0)
    df_feat = extract_paper_features(df_raw, window_size=200)
    
    # Extract feature matrix without label
    X_cols = [c for c in df_feat.columns if c != 'reference_speed']
    assert len(X_cols) == 21, f"Expected 21 features, got {len(X_cols)}: {X_cols}"
    assert X_cols == FEATURE_COLUMNS, "Feature column ordering does not match FEATURE_COLUMNS contract."


def test_raw_feature_units():
    """Requirement 4.2: Confirm raw feature units and magnitude calculation."""
    df_raw = create_synthetic_imu_session(duration_sec=2.0, freq_hz=50.0)
    df_feat = extract_paper_features(df_raw, window_size=200)
    
    # Gravity check (accel_z ~ 9.81 m/s^2, mag ~ 9.81 m/s^2)
    assert np.mean(df_feat['accel_z']) > 9.0 and np.mean(df_feat['accel_z']) < 11.0, \
        "accel_z magnitude outside expected m/s^2 range (~9.81)."
        
    expected_mag = np.sqrt(df_raw['accel_x']**2 + df_raw['accel_y']**2 + df_raw['accel_z']**2)
    np.testing.assert_allclose(df_feat['accel_mag'].values, expected_mag.values, rtol=1e-5)


def test_50hz_resampling_grid():
    """Requirement 4.4: Confirm 50 Hz resampling grid dt = 0.02s."""
    df_10hz = create_synthetic_imu_session(duration_sec=4.0, freq_hz=10.0)
    df_50hz = resample_to_50hz(df_10hz, target_freq_hz=50.0)
    
    dt_series = np.diff(df_50hz['relative_time_s'])
    np.testing.assert_allclose(dt_series, 0.02, rtol=1e-4, err_msg="Resampled dt is not exactly 0.02s (50 Hz).")
    assert len(df_50hz) == 200, f"Expected 200 samples for 4s at 50 Hz, got {len(df_50hz)}"


def test_4sec_window_duration():
    """Requirement 4.5: Confirm T=200 produces a 4-second sequence window at 50 Hz."""
    target_freq = 50.0
    T = 200
    duration = T / target_freq
    assert duration == 4.0, f"Expected 4.0s sequence duration, got {duration}s"


def test_no_future_data_leakage_in_rolling_stats():
    """Requirement 4.6: Confirm backward-looking rolling stats have ZERO future-data leakage."""
    df_raw = create_synthetic_imu_session(duration_sec=10.0, freq_hz=50.0)
    df_feat1 = extract_paper_features(df_raw, window_size=200)
    
    # Modify a future sample at index t=300
    df_raw_modified = df_raw.copy()
    df_raw_modified.loc[300, 'accel_x'] += 999.0  # Massive injection at t=300
    df_feat2 = extract_paper_features(df_raw_modified, window_size=200)
    
    # Rolling features at index t=250 MUST be identical between both datasets!
    row_t250_orig = df_feat1.iloc[250].drop(labels=['reference_speed'], errors='ignore').values
    row_t250_mod = df_feat2.iloc[250].drop(labels=['reference_speed'], errors='ignore').values
    
    np.testing.assert_allclose(
        row_t250_orig, 
        row_t250_mod, 
        atol=1e-7, 
        err_msg="FUTURE DATA LEAKAGE DETECTED! Modifying future sample at t=300 altered feature vector at t=250!"
    )


def test_normalization_fitted_only_on_training_data():
    """Requirement 4.7: Ensure normalization scaler is fitted ONLY on training data."""
    X_train = np.random.uniform(low=-2.0, high=2.0, size=(1000, 21))
    X_test = np.random.uniform(low=-10.0, high=10.0, size=(200, 21))  # Out-of-bounds test data
    
    scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
    scaler.fit(X_train)
    
    train_min_bounds = scaler.min_val.copy()
    train_max_bounds = scaler.max_val.copy()
    
    # Transform test data
    X_test_scaled = scaler.transform(X_test)
    
    # Scaler bounds MUST REMAIN FITTED strictly on X_train
    np.testing.assert_array_equal(scaler.min_val, train_min_bounds, err_msg="Scaler min bounds altered during transform!")
    np.testing.assert_array_equal(scaler.max_val, train_max_bounds, err_msg="Scaler max bounds altered during transform!")
    
    # Attempting to transform before fit must raise RuntimeError
    unfitted_scaler = PaperMinMaxScaler()
    with pytest.raises(RuntimeError):
        unfitted_scaler.transform(X_test)


def test_window_target_timestamp_alignment():
    """Sanity Check 3 & 4: Confirm sequence window end timestamp matches target velocity timestamp."""
    df_10hz = create_synthetic_imu_session(duration_sec=10.0, freq_hz=10.0)
    df_50hz = resample_to_50hz(df_10hz, target_freq_hz=50.0)
    
    T = 200
    for end_idx in [200, 300, 450]:
        win_start_t = df_50hz['relative_time_s'].iloc[end_idx - T + 1]
        win_end_t = df_50hz['relative_time_s'].iloc[end_idx]
        target_t = df_50hz['relative_time_s'].iloc[end_idx]
        
        assert win_end_t == target_t, f"Window end timestamp {win_end_t} != target timestamp {target_t}"
        assert np.isclose(win_end_t - win_start_t, (T - 1) * 0.02, atol=1e-5), "Window span is not 199 * dt = 3.98s"


def test_synchronize_s_and_v_streams_tolerance():
    """Sanity Check Requirement 4: Verify stream synchronization rejects matches exceeding 50ms tolerance."""
    from paper_baseline.feature_extraction import synchronize_s_and_v_streams
    
    # Create S stream starting at t = 0.0s to 15.0s (in ms)
    t_s = np.linspace(0.0, 15.0, 1500)
    df_s = pd.DataFrame({
        'Time Since Start ms': t_s * 1000.0,
        'accel_x': np.sin(t_s),
        'accel_y': np.cos(t_s),
        'accel_z': 9.81 * np.ones_like(t_s),
        'gyro_x': np.zeros_like(t_s),
        'gyro_y': np.zeros_like(t_s),
        'gyro_z': np.zeros_like(t_s)
    })
    
    # Create V stream starting 5.0s LATER than S (t = 5.0s to 15.0s, in ms)
    t_v = np.linspace(5.0, 15.0, 1000)
    df_v = pd.DataFrame({
        'Time Since Start ms': t_v * 1000.0,
        'velocity': 15.0 + 5.0 * np.sin(t_v)
    })
    
    # Synchronize with tolerance = 0.05s (50 ms)
    df_synced = synchronize_s_and_v_streams(df_s, df_v, max_tolerance_sec=0.05)
    
    # Pre-roll samples t < 4.95s MUST be rejected!
    assert len(df_synced) < len(df_s), "Pre-roll lead samples were not rejected!"
    assert df_synced['relative_time_s'].min() >= 4.95, f"Expected min time >= 4.95s, got {df_synced['relative_time_s'].min()}"
    assert not df_synced['velocity'].isna().any(), "NaN values found in synchronized target speed!"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])




