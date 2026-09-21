import os
import glob
import json
import pandas as pd
import numpy as np

def find_col(df, prefix):
    """
    Find column matching prefix (case-insensitive, ignoring special degree characters).
    """
    for col in df.columns:
        if prefix.lower() in col.lower():
            return col
    return None

def process_iovnbd_session_pair(s_path, v_path, session_id, target_dir):
    """
    Process paired smartphone (S) and vehicle ECU (V) files from IO-VNBD,
    synchronize streams onto 10 Hz uniform time grid,
    and save standardized CSV to target_dir.
    """
    s_df = pd.read_csv(s_path, encoding='latin1')
    v_df = pd.read_csv(v_path, encoding='latin1')
    
    s_df.columns = [c.strip() for c in s_df.columns]
    v_df.columns = [c.strip() for c in v_df.columns]
    
    # Locate column names dynamically
    col_s_time = find_col(s_df, 'TIME SINCE START (ms)') or 'TIME SINCE START (ms)'
    col_v_time = find_col(v_df, 'Time Since Start of Day (seconds)') or 'Time Since Start of Day (seconds)'
    
    # 1. Parse smartphone timestamps
    s_ts_ms = pd.to_numeric(s_df[col_s_time], errors='coerce')
    s_df['timestamp_ms'] = s_ts_ms
    s_clean = s_df.dropna(subset=['timestamp_ms']).sort_values('timestamp_ms').drop_duplicates('timestamp_ms')
    
    # 2. Parse vehicle timestamps
    v_ts_sec = pd.to_numeric(v_df[col_v_time], errors='coerce')
    v_df['timestamp_ms'] = (v_ts_sec - v_ts_sec.iloc[0]) * 1000.0 + s_clean['timestamp_ms'].iloc[0]
    v_clean = v_df.dropna(subset=['timestamp_ms']).sort_values('timestamp_ms').drop_duplicates('timestamp_ms')
    
    # 3. Synchronize streams via merge_asof
    s_clean['timestamp_ms'] = s_clean['timestamp_ms'].astype(np.float64)
    v_clean['timestamp_ms'] = v_clean['timestamp_ms'].astype(np.float64)
    
    merged = pd.merge_asof(s_clean, v_clean, on='timestamp_ms', direction='nearest', suffixes=('_s', '_v'))
    
    # Extract standardized fields
    out_df = pd.DataFrame()
    out_df['timestamp'] = merged['timestamp_ms']
    out_df['relative_time_s'] = (merged['timestamp_ms'] - merged['timestamp_ms'].iloc[0]) / 1000.0
    
    # Smartphone IMU (m/s^2 and rad/s)
    col_ax = find_col(merged, 'ACCELEROMETER X')
    col_ay = find_col(merged, 'ACCELEROMETER Y')
    col_az = find_col(merged, 'ACCELEROMETER Z')
    
    out_df['accel_x'] = pd.to_numeric(merged[col_ax], errors='coerce').interpolate().bfill().ffill() if col_ax else 0.0
    out_df['accel_y'] = pd.to_numeric(merged[col_ay], errors='coerce').interpolate().bfill().ffill() if col_ay else 0.0
    out_df['accel_z'] = pd.to_numeric(merged[col_az], errors='coerce').interpolate().bfill().ffill() if col_az else 0.0
    
    col_gx = find_col(merged, 'GYROSCOPE Yaw')
    col_gy = find_col(merged, 'GYROSCOPE Pitch')
    col_gz = find_col(merged, 'GYROSCOPE Roll')
    
    out_df['gyro_x'] = pd.to_numeric(merged[col_gx], errors='coerce').interpolate().bfill().ffill() if col_gx else 0.0
    out_df['gyro_y'] = pd.to_numeric(merged[col_gy], errors='coerce').interpolate().bfill().ffill() if col_gy else 0.0
    out_df['gyro_z'] = pd.to_numeric(merged[col_gz], errors='coerce').interpolate().bfill().ffill() if col_gz else 0.0
    
    # Smartphone GNSS
    col_lat_s = find_col(merged, 'GPS LATITUDE')
    col_lon_s = find_col(merged, 'GPS LONGITUDE')
    col_alt_s = find_col(merged, 'GPS ALTITUDE')
    col_spd_s = find_col(merged, 'GPS SPEED')
    col_ori_s = find_col(merged, 'GPS ORIENTATION')
    
    out_df['latitude'] = pd.to_numeric(merged[col_lat_s], errors='coerce') if col_lat_s else np.nan
    out_df['longitude'] = pd.to_numeric(merged[col_lon_s], errors='coerce') if col_lon_s else np.nan
    out_df['altitude'] = pd.to_numeric(merged[col_alt_s], errors='coerce') if col_alt_s else np.nan
    
    s_spd = pd.to_numeric(merged[col_spd_s], errors='coerce') if col_spd_s else pd.Series(np.nan, index=merged.index)
    out_df['gnss_speed'] = s_spd / 3.6 # km/h to m/s
    out_df['gnss_bearing'] = pd.to_numeric(merged[col_ori_s], errors='coerce') if col_ori_s else np.nan
    
    # Vehicle ECU Ground Truth
    col_v_spd = find_col(merged, 'Velocity (km/hr)')
    col_v_hdg = find_col(merged, 'Heading (degrees)')
    
    v_spd = pd.to_numeric(merged[col_v_spd], errors='coerce') if col_v_spd else pd.Series(np.nan, index=merged.index)
    out_df['reference_speed'] = v_spd / 3.6 # km/h to m/s ground-truth
    out_df['reference_speed_kmh'] = v_spd
    out_df['reference_heading'] = pd.to_numeric(merged[col_v_hdg], errors='coerce') if col_v_hdg else np.nan
    
    out_df['session_id'] = session_id
    out_df['vehicle_id'] = 'Research_Vehicle_Ford_Fiesta'
    
    out_path = os.path.join(target_dir, f"{session_id}_standardized.csv")
    out_df.to_csv(out_path, index=False)
    v_max = v_spd.max() if not v_spd.empty else 0.0
    print(f" -> Processed & Saved: {out_path} ({len(out_df)} rows, max ECU speed {v_max:.1f} km/h)")
    return out_path

def main():
    iovnbd_root = r"C:\Users\Keerthana N\Desktop\IO-VNBD"
    synced_dir = os.path.join(iovnbd_root, "SYNCHRONISED_DATA", "Synchronised V abd S datasets", "Categorised IOVNB Dataset")
    if not os.path.exists(synced_dir):
        synced_dir = os.path.join(iovnbd_root, "Synchronised V abd S datasets", "Categorised IOVNB Dataset")

    target_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\data\iovnbd_selected"
    os.makedirs(target_dir, exist_ok=True)

    selected_sessions = [
        ("M (Driver B)", "S-M.csv", "V-M.csv", "IOVNBD_M"),
        ("S (Driver A)/S1", "S-S1.csv", "V-S1.csv", "IOVNBD_S1"),
        ("S (Driver A)/S2", "S-S2.csv", "V-S2.csv", "IOVNBD_S2"),
        ("S (Driver A)/S3a", "S-S3a.csv", "V-S3a.csv", "IOVNBD_S3a"),
        ("S (Driver A)/S3c", "S-S3c.csv", "V-S3c.csv", "IOVNBD_S3c"),
        ("Vtb (Driver E)/Vtb1", "S-Vtb1.csv", "V-Vtb1.csv", "IOVNBD_Vtb1"),
        ("Vta (Driver E)/Vta1a", "S-Vta1a.csv", "V-Vta1a.csv", "IOVNBD_Vta1a")
    ]

    print("================================================================================")
    print("STANDARDIZING SELECTED IO-VNBD HIGH-SPEED VEHICLE DRIVING SESSIONS")
    print("================================================================================")

    for subpath, s_name, v_name, sid in selected_sessions:
        s_file = os.path.join(synced_dir, subpath, s_name)
        v_file = os.path.join(synced_dir, subpath, v_name)
        
        if os.path.exists(s_file) and os.path.exists(v_file):
            process_iovnbd_session_pair(s_file, v_file, sid, target_dir)
        else:
            print(f"Warning: Files missing for session {sid} at {s_file}")

    print("\n[SUCCESS] Standardized IO-VNBD datasets saved to data/iovnbd_selected/")

if __name__ == "__main__":
    main()
