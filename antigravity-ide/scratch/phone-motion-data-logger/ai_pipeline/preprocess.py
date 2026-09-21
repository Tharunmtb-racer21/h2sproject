import os
import glob
import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

def apply_butterworth_filter(data, cutoff=15.0, fs=100.0, order=4):
    """
    Apply a 4th-order Butterworth low-pass filter to sensor series.
    """
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    data_clean = pd.Series(data).interpolate(method='linear').bfill().ffill().values
    if len(data_clean) <= 12:
        return data_clean
    filtered = filtfilt(b, a, data_clean)
    return filtered

def preprocess_interleaved_log(filepath, target_fs=100.0):
    """
    Preprocess multi-stream interleaved Android sensor log.
    Extract SENSOR, GNSS, and CELLULAR streams and align onto a uniform target_fs (100 Hz) time grid.
    """
    df = pd.read_csv(filepath, low_memory=False)
    filename = os.path.basename(filepath)
    
    # 1. Extract streams
    sensor_df = df[df['stream_type'] == 'SENSOR'].copy()
    gnss_df = df[df['stream_type'] == 'GNSS'].copy()
    cell_df = df[df['stream_type'] == 'CELLULAR'].copy()
    
    if sensor_df.empty:
        print(f"Warning: {filename} has no SENSOR stream.")
        return None

    # Coerce numerics
    for col in ['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'mag_x', 'mag_y', 'mag_z', 'timestamp_ms']:
        if col in sensor_df.columns:
            sensor_df[col] = pd.to_numeric(sensor_df[col], errors='coerce')

    # Ensure float64 timestamps
    sensor_df = sensor_df.dropna(subset=['timestamp_ms']).copy()
    sensor_df['timestamp_ms'] = sensor_df['timestamp_ms'].astype(np.float64)
    sensor_df = sensor_df.sort_values('timestamp_ms').drop_duplicates(subset=['timestamp_ms'], keep='first')
    
    t_start = float(sensor_df['timestamp_ms'].iloc[0])
    t_end = float(sensor_df['timestamp_ms'].iloc[-1])
    
    if t_end <= t_start:
        print(f"Error: Invalid duration for {filename}")
        return None

    # 2. Create uniform 100 Hz time grid
    dt_ms = 1000.0 / target_fs
    grid_timestamps = np.arange(t_start, t_end + dt_ms, dt_ms, dtype=np.float64)
    
    proc_df = pd.DataFrame({'timestamp_ms': grid_timestamps})
    proc_df['relative_time_s'] = (proc_df['timestamp_ms'] - t_start) / 1000.0
    
    # Merge and interpolate IMU signals
    sensor_merged = pd.merge_asof(proc_df, sensor_df, on='timestamp_ms', direction='nearest')
    
    for col in ['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'mag_x', 'mag_y', 'mag_z']:
        if col in sensor_merged.columns:
            proc_df[col] = pd.Series(sensor_merged[col]).interpolate(method='linear').bfill().ffill()
        else:
            proc_df[col] = 0.0

    # Calculate Accelerometer magnitude
    proc_df['accel_mag'] = np.sqrt(proc_df['accel_x']**2 + proc_df['accel_y']**2 + proc_df['accel_z']**2)
    proc_df['gyro_mag'] = np.sqrt(proc_df['gyro_x']**2 + proc_df['gyro_y']**2 + proc_df['gyro_z']**2)
    
    # Butterworth low-pass filtering
    proc_df['accel_x_filt'] = apply_butterworth_filter(proc_df['accel_x'], cutoff=15.0, fs=target_fs)
    proc_df['accel_y_filt'] = apply_butterworth_filter(proc_df['accel_y'], cutoff=15.0, fs=target_fs)
    proc_df['accel_z_filt'] = apply_butterworth_filter(proc_df['accel_z'], cutoff=15.0, fs=target_fs)

    # 3. Synchronize GNSS stream (Forward Fill)
    if not gnss_df.empty and 'timestamp_ms' in gnss_df.columns:
        for col in ['latitude', 'longitude', 'altitude', 'accuracy', 'speed', 'bearing', 'timestamp_ms']:
            if col in gnss_df.columns:
                gnss_df[col] = pd.to_numeric(gnss_df[col], errors='coerce')
        gnss_sorted = gnss_df.dropna(subset=['timestamp_ms']).copy()
        gnss_sorted['timestamp_ms'] = gnss_sorted['timestamp_ms'].astype(np.float64)
        gnss_sorted = gnss_sorted.sort_values('timestamp_ms')
        
        gnss_merged = pd.merge_asof(proc_df[['timestamp_ms']], gnss_sorted, on='timestamp_ms', direction='backward')
        
        proc_df['latitude'] = gnss_merged['latitude'] if 'latitude' in gnss_merged else np.nan
        proc_df['longitude'] = gnss_merged['longitude'] if 'longitude' in gnss_merged else np.nan
        proc_df['altitude'] = gnss_merged['altitude'] if 'altitude' in gnss_merged else np.nan
        proc_df['gnss_speed_m_s'] = gnss_merged['speed'] if 'speed' in gnss_merged else np.nan
        proc_df['gnss_accuracy'] = gnss_merged['accuracy'] if 'accuracy' in gnss_merged else np.nan
        proc_df['gnss_bearing'] = gnss_merged['bearing'] if 'bearing' in gnss_merged else np.nan
    else:
        proc_df['latitude'] = np.nan
        proc_df['longitude'] = np.nan
        proc_df['altitude'] = np.nan
        proc_df['gnss_speed_m_s'] = np.nan
        proc_df['gnss_accuracy'] = np.nan
        proc_df['gnss_bearing'] = np.nan

    proc_df['gnss_speed_km_h'] = proc_df['gnss_speed_m_s'] * 3.6

    # 4. Synchronize CELLULAR stream (Forward Fill)
    if not cell_df.empty and 'timestamp_ms' in cell_df.columns:
        for col in ['cell_id', 'signal_dbm', 'signal_level', 'timestamp_ms']:
            if col in cell_df.columns:
                cell_df[col] = pd.to_numeric(cell_df[col], errors='coerce')
        cell_sorted = cell_df.dropna(subset=['timestamp_ms']).copy()
        cell_sorted['timestamp_ms'] = cell_sorted['timestamp_ms'].astype(np.float64)
        cell_sorted = cell_sorted.sort_values('timestamp_ms')
        
        cell_merged = pd.merge_asof(proc_df[['timestamp_ms']], cell_sorted, on='timestamp_ms', direction='backward')
        
        proc_df['cell_id'] = cell_merged['cell_id'] if 'cell_id' in cell_merged else np.nan
        proc_df['signal_dbm'] = cell_merged['signal_dbm'] if 'signal_dbm' in cell_merged else np.nan
    else:
        proc_df['cell_id'] = np.nan
        proc_df['signal_dbm'] = np.nan

    # 5. Quality & Validity Flags
    proc_df['flag_imu_valid'] = ((proc_df['accel_mag'] >= 2.0) & (proc_df['accel_mag'] <= 25.0)).astype(int)
    proc_df['flag_gnss_valid'] = (proc_df['latitude'].notna() & proc_df['longitude'].notna() & (proc_df['gnss_accuracy'] <= 50.0)).astype(int)
    proc_df['flag_speed_ref_valid'] = (proc_df['gnss_speed_m_s'].notna() & (proc_df['gnss_speed_m_s'] >= 0)).astype(int)
    proc_df['flag_outage'] = (proc_df['flag_gnss_valid'] == 0).astype(int)
    proc_df['flag_cell_valid'] = proc_df['cell_id'].notna().astype(int)

    return proc_df

def preprocess_flattened_web_log(filepath, target_fs=100.0):
    """
    Preprocess flattened web socket CSV log.
    """
    df = pd.read_csv(filepath, low_memory=False)
    
    # Parse phone_timestamp
    df['timestamp_ms'] = pd.to_datetime(df['phone_timestamp']).values.astype(np.float64) // 10**6
    df['timestamp_ms'] = df['timestamp_ms'].astype(np.float64)
    df = df.sort_values('timestamp_ms').drop_duplicates('timestamp_ms')
    
    t_start = float(df['timestamp_ms'].iloc[0])
    t_end = float(df['timestamp_ms'].iloc[-1])
    
    dt_ms = 1000.0 / target_fs
    grid_timestamps = np.arange(t_start, t_end + dt_ms, dt_ms, dtype=np.float64)
    
    proc_df = pd.DataFrame({'timestamp_ms': grid_timestamps})
    proc_df['relative_time_s'] = (proc_df['timestamp_ms'] - t_start) / 1000.0
    
    merged = pd.merge_asof(proc_df, df, on='timestamp_ms', direction='nearest')
    
    proc_df['accel_x'] = pd.to_numeric(merged['accelerometer_x'], errors='coerce').interpolate().bfill().ffill()
    proc_df['accel_y'] = pd.to_numeric(merged['accelerometer_y'], errors='coerce').interpolate().bfill().ffill()
    proc_df['accel_z'] = pd.to_numeric(merged['accelerometer_z'], errors='coerce').interpolate().bfill().ffill()
    
    proc_df['gyro_x'] = pd.to_numeric(merged['gyroscope_alpha'], errors='coerce').interpolate().bfill().ffill()
    proc_df['gyro_y'] = pd.to_numeric(merged['gyroscope_beta'], errors='coerce').interpolate().bfill().ffill()
    proc_df['gyro_z'] = pd.to_numeric(merged['gyroscope_gamma'], errors='coerce').interpolate().bfill().ffill()
    
    proc_df['accel_mag'] = np.sqrt(proc_df['accel_x']**2 + proc_df['accel_y']**2 + proc_df['accel_z']**2)
    proc_df['gyro_mag'] = np.sqrt(proc_df['gyro_x']**2 + proc_df['gyro_y']**2 + proc_df['gyro_z']**2)

    proc_df['accel_x_filt'] = apply_butterworth_filter(proc_df['accel_x'], cutoff=15.0, fs=target_fs)
    proc_df['accel_y_filt'] = apply_butterworth_filter(proc_df['accel_y'], cutoff=15.0, fs=target_fs)
    proc_df['accel_z_filt'] = apply_butterworth_filter(proc_df['accel_z'], cutoff=15.0, fs=target_fs)

    gnss_df = df.dropna(subset=['latitude']).copy()
    if not gnss_df.empty:
        gnss_df['timestamp_ms'] = gnss_df['timestamp_ms'].astype(np.float64)
        gnss_merged = pd.merge_asof(proc_df[['timestamp_ms']], gnss_df, on='timestamp_ms', direction='backward')
        proc_df['latitude'] = pd.to_numeric(gnss_merged['latitude'], errors='coerce') if 'latitude' in gnss_merged else np.nan
        proc_df['longitude'] = pd.to_numeric(gnss_merged['longitude'], errors='coerce') if 'longitude' in gnss_merged else np.nan
        proc_df['altitude'] = pd.to_numeric(gnss_merged['altitude'], errors='coerce') if 'altitude' in gnss_merged else np.nan
        proc_df['gnss_speed_m_s'] = pd.to_numeric(gnss_merged['speed'], errors='coerce') if 'speed' in gnss_merged else np.nan
        proc_df['gnss_accuracy'] = pd.to_numeric(gnss_merged['accuracy'], errors='coerce') if 'accuracy' in gnss_merged else np.nan
        proc_df['gnss_bearing'] = pd.to_numeric(gnss_merged['heading'], errors='coerce') if 'heading' in gnss_merged else np.nan
    else:
        proc_df['latitude'] = np.nan
        proc_df['longitude'] = np.nan
        proc_df['altitude'] = np.nan
        proc_df['gnss_speed_m_s'] = np.nan
        proc_df['gnss_accuracy'] = np.nan
        proc_df['gnss_bearing'] = np.nan

    proc_df['gnss_speed_km_h'] = proc_df['gnss_speed_m_s'] * 3.6

    proc_df['cell_id'] = np.nan
    proc_df['signal_dbm'] = np.nan

    proc_df['flag_imu_valid'] = ((proc_df['accel_mag'] >= 2.0) & (proc_df['accel_mag'] <= 25.0)).astype(int)
    proc_df['flag_gnss_valid'] = (proc_df['latitude'].notna() & proc_df['longitude'].notna()).astype(int)
    proc_df['flag_speed_ref_valid'] = (proc_df['gnss_speed_m_s'].notna() & (proc_df['gnss_speed_m_s'] >= 0)).astype(int)
    proc_df['flag_outage'] = (proc_df['flag_gnss_valid'] == 0).astype(int)
    proc_df['flag_cell_valid'] = 0

    return proc_df

def main():
    data_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\data"
    output_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline\processed_data"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    print(f"Preprocessing {len(csv_files)} dataset files to 100 Hz synchronized format...")
    
    for filepath in sorted(csv_files):
        filename = os.path.basename(filepath)
        df = pd.read_csv(filepath, nrows=5)
        
        print(f" -> Processing {filename}...")
        if 'stream_type' in df.columns:
            proc_df = preprocess_interleaved_log(filepath, target_fs=100.0)
        elif 'phone_timestamp' in df.columns:
            proc_df = preprocess_flattened_web_log(filepath, target_fs=100.0)
        else:
            print(f"Skipping unknown format: {filename}")
            continue
            
        if proc_df is not None and not proc_df.empty:
            out_filename = filename.replace('.csv', '_processed.csv')
            out_path = os.path.join(output_dir, out_filename)
            proc_df.to_csv(out_path, index=False)
            print(f"    Saved processed output: {out_filename} ({len(proc_df)} samples @ 100 Hz)")
            
    print(f"\n[SUCCESS] Preprocessing completed! Output files written to {output_dir}")

if __name__ == "__main__":
    main()
