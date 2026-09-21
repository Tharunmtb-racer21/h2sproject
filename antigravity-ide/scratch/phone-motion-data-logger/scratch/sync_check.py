"""
scratch/sync_check.py
Experimental synchronization audit between raw S-*.csv and V-*.csv files in IO-VNBD.
"""
import os
import glob
import pandas as pd
import numpy as np

base_path = r'C:\Users\Keerthana N\Desktop\IO-VNBD\Synchronised V abd S datasets\Categorised IOVNB Dataset'
pairs = [
    ('M', os.path.join(base_path, 'M (Driver B)', 'S-M.csv'), os.path.join(base_path, 'M (Driver B)', 'V-M.csv')),
    ('S1', os.path.join(base_path, 'S (Driver A)', 'S1', 'S-S1.csv'), os.path.join(base_path, 'S (Driver A)', 'S1', 'V-S1.csv')),
    ('S2', os.path.join(base_path, 'S (Driver A)', 'S2', 'S-S2.csv'), os.path.join(base_path, 'S (Driver A)', 'S2', 'V-S2.csv')),
    ('S3a', os.path.join(base_path, 'S (Driver A)', 'S3a', 'S-S3a.csv'), os.path.join(base_path, 'S (Driver A)', 'S3a', 'V-S3a.csv')),
    ('S3c', os.path.join(base_path, 'S (Driver A)', 'S3c', 'S-S3c.csv'), os.path.join(base_path, 'S (Driver A)', 'S3c', 'V-S3c.csv')),
]

for sid, s_path, v_path in pairs:
    print(f"=== RAW PAIR EXPERIMENTAL AUDIT: {sid} ===")
    if not os.path.exists(s_path) or not os.path.exists(v_path):
        print(f"Missing file: S_exists={os.path.exists(s_path)}, V_exists={os.path.exists(v_path)}")
        continue
    df_s = pd.read_csv(s_path, encoding='latin-1')
    df_v = pd.read_csv(v_path, encoding='latin-1')
    
    # Strip whitespace from columns
    df_s.columns = df_s.columns.str.strip()
    df_v.columns = df_v.columns.str.strip()
    
    s_ts_col = [c for c in df_s.columns if 'time' in c.lower() or 'ms' in c.lower()][0]
    v_ts_col = [c for c in df_v.columns if 'time' in c.lower() or 'sec' in c.lower()][0]
    
    s_raw = df_s[s_ts_col].values.astype(float)
    v_raw = df_v[v_ts_col].values.astype(float)
    
    # Check if S timestamp is in ms vs seconds
    s_scale = 1000.0 if ('ms' in s_ts_col.lower() or s_raw.max() > 1e5) else 1.0
    v_scale = 1000.0 if ('ms' in v_ts_col.lower() or v_raw.max() > 1e5) else 1.0
    
    s_t_sec = s_raw / s_scale
    v_t_sec = v_raw / v_scale
    
    # Calculate relative time offsets
    s_rel = s_t_sec - s_t_sec[0]
    v_rel = v_t_sec - v_t_sec[0]
    
    print(f"S Dataset ({len(df_s)} rows): Column='{s_ts_col}', Raw Range=[{s_raw[0]:.1f}, {s_raw[-1]:.1f}], Duration={s_rel[-1]:.2f}s ({s_rel[-1]/60:.2f} min)")
    print(f"V Dataset ({len(df_v)} rows): Column='{v_ts_col}', Raw Range=[{v_raw[0]:.1f}, {v_raw[-1]:.1f}], Duration={v_rel[-1]:.2f}s ({v_rel[-1]/60:.2f} min)")
    
    dt_s = np.diff(s_rel)
    dt_v = np.diff(v_rel)
    print(f"S Sampling dt (s): min={dt_s.min():.4f}, mean={dt_s.mean():.4f}, median={np.median(dt_s):.4f}, max={dt_s.max():.4f}")
    print(f"V Sampling dt (s): min={dt_v.min():.4f}, mean={dt_v.mean():.4f}, median={np.median(dt_v):.4f}, max={dt_v.max():.4f}")
    
    # Experimental merge_asof on relative time
    df_s_tmp = pd.DataFrame({'t_s': s_rel, 's_idx': np.arange(len(s_rel))}).sort_values('t_s')
    df_v_tmp = pd.DataFrame({'t_v': v_rel, 'v_idx': np.arange(len(v_rel))}).sort_values('t_v')
    
    merged = pd.merge_asof(
        df_s_tmp,
        df_v_tmp,
        left_on='t_s',
        right_on='t_v',
        direction='nearest'
    )
    
    diff_ms = np.abs(merged['t_s'] - merged['t_v']) * 1000.0
    unmatched_50ms = (diff_ms > 50.0).sum()
    unmatched_100ms = (diff_ms > 100.0).sum()
    
    print(f"merge_asof Time Offset (ms): min={diff_ms.min():.3f} ms, mean={diff_ms.mean():.3f} ms, median={np.median(diff_ms):.3f} ms, max={diff_ms.max():.3f} ms")
    print(f"Unmatched (>50ms): {unmatched_50ms} / {len(merged)} ({unmatched_50ms/len(merged)*100:.2f}%)")
    print(f"Unmatched (>100ms): {unmatched_100ms} / {len(merged)} ({unmatched_100ms/len(merged)*100:.2f}%)")
    print()
