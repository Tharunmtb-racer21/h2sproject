import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from alignment import PhoneToVehicleAligner
from disturbance import DisturbanceDetector
from outage_simulator import GNSSOutageSimulator
from dead_reckoning import DeadReckoningIntegrator
from fusion_engine import GNSSIMUFusionEngine

def run_sih_pipeline(dataset_filepath, output_dir):
    filename = os.path.basename(dataset_filepath)
    session_id = filename.replace('_processed.csv', '')
    
    print(f"\n================================================================================")
    print(f"RUNNING SIH26168 EXTENDED NAVIGATION PIPELINE FOR: {session_id}")
    print(f"================================================================================")
    
    df = pd.read_csv(dataset_filepath)
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # 1. Module A: Phone-to-Vehicle Frame Alignment
    aligner = PhoneToVehicleAligner()
    static_accel = [df['accel_x'].iloc[0], df['accel_y'].iloc[0], df['accel_z'].iloc[0]]
    pitch, roll = aligner.calibrate_static_pitch_roll(static_accel)
    print(f" -> [Module A] Phone Alignment Calibrated: Pitch = {np.degrees(pitch):.2f}°, Roll = {np.degrees(roll):.2f}°")
    
    # Check for orientation shifts during driving
    shifts_detected = 0
    for i in range(0, len(df), 100):
        curr_acc = [df['accel_x'].iloc[i], df['accel_y'].iloc[i], df['accel_z'].iloc[i]]
        shifted, angle = aligner.detect_mounting_shift(curr_acc, threshold_deg=15.0)
        if shifted:
            shifts_detected += 1
    print(f" -> [Module A] Mounting Orientation Shift Alerts: {shifts_detected} instances detected.")

    # 2. Module B: Disturbance Detection
    detector = DisturbanceDetector()
    df_dist = detector.process_sequence(df)
    disturbance_count = df_dist['is_disturbance'].sum()
    print(f" -> [Module B] Disturbance & Anomaly Detection: {disturbance_count} / {len(df)} frames flagged.")

    # 3. Module C: GNSS Outage Simulation Engine (30s blackout)
    t_max = df['relative_time_s'].max()
    outage_start = max(5.0, min(15.0, t_max * 0.2))
    outage_duration = min(30.0, t_max * 0.5)
    
    simulator = GNSSOutageSimulator(start_time_s=outage_start, duration_s=outage_duration)
    masked_df = simulator.apply_outage_mask(df_dist)
    idx_start, idx_end, act_duration = simulator.get_outage_bounds(masked_df)
    print(f" -> [Module C] Simulated GNSS Outage Active: {outage_start:.1f}s to {outage_start+act_duration:.1f}s (Duration: {act_duration:.1f}s)")

    # 4. Module D: Dead Reckoning Motion Integration
    # Use AI speed estimate if available, otherwise fallback to reference speed / integration
    speeds = masked_df['gnss_speed_m_s'].fillna(0.1).values if 'gnss_speed_m_s' in masked_df else np.ones(len(df)) * 0.5
    yaw_rates = masked_df['gyro_z'].values
    
    start_lat = df['latitude'].dropna().iloc[0] if 'latitude' in df and df['latitude'].notna().any() else 11.016845
    start_lon = df['longitude'].dropna().iloc[0] if 'longitude' in df and df['longitude'].notna().any() else 76.955812
    
    dr = DeadReckoningIntegrator()
    dr_df = dr.integrate_sequence(speeds, yaw_rates, dt=0.01, start_lat=start_lat, start_lon=start_lon, start_heading=0.0)
    
    outage_mask = (masked_df['relative_time_s'] >= outage_start) & (masked_df['relative_time_s'] <= (outage_start + act_duration))
    drift_metrics = dr.compute_drift_metrics(dr_df, df, outage_mask=outage_mask.values)
    
    print(f" -> [Module D] Dead Reckoning Drift Metrics:")
    print(f"      - Position Error RMSE: {drift_metrics['error_rmse_m']} meters")
    print(f"      - Max Positioning Error: {drift_metrics['error_max_m']} meters")
    print(f"      - Cumulative Drift Rate: {drift_metrics['drift_rate_pct']}% of distance traveled ({dr.distance_traveled:.1f}m)")

    # 5. Module E: GNSS/IMU Fusion & Sigmoid Temporal Handover
    fusion = GNSSIMUFusionEngine(t_blend_s=2.0)
    fused_df = fusion.fuse_trajectory(df, dr_df, simulated_outage_start=outage_start, simulated_outage_duration=act_duration)
    
    handover_frames = (fused_df['fusion_mode'] == 'SIGMOID_HANDOVER').sum()
    print(f" -> [Module E] GNSS/IMU Fusion & Temporal Handover Engine:")
    print(f"      - Pure DR Mode Frames: {(fused_df['fusion_mode'] == 'DEAD_RECKONING').sum()}")
    print(f"      - Sigmoid Handover Transition Frames (Zero Position Jump): {handover_frames}")

    # 6. Plot Trajectory Maps
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Ground Truth GNSS (if available)
    valid_gnss = df.dropna(subset=['latitude', 'longitude'])
    if not valid_gnss.empty:
        ax.plot(valid_gnss['longitude'], valid_gnss['latitude'], 'g--', linewidth=2.0, label='GNSS Ground-Truth Reference')
        
    # Dead Reckoning Trajectory
    ax.plot(dr_df['dr_longitude'], dr_df['dr_latitude'], 'r-', linewidth=2.0, label='Pure Dead Reckoning Trajectory (Outage Mode)')
    
    # Fused Trajectory (Sigmoid Blended)
    ax.plot(fused_df['fused_longitude'], fused_df['fused_latitude'], 'b-.', linewidth=2.2, label='Fused Navigation Trajectory (Sigmoid Handover)')
    
    # Mark Outage Segment
    outage_dr = dr_df[outage_mask.values]
    if not outage_dr.empty:
        ax.plot(outage_dr['dr_longitude'], outage_dr['dr_latitude'], 'm-', linewidth=3.5, label=f'Simulated Outage Blackout ({act_duration:.1f}s)')
        
    ax.plot(start_lon, start_lat, 'go', markersize=12, label='Trip Origin')
    
    ax.set_title(f'SIH26168 Dead Reckoning & GNSS Outage Handover: {session_id}', fontweight='bold', fontsize=13)
    ax.set_xlabel('Longitude (deg)', fontweight='bold')
    ax.set_ylabel('Latitude (deg)', fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    plot_path = os.path.join(plots_dir, f"{session_id}_dead_reckoning_fusion.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    
    return {
        'session_id': session_id,
        'alignment': {'pitch_deg': round(np.degrees(pitch), 2), 'roll_deg': round(np.degrees(roll), 2), 'shift_alerts': shifts_detected},
        'disturbance': {'flagged_frames': int(disturbance_count)},
        'outage_simulation': {'start_s': outage_start, 'duration_s': act_duration},
        'dead_reckoning_metrics': drift_metrics,
        'fusion': {'handover_frames': int(handover_frames)}
    }

def main():
    processed_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline\processed_data"
    output_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\sih_modules"
    
    valid_files = [
        os.path.join(processed_dir, "sensor_data_processed.csv"),
        os.path.join(processed_dir, "SESSION-20260917_215707_processed.csv")
    ]
    
    summary_reports = []
    for f in valid_files:
        if os.path.exists(f):
            rep = run_sih_pipeline(f, output_dir)
            summary_reports.append(rep)
            
    with open(os.path.join(output_dir, "SIH_EXTENDED_PIPELINE_REPORT.json"), "w") as fp:
        json.dump(summary_reports, fp, indent=2)
        
    print(f"\n================================================================================")
    print(f"[SUCCESS] SIH Extended Pipeline Execution Complete!")
    print(f" -> JSON Report Saved: {os.path.join(output_dir, 'SIH_EXTENDED_PIPELINE_REPORT.json')}")
    print(f"================================================================================")

if __name__ == "__main__":
    main()
