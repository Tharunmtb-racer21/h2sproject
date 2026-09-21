import os
import glob
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def generate_plots(filepath, output_dir):
    filename = os.path.basename(filepath)
    df = pd.read_csv(filepath)
    
    session_id = filename.replace('_processed.csv', '')
    print(f" -> Generating plots for {session_id}...")
    
    fig, axes = plt.subplots(5, 1, figsize=(12, 16), sharex=True)
    fig.suptitle(f"Phase 1 Telemetry Report: {session_id}", fontsize=16, fontweight='bold', y=0.98)
    
    time_s = df['relative_time_s']
    
    # Plot 1: Accelerometer X/Y/Z & Filtered
    axes[0].plot(time_s, df['accel_x'], label='Accel X (raw)', alpha=0.5, color='#1f77b4')
    axes[0].plot(time_s, df['accel_y'], label='Accel Y (raw)', alpha=0.5, color='#ff7f0e')
    axes[0].plot(time_s, df['accel_z'], label='Accel Z (raw)', alpha=0.5, color='#2ca02c')
    axes[0].set_ylabel('Accel (m/s²)', fontweight='bold')
    axes[0].set_title('1. Accelerometer X/Y/Z Telemetry', fontsize=12)
    axes[0].legend(loc='upper right', ncol=3)
    axes[0].grid(True, linestyle='--', alpha=0.6)
    
    # Plot 2: Gyroscope X/Y/Z
    axes[1].plot(time_s, df['gyro_x'], label='Gyro X', color='#d62728', alpha=0.8)
    axes[1].plot(time_s, df['gyro_y'], label='Gyro Y', color='#9467bd', alpha=0.8)
    axes[1].plot(time_s, df['gyro_z'], label='Gyro Z', color='#8c564b', alpha=0.8)
    axes[1].set_ylabel('Gyro (rad/s)', fontweight='bold')
    axes[1].set_title('2. Gyroscope X/Y/Z Angular Velocity', fontsize=12)
    axes[1].legend(loc='upper right', ncol=3)
    axes[1].grid(True, linestyle='--', alpha=0.6)
    
    # Plot 3: Acceleration Magnitude
    axes[2].plot(time_s, df['accel_mag'], label='Raw Magnitude ||a||', color='#17becf', alpha=0.6)
    if 'accel_x_filt' in df.columns:
        filt_mag = np.sqrt(df['accel_x_filt']**2 + df['accel_y_filt']**2 + df['accel_z_filt']**2)
        axes[2].plot(time_s, filt_mag, label='Butterworth 15Hz ||a||', color='#e377c2', linewidth=1.5)
    axes[2].axhline(9.81, color='red', linestyle=':', label='Gravity (9.81 m/s²)')
    axes[2].set_ylabel('Magnitude (m/s²)', fontweight='bold')
    axes[2].set_title('3. Acceleration Magnitude & Vibration Filtering', fontsize=12)
    axes[2].legend(loc='upper right', ncol=3)
    axes[2].grid(True, linestyle='--', alpha=0.6)
    
    # Plot 4: Speed / Velocity Reference
    if 'gnss_speed_m_s' in df.columns and df['gnss_speed_m_s'].notna().sum() > 0:
        axes[3].plot(time_s, df['gnss_speed_m_s'], label='GNSS Speed (m/s)', color='#2ca02c', linewidth=2.0)
        axes[3].plot(time_s, df['gnss_speed_km_h'], label='GNSS Speed (km/h)', color='#ff7f0e', linestyle='--', alpha=0.8)
        axes[3].set_ylabel('Speed', fontweight='bold')
        axes[3].set_title('4. Reference Ground-Truth Vehicle Speed', fontsize=12)
        axes[3].legend(loc='upper right')
    else:
        axes[3].text(0.5, 0.5, 'NO VALID GNSS SPEED REFERENCE IN THIS LOG\n(Simulated Outage / Indoors)',
                     horizontalalignment='center', verticalalignment='center', transform=axes[3].transAxes,
                     color='darkred', fontweight='bold', fontsize=12)
        axes[3].set_ylabel('Speed', fontweight='bold')
        axes[3].set_title('4. Reference Ground-Truth Vehicle Speed [MISSING / OUTAGE]', fontsize=12)
    axes[3].grid(True, linestyle='--', alpha=0.6)
    
    # Plot 5: Quality Flags & Outages
    axes[4].plot(time_s, df['flag_imu_valid'], label='IMU Valid', color='green', alpha=0.7)
    axes[4].plot(time_s, df['flag_gnss_valid'], label='GNSS Valid', color='blue', alpha=0.7)
    axes[4].plot(time_s, df['flag_outage'], label='GNSS Outage Flag', color='red', linestyle='--', alpha=0.8)
    axes[4].set_ylabel('Flags (0/1)', fontweight='bold')
    axes[4].set_xlabel('Time (seconds)', fontweight='bold')
    axes[4].set_title('5. Data Quality & GNSS Signal Outage Flags', fontsize=12)
    axes[4].set_ylim(-0.1, 1.2)
    axes[4].legend(loc='upper right', ncol=3)
    axes[4].grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    plot_path = os.path.join(output_dir, f"{session_id}_telemetry_plot.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    
    # 2D GNSS Trajectory Plot if location data exists
    valid_locs = df.dropna(subset=['latitude', 'longitude'])
    if not valid_locs.empty and len(valid_locs) > 1:
        fig_map, ax_map = plt.subplots(figsize=(8, 8))
        ax_map.plot(valid_locs['longitude'], valid_locs['latitude'], 'b-o', markersize=3, label='GNSS Ground Track')
        ax_map.plot(valid_locs['longitude'].iloc[0], valid_locs['latitude'].iloc[0], 'go', markersize=10, label='Start Point')
        ax_map.plot(valid_locs['longitude'].iloc[-1], valid_locs['latitude'].iloc[-1], 'ro', markersize=10, label='End Point')
        ax_map.set_xlabel('Longitude (deg)', fontweight='bold')
        ax_map.set_ylabel('Latitude (deg)', fontweight='bold')
        ax_map.set_title(f'GNSS 2D Trajectory Map: {session_id}', fontweight='bold')
        ax_map.grid(True, linestyle='--', alpha=0.6)
        ax_map.legend()
        traj_plot_path = os.path.join(output_dir, f"{session_id}_trajectory_map.png")
        plt.savefig(traj_plot_path, dpi=200)
        plt.close()

def main():
    processed_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline\processed_data"
    output_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline\plots"
    os.makedirs(output_dir, exist_ok=True)
    
    proc_files = glob.glob(os.path.join(processed_dir, "*_processed.csv"))
    print(f"Generating Phase 1 telemetry plots for {len(proc_files)} dataset files...")
    
    for f in sorted(proc_files):
        generate_plots(f, output_dir)
        
    print(f"\n[SUCCESS] Plots generated! Figures saved to {output_dir}")

if __name__ == "__main__":
    main()
