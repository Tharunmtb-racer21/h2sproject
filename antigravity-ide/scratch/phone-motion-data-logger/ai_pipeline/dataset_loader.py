import os
import glob
import pandas as pd
import numpy as np

def build_paper_features(df, window_size=200):
    """
    Construct 21-dimensional feature matrix per timestep following Shin et al. (2025):
    - 7 Raw Features: [accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, accel_mag]
    - 14 Statistical Features: mean (mu) and sample variance (sigma^2) of the 7 raw features over window T.
    """
    # 1. Raw 7 features
    acc_x = df['accel_x'].values
    acc_y = df['accel_y'].values
    acc_z = df['accel_z'].values
    gyro_x = df['gyro_x'].values
    gyro_y = df['gyro_y'].values
    gyro_z = df['gyro_z'].values
    acc_mag = df['accel_mag'].values
    
    raw_matrix = np.column_stack([acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, acc_mag]) # (N, 7)
    
    # Min-Max Normalization on raw features
    raw_min = np.min(raw_matrix, axis=0, keepdims=True)
    raw_max = np.max(raw_matrix, axis=0, keepdims=True)
    raw_range = np.where(raw_max - raw_min == 0, 1.0, raw_max - raw_min)
    raw_norm = (raw_matrix - raw_min) / raw_range
    
    # 2. Rolling statistical features (mean and sample variance) over window T
    df_raw = pd.DataFrame(raw_norm, columns=[f'r_{i}' for i in range(7)])
    rolling_mean = df_raw.rolling(window=window_size, min_periods=1).mean().values # (N, 7)
    rolling_var = df_raw.rolling(window=window_size, min_periods=1).var(ddof=1).fillna(0.0).values # (N, 7)
    
    # Concatenate to 21-dimensional feature vector per timestep
    feature_matrix = np.hstack([raw_norm, rolling_mean, rolling_var]) # (N, 21)
    return feature_matrix

def create_session_sequences(filepath, sequence_length=200, stride=10):
    """
    Create time-based sequences (T x D) for a single recording session.
    Checks target validity and excludes sessions lacking ground-truth speed.
    """
    filename = os.path.basename(filepath)
    df = pd.read_csv(filepath)
    
    # Check if session has valid ground-truth speed reference
    valid_speed_mask = df['flag_speed_ref_valid'] == 1
    if not valid_speed_mask.any() or df['gnss_speed_m_s'].isnull().all():
        print(f" -> [EXCLUDED] {filename}: Lacks ground-truth speed target. Excluded from training set.")
        return None, None, None
        
    feature_matrix = build_paper_features(df, window_size=sequence_length)
    target_speeds = df['gnss_speed_m_s'].values # m/s
    
    X_seq = []
    y_seq = []
    metadata = []
    
    N = len(df)
    for i in range(0, N - sequence_length + 1, stride):
        window_x = feature_matrix[i : i + sequence_length] # (T, 21)
        target_v = target_speeds[i + sequence_length - 1] # target at end of window
        
        if np.isnan(target_v):
            continue
            
        X_seq.append(window_x)
        y_seq.append(target_v)
        
        # Segment labeling for evaluation
        window_gyro_z = df['gyro_z'].iloc[i : i + sequence_length].values
        window_acc_z = df['accel_z'].iloc[i : i + sequence_length].values
        
        is_stat = 1 if target_v < 0.05 else 0
        is_turn = 1 if np.max(np.abs(window_gyro_z)) > 0.2 else 0
        is_vib = 1 if np.var(window_acc_z) > 1.5 else 0
        
        metadata.append({
            'session': filename,
            'is_stationary': is_stat,
            'is_turning': is_turn,
            'is_vibration': is_vib
        })
        
    if not X_seq:
        return None, None, None
        
    return np.array(X_seq, dtype=np.float32), np.array(y_seq, dtype=np.float32), metadata

def load_dataset_by_sessions(processed_dir, sequence_length=200, stride=10):
    """
    Load all sessions and perform session-based train/val/test split.
    """
    files = sorted(glob.glob(os.path.join(processed_dir, "*_processed.csv")))
    
    session_data = {}
    excluded_files = []
    
    for f in files:
        X, y, meta = create_session_sequences(f, sequence_length=sequence_length, stride=stride)
        if X is not None:
            session_data[os.path.basename(f)] = (X, y, meta)
        else:
            excluded_files.append(os.path.basename(f))
            
    print(f"\nDataset Loading Summary:")
    print(f" -> Valid Sessions for Training/Evaluation ({len(session_data)}): {list(session_data.keys())}")
    print(f" -> Excluded Sessions (Missing Speed Ground-Truth) ({len(excluded_files)}): {excluded_files}")
    
    return session_data, excluded_files

if __name__ == "__main__":
    pdir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline\processed_data"
    sdata, ex_files = load_dataset_by_sessions(pdir, sequence_length=200)
