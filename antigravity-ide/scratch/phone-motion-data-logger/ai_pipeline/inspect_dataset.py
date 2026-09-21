import os
import glob
import json
import pandas as pd
import numpy as np

def convert_np(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def sanitize_dict(d):
    if isinstance(d, dict):
        return {str(k): sanitize_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [sanitize_dict(v) for v in d]
    else:
        return convert_np(d)

def detect_file_schema(filepath):
    """
    Detect dataset structure, columns, stream types, timestamps, and sampling rates.
    """
    df = pd.read_csv(filepath, low_memory=False)
    filename = os.path.basename(filepath)
    
    report = {
        "file_name": filename,
        "file_size_bytes": os.path.getsize(filepath),
        "total_rows": len(df),
        "columns": list(df.columns)
    }
    
    if 'stream_type' in df.columns:
        report["format"] = "Multi-Stream Interleaved Android Log"
        stream_counts = {str(k): int(v) for k, v in df['stream_type'].value_counts().to_dict().items()}
        report["stream_counts"] = stream_counts
        
        # SENSOR stream analysis
        sensor_df = df[df['stream_type'] == 'SENSOR'].dropna(how='all', axis=1).copy()
        gnss_df = df[df['stream_type'] == 'GNSS'].dropna(how='all', axis=1).copy()
        cell_df = df[df['stream_type'] == 'CELLULAR'].dropna(how='all', axis=1).copy()
        
        # Coerce numeric columns for sensor_df
        for col in ['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'mag_x', 'mag_y', 'mag_z', 'timestamp_ms']:
            if col in sensor_df.columns:
                sensor_df[col] = pd.to_numeric(sensor_df[col], errors='coerce')
                
        # Timestamp analysis for SENSOR stream
        if 'timestamp_ms' in sensor_df.columns:
            ts = sensor_df['timestamp_ms'].dropna().values
            dt_ms = np.diff(ts)
            dt_valid = dt_ms[dt_ms > 0] # Filter zero or negative deltas
            duration_s = (ts[-1] - ts[0]) / 1000.0 if len(ts) > 1 else 0
            
            report["sensor_stream_stats"] = {
                "num_samples": int(len(sensor_df)),
                "duration_seconds": float(round(duration_s, 2)),
                "timestamp_column": "timestamp_ms",
                "timestamp_format": "Epoch Milliseconds (int64)",
                "sampling_dt_mean_ms": float(np.mean(dt_valid)) if len(dt_valid) > 0 else 0.0,
                "sampling_dt_std_ms": float(np.std(dt_valid)) if len(dt_valid) > 0 else 0.0,
                "estimated_hz": float(round(1000.0 / np.mean(dt_valid), 2)) if len(dt_valid) > 0 and np.mean(dt_valid) > 0 else 0.0,
                "duplicate_timestamps": int(sum(np.diff(ts) == 0))
            }
            
        # IMU columns & units
        acc_cols = [c for c in ['accel_x', 'accel_y', 'accel_z'] if c in sensor_df.columns]
        gyro_cols = [c for c in ['gyro_x', 'gyro_y', 'gyro_z'] if c in sensor_df.columns]
        
        acc_valid = sensor_df[acc_cols].dropna() if len(acc_cols) == 3 else pd.DataFrame()
        if not acc_valid.empty:
            acc_mag = np.sqrt(acc_valid['accel_x']**2 + acc_valid['accel_y']**2 + acc_valid['accel_z']**2)
            acc_mean_mag = float(np.mean(acc_mag))
            acc_unit = "m/s^2 (includes ~9.81 m/s^2 gravity)" if 8.0 <= acc_mean_mag <= 11.0 else "m/s^2 (no gravity / scaled)"
        else:
            acc_unit = "Not available / All NaNs"
            acc_mean_mag = 0.0
            
        gyro_valid = sensor_df[gyro_cols].dropna() if len(gyro_cols) == 3 else pd.DataFrame()
        if not gyro_valid.empty:
            gyro_mag = np.sqrt(gyro_valid['gyro_x']**2 + gyro_valid['gyro_y']**2 + gyro_valid['gyro_z']**2)
            gyro_mean_mag = float(np.mean(gyro_mag))
            gyro_unit = "rad/s" if gyro_mean_mag < 2.0 else "deg/s"
        else:
            gyro_unit = "Not available / All NaNs"
            gyro_mean_mag = 0.0
            
        report["sensor_units"] = {
            "accelerometer": acc_unit,
            "accelerometer_mean_magnitude": float(round(acc_mean_mag, 3)),
            "gyroscope": gyro_unit,
            "gyroscope_mean_magnitude": float(round(gyro_mean_mag, 4))
        }
        
        # GNSS Stream analysis
        if not gnss_df.empty:
            for col in ['timestamp_ms', 'latitude', 'longitude', 'altitude', 'accuracy', 'speed', 'bearing']:
                if col in gnss_df.columns:
                    gnss_df[col] = pd.to_numeric(gnss_df[col], errors='coerce')
                    
            gnss_ts = gnss_df['timestamp_ms'].dropna().values
            gnss_dt = np.diff(gnss_ts)
            gnss_dt = gnss_dt[gnss_dt > 0]
            
            speeds = gnss_df['speed'].dropna().values if 'speed' in gnss_df.columns else []
            lats = gnss_df['latitude'].dropna().values if 'latitude' in gnss_df.columns else []
            lons = gnss_df['longitude'].dropna().values if 'longitude' in gnss_df.columns else []
            
            report["gnss_stream_stats"] = {
                "num_samples": int(len(gnss_df)),
                "sampling_dt_mean_ms": float(np.mean(gnss_dt)) if len(gnss_dt) > 0 else 0.0,
                "estimated_hz": float(round(1000.0 / np.mean(gnss_dt), 2)) if len(gnss_dt) > 0 and np.mean(gnss_dt) > 0 else 0.0,
                "has_latitude_longitude": bool(len(lats) > 0 and len(lons) > 0),
                "has_speed_reference": bool(len(speeds) > 0),
                "speed_unit": "m/s (meters per second)",
                "speed_min_m_s": float(round(np.min(speeds), 3)) if len(speeds) > 0 else None,
                "speed_max_m_s": float(round(np.max(speeds), 3)) if len(speeds) > 0 else None,
                "speed_mean_m_s": float(round(np.mean(speeds), 3)) if len(speeds) > 0 else None,
                "speed_mean_km_h": float(round(np.mean(speeds) * 3.6, 3)) if len(speeds) > 0 else None,
                "valid_gps_fixes": int((gnss_df['has_fix'] == True).sum()) if 'has_fix' in gnss_df.columns else len(lats)
            }
        else:
            report["gnss_stream_stats"] = {"num_samples": 0, "has_speed_reference": False}

        # Cellular Stream Analysis
        if not cell_df.empty:
            for col in ['timestamp_ms', 'cell_id', 'signal_dbm', 'signal_level']:
                if col in cell_df.columns:
                    cell_df[col] = pd.to_numeric(cell_df[col], errors='coerce')
            report["cellular_stream_stats"] = {
                "num_samples": int(len(cell_df)),
                "registered_cells": int((cell_df['registered'] == True).sum()) if 'registered' in cell_df.columns else len(cell_df),
                "cell_types": [str(x) for x in cell_df['cell_type'].dropna().unique()] if 'cell_type' in cell_df.columns else [],
                "has_cell_id": bool('cell_id' in cell_df.columns and cell_df['cell_id'].notna().sum() > 0),
                "has_signal_dbm": bool('signal_dbm' in cell_df.columns and cell_df['signal_dbm'].notna().sum() > 0)
            }
        else:
            report["cellular_stream_stats"] = {"num_samples": 0}

    elif 'phone_timestamp' in df.columns:
        report["format"] = "Flattened Web Socket CSV"
        # Parse ISO timestamps
        ts = pd.to_datetime(df['phone_timestamp']).values.astype(np.int64) // 10**6
        dt_ms = np.diff(ts)
        dt_ms = dt_ms[dt_ms > 0]
        
        report["sensor_stream_stats"] = {
            "num_samples": int(len(df)),
            "duration_seconds": float(round((ts[-1] - ts[0]) / 1000.0, 2)) if len(ts) > 1 else 0.0,
            "timestamp_column": "phone_timestamp",
            "timestamp_format": "ISO-8601 String",
            "sampling_dt_mean_ms": float(np.mean(dt_ms)) if len(dt_ms) > 0 else 0.0,
            "estimated_hz": float(round(1000.0 / np.mean(dt_ms), 2)) if len(dt_ms) > 0 and np.mean(dt_ms) > 0 else 0.0,
            "duplicate_timestamps": int(sum(np.diff(ts) == 0))
        }
        
        acc_x = pd.to_numeric(df['accelerometer_x'], errors='coerce')
        acc_y = pd.to_numeric(df['accelerometer_y'], errors='coerce')
        acc_z = pd.to_numeric(df['accelerometer_z'], errors='coerce')
        acc_mag = np.sqrt(acc_x**2 + acc_y**2 + acc_z**2).dropna()
        
        report["sensor_units"] = {
            "accelerometer": "m/s^2",
            "accelerometer_mean_magnitude": float(round(np.mean(acc_mag), 3)) if not acc_mag.empty else 0.0,
            "gyroscope": "rad/s"
        }
        
        speeds = pd.to_numeric(df['speed'], errors='coerce').dropna().values if 'speed' in df.columns else []
        report["gnss_stream_stats"] = {
            "num_samples": int(len(df['latitude'].dropna())),
            "has_latitude_longitude": True,
            "has_speed_reference": bool(len(speeds) > 0),
            "speed_min_m_s": float(round(np.min(speeds), 3)) if len(speeds) > 0 else None,
            "speed_max_m_s": float(round(np.max(speeds), 3)) if len(speeds) > 0 else None,
            "speed_mean_m_s": float(round(np.mean(speeds), 3)) if len(speeds) > 0 else None,
            "speed_mean_km_h": float(round(np.mean(speeds) * 3.6, 3)) if len(speeds) > 0 else None
        }

    # Missing values breakdown
    missing_pct = {str(k): float(v) for k, v in (df.isnull().sum() / len(df) * 100).round(2).to_dict().items()}
    report["missing_values_pct"] = missing_pct

    return sanitize_dict(report)

def main():
    data_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\data"
    output_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    print(f"Inspecting {len(csv_files)} files in dataset directory...")
    
    dataset_summary = []
    for f in sorted(csv_files):
        print(f" -> Inspecting {os.path.basename(f)}...")
        rep = detect_file_schema(f)
        dataset_summary.append(rep)
        
    report_path = os.path.join(output_dir, "DATASET_REPORT.json")
    with open(report_path, "w") as fp:
        json.dump(dataset_summary, fp, indent=2)
        
    print(f"\n[SUCCESS] Inspection complete. Report saved to: {report_path}")

if __name__ == "__main__":
    main()
