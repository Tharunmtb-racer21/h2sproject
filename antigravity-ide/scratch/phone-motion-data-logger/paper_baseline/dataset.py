"""
paper_baseline/dataset.py
SIH26168 - Paper-Aligned PyTorch Dataset and Sequence Pipeline (Shin et al., 2025)

Memory-Optimized Implementation:
1. Session-isolated dataset loading and 50 Hz feature extraction.
2. Anti-leakage MinMax scaling fitted strictly on training data.
3. On-the-fly window slicing in PyTorch Dataset (105 MB RAM instead of 20 GB).
4. PyTorch Dataset and DataLoader creation with zero cross-session or target leakage.
"""

import os
import glob
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from typing import Tuple, List, Dict, Optional

from paper_baseline.feature_extraction import (
    synchronize_s_and_v_streams,
    resample_to_50hz,
    extract_paper_features,
    PaperMinMaxScaler,
    FEATURE_COLUMNS
)

RAW_DATA_PATH = r'C:\Users\Keerthana N\Desktop\IO-VNBD\Synchronised V abd S datasets\Categorised IOVNB Dataset'
SELECTED_DATA_PATH = r'data/iovnbd_selected'

TRAIN_SESSIONS = ['IOVNBD_M', 'IOVNBD_S1', 'IOVNBD_S2']
VAL_SESSIONS = ['IOVNBD_S3a']
TEST_SESSIONS = ['IOVNBD_S3c']


def load_and_preprocess_session(
    session_id: str,
    target_freq_hz: float = 50.0,
    window_size: int = 200
) -> pd.DataFrame:
    """
    Loads raw session CSV file, applies 50ms tolerance synchronization,
    resamples to 50 Hz, and extracts 21 paper-aligned features.
    """
    std_path = os.path.join(SELECTED_DATA_PATH, f'{session_id}_standardized.csv')
    if os.path.exists(std_path):
        df_raw = pd.read_csv(std_path)
    else:
        s_file = glob.glob(os.path.join(RAW_DATA_PATH, '**', f'S-*{session_id[-2:]}.csv'), recursive=True)
        v_file = glob.glob(os.path.join(RAW_DATA_PATH, '**', f'V-*{session_id[-2:]}.csv'), recursive=True)
        if not s_file or not v_file:
            raise FileNotFoundError(f"Raw data files for {session_id} not found.")
        
        df_s = pd.read_csv(s_file[0], encoding='latin-1')
        df_v = pd.read_csv(v_file[0], encoding='latin-1')
        df_raw = synchronize_s_and_v_streams(df_s, df_v, max_tolerance_sec=0.05)

    df_50hz = resample_to_50hz(df_raw, target_freq_hz=target_freq_hz)
    df_features = extract_paper_features(df_50hz, window_size=window_size)
    return df_features


class LazySpeedSequenceDataset(Dataset):
    """
    Memory-Efficient PyTorch Dataset for vehicle speed sequence learning.
    Stores 2D feature matrices and computes 3D windows (T=200, 21) on-the-fly.
    
    Prevents cross-session boundary leakage by enforcing valid end indices per session block.
    """
    def __init__(
        self,
        session_dfs: List[pd.DataFrame],
        scaler: PaperMinMaxScaler,
        fit_scaler: bool = False,
        sequence_length: int = 200,
        stride: int = 1
    ):
        self.sequence_length = sequence_length
        self.stride = stride
        
        # Extract 21 feature matrix & target arrays per session
        self.feature_matrices = []
        self.target_arrays = []
        self.valid_indices = []  # List of (session_idx, end_sample_idx)
        
        # Prepare 2D matrices
        all_X_concat = []
        for s_idx, df in enumerate(session_dfs):
            X_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
            if len(X_cols) != 21:
                raise ValueError(f"Expected 21 features, got {len(X_cols)}")
                
            X_data = df[X_cols].values.astype(np.float32)
            y_data = df['reference_speed'].values.astype(np.float32)
            
            all_X_concat.append(X_data)
            self.feature_matrices.append(X_data)
            self.target_arrays.append(y_data)
            
            # Generate valid sequence end indices strictly within this session
            num_samples = len(df)
            for end_idx in range(sequence_length - 1, num_samples, stride):
                self.valid_indices.append((s_idx, end_idx))
                
        # Fit scaler ONLY if requested (Training split)
        if fit_scaler:
            X_flat = np.concatenate(all_X_concat, axis=0)
            scaler.fit(X_flat)
            
        self.scaler = scaler
        
        # Apply scaling to feature matrices in memory
        for s_idx in range(len(self.feature_matrices)):
            self.feature_matrices[s_idx] = scaler.transform(self.feature_matrices[s_idx])

    def __len__(self) -> int:
        return len(self.valid_indices)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        s_idx, end_idx = self.valid_indices[idx]
        start_idx = end_idx - self.sequence_length + 1
        
        # Slice T=200 window from session feature matrix
        X_win = self.feature_matrices[s_idx][start_idx : end_idx + 1]
        y_val = self.target_arrays[s_idx][end_idx]
        
        return torch.from_numpy(X_win).float(), torch.tensor([y_val], dtype=torch.float32)


def build_paper_dataloaders(
    batch_size: int = 32,
    sequence_length: int = 200,
    stride: int = 1,
    num_workers: int = 0
) -> Tuple[DataLoader, DataLoader, DataLoader, PaperMinMaxScaler, Dict]:
    """
    Builds reproducible PyTorch DataLoaders for Train, Val, and Test splits.
    
    Data Leakage Safeguards Enforced:
    1. MinMax Scaler is fitted ONLY on Training set windows (X_train).
    2. Scaler bounds are applied to Val (X_val) and Test (X_test) without updating bounds.
    3. Session S3c is created for final testing ONLY and must not be used for model tuning.
    """
    # Load dataframes
    train_dfs = [load_and_preprocess_session(sid, window_size=sequence_length) for sid in TRAIN_SESSIONS]
    val_dfs = [load_and_preprocess_session(sid, window_size=sequence_length) for sid in VAL_SESSIONS]
    test_dfs = [load_and_preprocess_session(sid, window_size=sequence_length) for sid in TEST_SESSIONS]
    
    # Initialize scaler
    scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
    
    # Construct Lazy PyTorch Datasets
    train_dataset = LazySpeedSequenceDataset(train_dfs, scaler=scaler, fit_scaler=True, sequence_length=sequence_length, stride=stride)
    val_dataset = LazySpeedSequenceDataset(val_dfs, scaler=scaler, fit_scaler=False, sequence_length=sequence_length, stride=stride)
    test_dataset = LazySpeedSequenceDataset(test_dfs, scaler=scaler, fit_scaler=False, sequence_length=sequence_length, stride=stride)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=False, num_workers=num_workers)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, drop_last=False, num_workers=num_workers)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, drop_last=False, num_workers=num_workers)
    
    meta_info = {
        'train_samples': len(train_dataset),
        'val_samples': len(val_dataset),
        'test_samples': len(test_dataset),
        'input_shape': (sequence_length, 21),
        'target_shape': (1,),
        'feature_columns': FEATURE_COLUMNS
    }
    
    return train_loader, val_loader, test_loader, scaler, meta_info
