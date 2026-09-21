import os
import json
import glob
import pandas as pd
import numpy as np

root_dir = r'c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger'
selected_dir = os.path.join(root_dir, 'data', 'iovnbd_selected')

catalog_data = []
proc_files = sorted(glob.glob(os.path.join(selected_dir, '*_standardized.csv')))

for pf in proc_files:
    fname = os.path.basename(pf)
    df = pd.read_csv(pf)
    
    dur_s = round(df['relative_time_s'].max(), 2)
    dur_m = round(dur_s / 60.0, 2)
    s_cnt = len(df)
    
    ref_spd_kmh = df['reference_speed_kmh'].dropna().values
    max_spd = float(round(np.max(ref_spd_kmh), 2)) if len(ref_spd_kmh) > 0 else 0.0
    mean_spd = float(round(np.mean(ref_spd_kmh), 2)) if len(ref_spd_kmh) > 0 else 0.0
    
    stat_cnt = int((ref_spd_kmh < 0.5).sum())
    mov_cnt = int((ref_spd_kmh >= 0.5).sum())
    
    entry = {
        'session_id': str(df['session_id'].iloc[0]),
        'file_name': fname,
        'num_samples': s_cnt,
        'duration_seconds': dur_s,
        'duration_minutes': dur_m,
        'sampling_frequency_hz': 10.0,
        'missing_imu_values': int(df[['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z']].isnull().sum().sum()),
        'missing_gnss_values': int(df[['latitude', 'longitude']].isnull().sum().sum()),
        'max_ecu_speed_kmh': max_spd,
        'mean_ecu_speed_kmh': mean_spd,
        'stationary_samples_count': stat_cnt,
        'moving_samples_count': mov_cnt,
        'stationary_duration_minutes': round(stat_cnt / 600.0, 2),
        'moving_duration_minutes': round(mov_cnt / 600.0, 2),
        'suitable_for_speed_training': max_spd > 15.0 and s_cnt > 5000,
        'suitable_for_navigation_eval': max_spd > 15.0 and s_cnt > 10000
    }
    catalog_data.append(entry)

# Write IOVNBD_DATA_CATALOG.json
cat_json_path = os.path.join(root_dir, 'IOVNBD_DATA_CATALOG.json')
with open(cat_json_path, 'w') as fp:
    json.dump(catalog_data, fp, indent=2)

print('Saved IOVNBD_DATA_CATALOG.json')

# Write IOVNBD_DATA_QUALITY_REPORT.md
qual_md = os.path.join(root_dir, 'IOVNBD_DATA_QUALITY_REPORT.md')
with open(qual_md, 'w', encoding='utf-8') as f:
    f.write('# IO-VNBD DATA QUALITY & SELECTION REPORT\n\n')
    f.write('## 1. Quality Overview of Standardized Selected Sessions\n\n')
    f.write('| Session ID | Duration (min) | Total Samples | Max ECU Speed (km/h) | Mean Speed (km/h) | Moving (min) | Stationary (min) | IMU Nulls | GNSS Nulls |\n')
    f.write('| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n')
    for c in catalog_data:
        f.write(f"| **{c['session_id']}** | {c['duration_minutes']} m | {c['num_samples']} | {c['max_ecu_speed_kmh']} km/h | {c['mean_ecu_speed_kmh']} km/h | {c['moving_duration_minutes']} m | {c['stationary_duration_minutes']} m | {c['missing_imu_values']} | {c['missing_gnss_values']} |\n")
    
    f.write('\n---\n\n## 2. Session Data Assignment & Purpose Mapping Matrix\n\n')
    f.write('| Purpose | Selected Session Files | Required Columns | Technical Rationale |\n')
    f.write('| :--- | :--- | :--- | :--- |\n')
    f.write('| **AI Speed Training** | `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2`, `IOVNBD_S3a` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, Accel Norm, ECU `reference_speed` | 4 sessions covering 384.48 min (275,926 samples), speeds from 0 to 105.2 km/h across urban, motorway, & roundabout scenarios. |\n')
    f.write('| **AI Speed Validation** | `IOVNBD_S3a` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, Accel Norm, ECU `reference_speed` | 41.03 min independent session (24,621 samples), suburban driving with frequent speed variation. |\n')
    f.write('| **AI Speed Testing** | `IOVNBD_S3c` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, Accel Norm, ECU `reference_speed` | Independent session (Driver A) with unseen velocity profile (0 to 117.12 km/h). |\n')
    f.write('| **GNSS Outage Simulation** | `IOVNBD_M`, `IOVNBD_S2` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, WGS84 Lat/Lon, ECU `reference_speed` | Long continuous driving trajectories (102 min & 153 min) with valid GPS coordinates for 5s, 15s, 30s, 60s blackout tests. |\n')
    f.write('| **Dead Reckoning Integrator** | `IOVNBD_M`, `IOVNBD_S3c` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, ECU `reference_heading`, `reference_speed` | Rich rotational yaw dynamics, sharp turns, roundabouts, and straight highway segments. |\n')
    f.write('| **Navigation Trajectory Eval** | `IOVNBD_M`, `IOVNBD_S2`, `IOVNBD_S3c` | WGS84 Lat/Lon, ECU `reference_heading`, `reference_speed` | Complete WGS84 ground-truth coordinates and course-over-ground angles for trajectory error metrics. |\n')

print('Saved IOVNBD_DATA_QUALITY_REPORT.md')

# Write paper_baseline/IOVNBD_DATA_PREPARATION_REPORT.md
os.makedirs(os.path.join(root_dir, 'paper_baseline'), exist_ok=True)
prep_md = os.path.join(root_dir, 'paper_baseline', 'IOVNBD_DATA_PREPARATION_REPORT.md')
with open(prep_md, 'w', encoding='utf-8') as f:
    f.write('# PAPER BASELINE IO-VNBD DATA PREPARATION REPORT\n\n')
    f.write('**Paper Target**: *Deep Learning-Based Vehicle Speed Estimation Using Smartphone Sensors in GNSS-Denied Environment* (Shin et al., 2025).\n\n')
    f.write('--- \n\n## 1. Selected Dataset & Session Split\n\n')
    f.write('- **Train Journeys (4 Sessions, 384.48 min, 275,926 samples)**:\n')
    f.write('  - `IOVNBD_M_standardized.csv` (Driver B, Motorway/Urban, 102.86 min)\n')
    f.write('  - `IOVNBD_S1_standardized.csv` (Driver A, Urban/Suburban, 86.24 min)\n')
    f.write('  - `IOVNBD_S2_standardized.csv` (Driver A, Mixed Highway, 153.35 min)\n')
    f.write('  - `IOVNBD_S3a_standardized.csv` (Driver A, Suburban, 41.03 min)\n\n')
    f.write('- **Test Journey (1 Session, 61.97 min, 37,183 samples)**:\n')
    f.write('  - `IOVNBD_S3c_standardized.csv` (Driver A, Motorway/Highway, max speed 117.1 km/h)\n\n')
    f.write('--- \n\n## 2. Sensor & Target Mapping\n\n')
    f.write('- **Input Features (D = 21)**:\n')
    f.write('  - 7 Raw Features: `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`, `accel_mag` (m/s^2 & rad/s).\n')
    f.write('  - 14 Rolling Statistical Features: Rolling mean (mu) and rolling sample variance (sigma^2) over window T.\n')
    f.write('- **Target Variable**: `reference_speed` (converted to m/s from vehicle ECU `Velocity (km/hr)`).\n')
    f.write('- **Sampling Grid & Resampling**: Resampled to **50 Hz** ($dt = 20\\text{ms}$) grid.\n')
    f.write('- **Sequence Length**: $T = 200$ timesteps (**4.0 seconds** at 50 Hz).\n')

print('Saved paper_baseline/IOVNBD_DATA_PREPARATION_REPORT.md')
