"""
scratch/signed_offset_audit.py
Rigorous calculation of signed timestamp differences, systematic clock offset estimates,
and post-debiasing residual statistics across IO-VNBD dataset pairs.
"""
import os
import glob
import pandas as pd
import numpy as np

base_path = r'C:\Users\Keerthana N\Desktop\IO-VNBD\Synchronised V abd S datasets\Categorised IOVNB Dataset'
pairs = [
    ('IOVNBD_M', os.path.join(base_path, 'M (Driver B)', 'S-M.csv'), os.path.join(base_path, 'M (Driver B)', 'V-M.csv')),
    ('IOVNBD_S1', os.path.join(base_path, 'S (Driver A)', 'S1', 'S-S1.csv'), os.path.join(base_path, 'S (Driver A)', 'S1', 'V-S1.csv')),
    ('IOVNBD_S2', os.path.join(base_path, 'S (Driver A)', 'S2', 'S-S2.csv'), os.path.join(base_path, 'S (Driver A)', 'S2', 'V-S2.csv')),
    ('IOVNBD_S3a', os.path.join(base_path, 'S (Driver A)', 'S3a', 'S-S3a.csv'), os.path.join(base_path, 'S (Driver A)', 'S3a', 'V-S3a.csv')),
    ('IOVNBD_S3c', os.path.join(base_path, 'S (Driver A)', 'S3c', 'S-S3c.csv'), os.path.join(base_path, 'S (Driver A)', 'S3c', 'V-S3c.csv')),
]

results = []

print("==========================================================================")
print("             SIGNED TIMESTAMP DIFFERENCE & CLOCK OFFSET AUDIT             ")
print("==========================================================================\n")

for sid, s_path, v_path in pairs:
    df_s = pd.read_csv(s_path, encoding='latin-1')
    df_v = pd.read_csv(v_path, encoding='latin-1')
    
    df_s.columns = df_s.columns.str.strip()
    df_v.columns = df_v.columns.str.strip()
    
    s_ts_col = [c for c in df_s.columns if 'time' in c.lower() or 'ms' in c.lower()][0]
    v_ts_col = [c for c in df_v.columns if 'time' in c.lower() or 'sec' in c.lower()][0]
    
    s_raw = df_s[s_ts_col].values.astype(float)
    v_raw = df_v[v_ts_col].values.astype(float)
    
    s_scale = 1000.0 if ('ms' in s_ts_col.lower() or s_raw.max() > 1e5) else 1.0
    v_scale = 1000.0 if ('ms' in v_ts_col.lower() or v_raw.max() > 1e5) else 1.0
    
    s_t_sec = s_raw / s_scale
    v_t_sec = v_raw / v_scale
    
    s_rel = s_t_sec - s_t_sec[0]
    v_rel = v_t_sec - v_t_sec[0]
    
    df_s_sorted = pd.DataFrame({'t_s': s_rel, 's_idx': np.arange(len(s_rel))}).sort_values('t_s')
    df_v_sorted = pd.DataFrame({'t_v': v_rel, 'v_idx': np.arange(len(v_rel))}).sort_values('t_v')
    
    # Enforce tolerance = 0.05s (50 ms) to analyze valid synchronized paired records
    merged_tol = pd.merge_asof(
        df_s_sorted,
        df_v_sorted,
        left_on='t_s',
        right_on='t_v',
        direction='nearest',
        tolerance=0.05
    )
    
    # Filter valid matched records
    matched_df = merged_tol.dropna(subset=['t_v']).copy()
    
    # Calculate signed difference: delta_t = (t_s - t_v) in milliseconds
    signed_diff_ms = (matched_df['t_s'] - matched_df['t_v']) * 1000.0
    
    # Estimators:
    # 1. Median signed difference (Robust estimator for systematic clock offset)
    est_offset_median = np.median(signed_diff_ms)
    # 2. Mean signed difference
    est_offset_mean = np.mean(signed_diff_ms)
    
    # Standard deviation of signed differences
    std_diff = np.std(signed_diff_ms)
    
    # Residual error after subtracting the estimated systematic clock offset (median)
    residual_ms = signed_diff_ms - est_offset_median
    abs_residual_ms = np.abs(residual_ms)
    p95_residual = np.percentile(abs_residual_ms, 95)
    mean_abs_residual = np.mean(abs_residual_ms)
    max_abs_residual = np.max(abs_residual_ms)
    
    results.append({
        'Session': sid,
        'Matched Count': len(matched_df),
        'Mean Signed Diff (ms)': est_offset_mean,
        'Median Signed Diff (ms)': est_offset_median,
        'Std Dev (ms)': std_diff,
        'Systematic Offset (Median)': est_offset_median,
        'Post-Offset Mean Abs Residual (ms)': mean_abs_residual,
        'Post-Offset P95 Residual (ms)': p95_residual,
        'Post-Offset Max Residual (ms)': max_abs_residual
    })

df_out = pd.DataFrame(results)
print(df_out.to_string(index=False))
