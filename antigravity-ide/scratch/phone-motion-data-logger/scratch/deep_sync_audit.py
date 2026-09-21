"""
scratch/deep_sync_audit.py
Definitive, rigorous synchronization audit for IO-VNBD dataset pairs (M, S1, S2, S3a, S3c).
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
print("             DEFINITIVE EXPERIMENTAL SYNCHRONIZATION AUDIT                ")
print("==========================================================================\n")

for sid, s_path, v_path in pairs:
    print(f"--- Processing {sid} ---")
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
    
    # Relative time from start of session
    s_rel = s_t_sec - s_t_sec[0]
    v_rel = v_t_sec - v_t_sec[0]
    
    df_s_sorted = pd.DataFrame({'t_s': s_rel, 's_idx': np.arange(len(s_rel))}).sort_values('t_s')
    df_v_sorted = pd.DataFrame({'t_v': v_rel, 'v_idx': np.arange(len(v_rel))}).sort_values('t_v')
    
    # A. Diagnostic merge_asof WITHOUT tolerance
    merged_diag = pd.merge_asof(
        df_s_sorted,
        df_v_sorted,
        left_on='t_s',
        right_on='t_v',
        direction='nearest'
    )
    diff_diag_ms = np.abs(merged_diag['t_s'] - merged_diag['t_v']) * 1000.0
    
    # B. Valid merge_asof WITH tolerance = 0.05 seconds (50 ms)
    merged_tol = pd.merge_asof(
        df_s_sorted,
        df_v_sorted,
        left_on='t_s',
        right_on='t_v',
        direction='nearest',
        tolerance=0.05
    )
    
    total_records = len(df_s_sorted)
    matched_mask = ~merged_tol['t_v'].isna()
    matched_count = matched_mask.sum()
    rejected_count = total_records - matched_count
    match_pct = (matched_count / total_records) * 100.0
    
    # Statistics on diagnostic match differences
    mean_diff = np.mean(diff_diag_ms)
    median_diff = np.median(diff_diag_ms)
    p95_diff = np.percentile(diff_diag_ms, 95)
    max_diff = np.max(diff_diag_ms)
    
    gt_20ms = (diff_diag_ms > 20.0).sum()
    gt_50ms = (diff_diag_ms > 50.0).sum()
    gt_100ms = (diff_diag_ms > 100.0).sum()
    
    results.append({
        'sid': sid,
        'total': total_records,
        'matched': matched_count,
        'rejected': rejected_count,
        'match_pct': match_pct,
        'mean_ms': mean_diff,
        'median_ms': median_diff,
        'p95_ms': p95_diff,
        'max_ms': max_diff,
        'gt_20ms': gt_20ms,
        'gt_50ms': gt_50ms,
        'gt_100ms': gt_100ms
    })
    
    # Detailed M Session investigation for > 100 ms differences
    if sid == 'IOVNBD_M':
        print(f"\n==========================================================================")
        print(f"       INVESTIGATION OF LARGE TIMESTAMPS / GAPS (> 100 ms) IN SESSION M  ")
        print(f"==========================================================================")
        large_diff_mask = diff_diag_ms > 100.0
        large_indices = np.where(large_diff_mask)[0]
        print(f"Total records in M with time diff > 100 ms: {len(large_indices)}")
        
        # Group contiguous index blocks to identify gaps
        gap_blocks = []
        if len(large_indices) > 0:
            curr_block = [large_indices[0]]
            for idx in large_indices[1:]:
                if idx == curr_block[-1] + 1:
                    curr_block.append(idx)
                else:
                    gap_blocks.append(curr_block)
                    curr_block = [idx]
            gap_blocks.append(curr_block)
            
        print(f"Identified {len(gap_blocks)} contiguous gap block(s) exceeding 100 ms:\n")
        
        for b_idx, block in enumerate(gap_blocks):
            b_start = block[0]
            b_end = block[-1]
            s_t_start = merged_diag.iloc[b_start]['t_s']
            s_t_end = merged_diag.iloc[b_end]['t_s']
            v_t_start = merged_diag.iloc[b_start]['t_v']
            v_t_end = merged_diag.iloc[b_end]['t_v']
            max_block_diff = np.max(diff_diag_ms[block])
            
            print(f"Block #{b_idx+1} (Rows {b_start} to {b_end}, Total {len(block)} records):")
            print(f"  Smartphone Relative Time: {s_t_start:.3f}s to {s_t_end:.3f}s")
            print(f"  Matched Vehicle Time:    {v_t_start:.3f}s to {v_t_end:.3f}s")
            print(f"  Max Matching Difference: {max_block_diff:.3f} ms")
            
            # Print first 3 and last 3 samples in the block
            print(f"  Sample Breakdown (First 3):")
            for i in block[:min(3, len(block))]:
                row = merged_diag.iloc[i]
                print(f"    - S_t: {row['t_s']:.3f}s | Nearest V_t: {row['t_v']:.3f}s | Diff: {diff_diag_ms[i]:.1f} ms")
            print()

# Print summary table
df_res = pd.DataFrame(results)
print("==========================================================================")
print("                         FINAL AUDIT SUMMARY TABLE                        ")
print("==========================================================================")
print(df_res.to_string(index=False))
