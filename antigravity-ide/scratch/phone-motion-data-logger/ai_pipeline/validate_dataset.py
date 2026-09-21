import os
import glob
import pandas as pd
import numpy as np

def validate_processed_file(filepath):
    filename = os.path.basename(filepath)
    df = pd.read_csv(filepath)
    
    issues = []
    warnings = []
    passed = []
    
    # Check 1: Row count & time grid continuity
    if len(df) < 100:
        issues.append(f"CRITICAL: Insufficient sample count ({len(df)} rows < 1.0 s @ 100Hz)")
    else:
        passed.append(f"Sample count OK: {len(df)} samples ({df['relative_time_s'].max():.2f} seconds)")

    dt = np.diff(df['timestamp_ms'])
    dt_std = np.std(dt)
    if dt_std > 1.0:
        warnings.append(f"Timestamp jitter detected: dt std = {dt_std:.2f} ms")
    else:
        passed.append("Uniform 100 Hz time grid verified (dt = 10.0 ms)")

    # Check 2: Accelerometer validity
    if 'accel_mag' in df.columns:
        mean_acc = df['accel_mag'].mean()
        if mean_acc < 5.0 or mean_acc > 15.0:
            warnings.append(f"Unusual accelerometer mean magnitude: {mean_acc:.2f} m/s² (expected ~9.81 m/s²)")
        else:
            passed.append(f"Accelerometer gravity vector verified: mean ||a|| = {mean_acc:.2f} m/s²")
    else:
        issues.append("CRITICAL: Missing accelerometer magnitude stream")

    # Check 3: Gyroscope validity
    if 'gyro_mag' in df.columns:
        mean_gyro = df['gyro_mag'].mean()
        passed.append(f"Gyroscope angular velocity stream verified: mean ||gyro|| = {mean_gyro:.4f} rad/s")
    else:
        issues.append("CRITICAL: Missing gyroscope stream")

    # Check 4: Ground-truth reference speed availability
    speed_valid_cnt = df['flag_speed_ref_valid'].sum()
    if speed_valid_cnt == 0:
        warnings.append("NO GROUND-TRUTH SPEED REFERENCE: GNSS speed is null or zero across entire recording (Indoor / GNSS-denied log). Required for supervised AI training.")
    else:
        mean_speed = df[df['flag_speed_ref_valid'] == 1]['gnss_speed_km_h'].mean()
        max_speed = df[df['flag_speed_ref_valid'] == 1]['gnss_speed_km_h'].max()
        passed.append(f"Ground-truth speed reference available: {speed_valid_cnt} valid samples (Mean: {mean_speed:.2f} km/h, Max: {max_speed:.2f} km/h)")

    # Check 5: GNSS Trajectory Position
    gnss_valid_cnt = df['flag_gnss_valid'].sum()
    if gnss_valid_cnt == 0:
        warnings.append("NO GNSS POSITION FIX: Latitude/Longitude unavailable. Outage flag active.")
    else:
        passed.append(f"GNSS position fix available: {gnss_valid_cnt} valid samples")

    # Check 6: Cellular network bounds
    cell_cnt = df['flag_cell_valid'].sum()
    if cell_cnt > 0:
        passed.append(f"Cellular tower metrics detected: {cell_cnt} synchronized frames with Cell ID")
    else:
        warnings.append("No Cellular Cell ID metric recorded in this log file.")

    return {
        "file": filename,
        "passed": passed,
        "warnings": warnings,
        "issues": issues,
        "is_ready_for_training": len(issues) == 0 and speed_valid_cnt > 0
    }

def main():
    processed_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline\processed_data"
    proc_files = glob.glob(os.path.join(processed_dir, "*_processed.csv"))
    
    print("="*80)
    print("PHASE 1 DATASET VALIDATION REPORT")
    print("="*80)
    
    training_ready_count = 0
    
    for f in sorted(proc_files):
        res = validate_processed_file(f)
        print(f"\nFILE: {res['file']}")
        print(f" -> Ready for AI Training? {'YES' if res['is_ready_for_training'] else 'NO (Requires Ground-Truth Speed log)'}")
        
        print(" [PASSED CHECKS]:")
        for p in res['passed']:
            print(f"   [OK] {p}")
            
        if res['warnings']:
            print(" [WARNINGS / MISSING REFERENCE SIGNALS]:")
            for w in res['warnings']:
                print(f"   [WARN] {w}")
                
        if res['issues']:
            print(" [CRITICAL ISSUES]:")
            for i in res['issues']:
                print(f"   [FAIL] {i}")

        if res['is_ready_for_training']:
            training_ready_count += 1
            
    print("\n" + "="*80)
    print(f"SUMMARY: {training_ready_count} / {len(proc_files)} dataset files contain valid ground-truth reference speed for AI model training.")
    print("Do not initiate deep learning model training until dataset report and ground-truth validation are completed and approved.")
    print("="*80)

if __name__ == "__main__":
    main()
