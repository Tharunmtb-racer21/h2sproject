"""
scratch/target_scale_audit.py
Audits target velocity statistics (min, max, mean, median, std) for Training (M, S1, S2) and Validation (S3a).
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from paper_baseline.dataset import (
    load_and_preprocess_session,
    TRAIN_SESSIONS,
    VAL_SESSIONS,
    TEST_SESSIONS
)

print("==========================================================================")
print("                    TARGET VELOCITY BASELINE SCALE AUDIT                  ")
print("==========================================================================\n")

def analyze_targets(session_list, split_name):
    dfs = [load_and_preprocess_session(sid) for sid in session_list]
    concat_df = pd.concat(dfs, ignore_index=True)
    
    speeds_ms = concat_df['reference_speed'].values
    speeds_kmh = speeds_ms * 3.6
    
    print(f"--- {split_name} SET ({', '.join(session_list)}) ---")
    print(f"Total 50 Hz Samples:   {len(concat_df):,}")
    print(f"Target Speed (m/s):")
    print(f"  - Min:    {np.min(speeds_ms):.4f} m/s")
    print(f"  - Max:    {np.max(speeds_ms):.4f} m/s")
    print(f"  - Mean:   {np.mean(speeds_ms):.4f} m/s")
    print(f"  - Median: {np.median(speeds_ms):.4f} m/s")
    print(f"  - Std:    {np.std(speeds_ms):.4f} m/s")
    print(f"Target Speed (km/h):")
    print(f"  - Min:    {np.min(speeds_kmh):.2f} km/h")
    print(f"  - Max:    {np.max(speeds_kmh):.2f} km/h")
    print(f"  - Mean:   {np.mean(speeds_kmh):.2f} km/h")
    print(f"  - Median: {np.median(speeds_kmh):.2f} km/h")
    print(f"  - Std:    {np.std(speeds_kmh):.2f} km/h")
    print(f"Variance (m/s)^2:    {np.var(speeds_ms):.4f} (m/s)^2\n")
    return np.mean(speeds_ms), np.var(speeds_ms)

tr_mean, tr_var = analyze_targets(TRAIN_SESSIONS, "TRAINING")
val_mean, val_var = analyze_targets(VAL_SESSIONS, "VALIDATION")
te_mean, te_var = analyze_targets(TEST_SESSIONS, "TESTING (HELD-OUT)")

print("--- INITIAL UN-TRAINED MSE INTERPRETATION ---")
print(f"Zero-prediction MSE (predicting 0 m/s constantly): Mean(y^2) = {tr_mean**2 + tr_var:.2f} (m/s)^2")
print(f"Mean-prediction MSE (predicting average speed {tr_mean:.2f} m/s): Var(y) = {tr_var:.2f} (m/s)^2")
print(f"Observed initial un-trained MSE (~65.48) corresponds to an RMSE of sqrt(65.48) = {np.sqrt(65.48):.2f} m/s ({np.sqrt(65.48)*3.6:.2f} km/h).")
