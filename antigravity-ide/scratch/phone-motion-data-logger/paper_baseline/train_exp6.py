"""
paper_baseline/train_exp6.py
SIH26168 - Experiment 6: AI Speed Model V2 Using Bounded Absolute Speed Ratio

Target Formulation:
    r_t = clip( v_t / max(v_anchor, 1.0), 0.0, 3.0 )
    where v_anchor = v at window start index (t_start = t_end - 199)

Output Architecture:
    LSTMAbsoluteSpeedRatio (217,729 parameters)
    Output Head: 3.0 * torch.sigmoid( Linear(64, 1) )
"""

import os
import json
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from paper_baseline.feature_extraction import (
    extract_paper_features,
    PaperMinMaxScaler,
    FEATURE_COLUMNS
)

# Output Directory
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "Exp_6_LSTM_AbsoluteSpeedRatio"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "iovnbd_selected"))

TRAIN_SESSIONS = ['IOVNBD_M', 'IOVNBD_S1', 'IOVNBD_S2']
VAL_SESSIONS = ['IOVNBD_S3a']
TEST_SESSIONS = ['IOVNBD_S3c']


class LSTMAbsoluteSpeedRatio(nn.Module):
    """
    Model V2: Stacked LSTM with Bounded Absolute Speed Ratio Output Head [0.0, 3.0].
    """
    def __init__(self, input_dim: int = 21, hidden_dim: int = 128, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.fc1 = nn.Linear(hidden_dim, 64)
        self.relu = nn.ReLU()
        self.drop = nn.Dropout(dropout)
        self.out_head = nn.Linear(64, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, T=200, 21)
        lstm_out, _ = self.lstm(x)             # (B, T, 128)
        h_last = lstm_out[:, -1, :]            # (B, 128)
        feat = self.drop(self.relu(self.fc1(h_last))) # (B, 64)
        raw_logits = self.out_head(feat)       # (B, 1)
        r_pred = 3.0 * torch.sigmoid(raw_logits) # Bounded in [0.0, 3.0]
        return r_pred


class SpeedRatioSequenceDataset(Dataset):
    """
    Dataset slicing T=200 sliding windows and computing bounded speed ratio target r_t.
    """
    def __init__(self, session_dfs, scaler, fit_scaler=False, sequence_length=200, stride=5):
        self.sequence_length = sequence_length
        self.stride = stride
        
        self.feature_matrices = []
        self.ratio_targets = []
        self.valid_indices = []
        
        all_X_concat = []
        for s_idx, df in enumerate(session_dfs):
            X_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
            X_data = df[X_cols].values.astype(np.float32)
            v_data = df['reference_speed'].values.astype(np.float32)
            
            all_X_concat.append(X_data)
            self.feature_matrices.append(X_data)
            
            r_targets = np.zeros(len(df), dtype=np.float32)
            num_samples = len(df)
            for end_idx in range(sequence_length - 1, num_samples, stride):
                start_idx = end_idx - sequence_length + 1
                v_anchor = v_data[start_idx]
                v_target = v_data[end_idx]
                
                r_t = float(np.clip(v_target / max(v_anchor, 1.0), 0.0, 3.0))
                r_targets[end_idx] = r_t
                self.valid_indices.append((s_idx, end_idx))
                
            self.ratio_targets.append(r_targets)

        if fit_scaler:
            X_flat = np.concatenate(all_X_concat, axis=0)
            scaler.fit(X_flat)
            
        self.scaler = scaler
        for s_idx in range(len(self.feature_matrices)):
            self.feature_matrices[s_idx] = scaler.transform(self.feature_matrices[s_idx])

    def __len__(self):
        return len(self.valid_indices)

    def __getitem__(self, idx):
        s_idx, end_idx = self.valid_indices[idx]
        start_idx = end_idx - self.sequence_length + 1
        
        X_win = self.feature_matrices[s_idx][start_idx : end_idx + 1]
        r_target = self.ratio_targets[s_idx][end_idx]
        
        return torch.from_numpy(X_win).float(), torch.tensor([r_target], dtype=torch.float32)


def preprocess_session_file(session_id):
    path = os.path.join(DATA_DIR, f"{session_id}_standardized.csv")
    df_raw = pd.read_csv(path)
    df_feat = extract_paper_features(df_raw, window_size=200)
    return df_feat


def run_training_exp6(epochs=10, batch_size=128, lr=0.001):
    print("======================================================================", flush=True)
    print("STARTING EXPERIMENT 6: AI SPEED MODEL V2 (BOUNDED ABSOLUTE SPEED RATIO)", flush=True)
    print("======================================================================", flush=True)
    
    print("Preprocessing sessions...", flush=True)
    train_dfs = [preprocess_session_file(sid) for sid in TRAIN_SESSIONS if os.path.exists(os.path.join(DATA_DIR, f"{sid}_standardized.csv"))]
    val_dfs = [preprocess_session_file(sid) for sid in VAL_SESSIONS if os.path.exists(os.path.join(DATA_DIR, f"{sid}_standardized.csv"))]
    test_dfs = [preprocess_session_file(sid) for sid in TEST_SESSIONS if os.path.exists(os.path.join(DATA_DIR, f"{sid}_standardized.csv"))]
    
    scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
    train_ds = SpeedRatioSequenceDataset(train_dfs, scaler=scaler, fit_scaler=True, sequence_length=200, stride=5)
    val_ds = SpeedRatioSequenceDataset(val_dfs, scaler=scaler, fit_scaler=False, sequence_length=200, stride=5)
    test_ds = SpeedRatioSequenceDataset(test_dfs, scaler=scaler, fit_scaler=False, sequence_length=200, stride=5)
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)
    
    print(f"Dataset samples: Train={len(train_ds)}, Val={len(val_ds)}, Test={len(test_ds)}", flush=True)
    
    scaler_dict = {
        "min_val": scaler.min_val.tolist(),
        "max_val": scaler.max_val.tolist()
    }
    with open(os.path.join(OUTPUT_DIR, "scaler_params.json"), "w") as f:
        json.dump(scaler_dict, f, indent=2)
        
    model = LSTMAbsoluteSpeedRatio(input_dim=21, hidden_dim=128, num_layers=2, dropout=0.2)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model Parameters: {param_count:,}", flush=True)
    
    best_val_loss = float("inf")
    best_model_path = os.path.join(OUTPUT_DIR, "best_model.pt")
    
    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for X_b, y_b in train_loader:
            optimizer.zero_grad()
            y_pred = model(X_b)
            loss = criterion(y_pred, y_b)
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())
            
        model.eval()
        val_losses = []
        with torch.no_grad():
            for X_b, y_b in val_loader:
                y_pred = model(X_b)
                loss = criterion(y_pred, y_b)
                val_losses.append(loss.item())
                
        tr_loss = float(np.mean(train_losses))
        va_loss = float(np.mean(val_losses))
        
        print(f"Epoch {epoch:02d}/{epochs:02d} | Train MSE: {tr_loss:.6f} | Val MSE: {va_loss:.6f}", flush=True)
        
        if va_loss < best_val_loss:
            best_val_loss = va_loss
            ckpt = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_loss": va_loss,
                "train_loss": tr_loss,
                "target_type": "bounded_absolute_speed_ratio",
                "param_count": param_count
            }
            torch.save(ckpt, best_model_path)
            
    print(f"\n[OK] Model V2 training complete. Best Val Loss: {best_val_loss:.6f}", flush=True)
    print(f"Saved checkpoint to: {best_model_path}", flush=True)


if __name__ == "__main__":
    run_training_exp6(epochs=10, batch_size=128, lr=0.001)
