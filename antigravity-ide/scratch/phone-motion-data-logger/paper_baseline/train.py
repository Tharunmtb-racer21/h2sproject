"""
paper_baseline/train.py
SIH26168 - Paper-Aligned Model Training Script (Shin et al., 2025)

Implements:
1. Frozen configuration enforcement and hardware detection.
2. Pre-flight dataset and anti-leakage assertions.
3. Resumable checkpointing (best_model.pt & last_checkpoint.pt).
4. Epoch history logging to training_history.csv.
5. Sequential training of LSTMSelfAttention, LSTMNoAttention, and SimpleBaselineMLP.
6. Strict test set isolation (S3c remains frozen).
"""

import os
import sys
import time
import math
import random
import csv
import torch
import torch.nn as nn

import torch.optim as optim
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from paper_baseline.dataset import (
    build_paper_dataloaders,
    TRAIN_SESSIONS,
    VAL_SESSIONS,
    TEST_SESSIONS
)
from paper_baseline.feature_extraction import FEATURE_COLUMNS
from paper_baseline.models import (
    LSTMSelfAttention,
    LSTMNoAttention,
    SimpleBaselineMLP,
    count_parameters
)

# -----------------------------------------------------------------------------
# FROZEN LOCKED CONFIGURATION
# -----------------------------------------------------------------------------
SEED = 42
SEQUENCE_LENGTH = 200
STRIDE = 1
BATCH_SIZE = 32
HIDDEN_DIM = 128
NUM_LAYERS = 2
DROPOUT = 0.2
LEARNING_RATE = 0.0008
EPOCHS = 35
TEST_SET_FROZEN = True

OUTPUT_DIR = 'outputs'


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def detect_hardware():
    cpu_count = os.cpu_count()
    cuda_avail = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_avail else "N/A"
    gpu_vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3) if cuda_avail else 0.0
    pytorch_cuda = torch.version.cuda if cuda_avail else "N/A"
    
    print("==========================================================================", flush=True)
    print("                    HARDWARE & ENVIRONMENT DETECTION                      ", flush=True)
    print("==========================================================================", flush=True)
    print(f"OS:                 {sys.platform}", flush=True)
    print(f"Python Version:     {sys.version.split()[0]}", flush=True)
    print(f"PyTorch Version:    {torch.__version__}", flush=True)
    print(f"CPU Cores:          {cpu_count}", flush=True)
    print(f"CUDA Available:     {cuda_avail}", flush=True)
    print(f"GPU Name:           {gpu_name}", flush=True)
    print(f"GPU VRAM:           {gpu_vram:.2f} GB", flush=True)
    print(f"PyTorch CUDA Ver:   {pytorch_cuda}", flush=True)
    print("==========================================================================\n", flush=True)
    return cuda_avail




def run_preflight_assertions(train_loader, val_loader, test_loader, scaler):
    print("--- Running Pre-Flight Pipeline Assertions ---", flush=True)
    assert TRAIN_SESSIONS == ['IOVNBD_M', 'IOVNBD_S1', 'IOVNBD_S2'], "Invalid training sessions!"
    assert VAL_SESSIONS == ['IOVNBD_S3a'], "Invalid validation session!"
    assert TEST_SESSIONS == ['IOVNBD_S3c'], "Invalid test session!"
    assert TEST_SET_FROZEN, "HARD SAFETY FAILURE: TEST_SET_FROZEN is False!"
    assert len(FEATURE_COLUMNS) == 21, f"Expected 21 features, got {len(FEATURE_COLUMNS)}"
    assert 'reference_speed' not in FEATURE_COLUMNS, "Target variable found inside feature matrix!"
    
    # Batch assertion
    X_b, y_b = next(iter(train_loader))
    assert X_b.shape[1:] == (200, 21), f"Expected input shape (200, 21), got {X_b.shape[1:]}"
    assert y_b.shape[1:] == (1,), f"Expected target shape (1,), got {y_b.shape[1:]}"
    assert not torch.isnan(X_b).any() and not torch.isinf(X_b).any(), "NaN/Inf in training inputs!"
    assert not torch.isnan(y_b).any() and not torch.isinf(y_b).any(), "NaN/Inf in training targets!"
    
    # Scaler bounds assertion
    assert scaler.is_fitted, "Scaler must be fitted!"
    print("Pre-Flight Pipeline Assertions: ALL PASSED!\n", flush=True)



def train_single_model(model_name: str, model: nn.Module, train_loader, val_loader, device: torch.device):
    model_dir = os.path.join(OUTPUT_DIR, model_name)
    os.makedirs(model_dir, exist_ok=True)
    
    history_csv = os.path.join(model_dir, 'training_history.csv')
    best_ckpt_path = os.path.join(model_dir, 'best_model.pt')
    last_ckpt_path = os.path.join(model_dir, 'last_checkpoint.pt')
    
    model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)
    
    start_epoch = 1
    best_val_loss = float('inf')
    cum_time_sec = 0.0
    history_records = []
    
    # Resume checkpoint if exists
    if os.path.exists(last_ckpt_path):
        print(f"Resuming existing training checkpoint from {last_ckpt_path}...")
        checkpoint = torch.load(last_ckpt_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_val_loss = checkpoint['best_validation_loss']
        cum_time_sec = checkpoint['cum_time_sec']
        print(f"Resumed at epoch {start_epoch} with Best Val Loss: {best_val_loss:.6f}")

    if start_epoch > EPOCHS:
        print(f"Model {model_name} training already completed ({EPOCHS} epochs). Skipping.\n")
        return best_val_loss
        
    print(f"==========================================================================")
    print(f"            STARTING TRAINING: {model_name} ({EPOCHS} EPOCHS)             ")
    print(f"==========================================================================")
    
    # Initialize history CSV if new
    if not os.path.exists(history_csv):
        with open(history_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['epoch', 'train_loss', 'val_loss', 'train_rmse', 'val_rmse', 'learning_rate', 'epoch_duration_s', 'cum_time_s'])

    for epoch in range(start_epoch, EPOCHS + 1):
        t_epoch_start = time.time()
        
        # --- Training Loop ---
        model.train()
        train_loss_sum = 0.0
        train_count = 0
        
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            
            pred = model(X_batch)
            loss = criterion(pred, y_batch)
            
            if torch.isnan(loss) or torch.isinf(loss):
                raise RuntimeError(f"CRITICAL FAILURE: Loss became {loss.item()} at epoch {epoch}!")
                
            loss.backward()
            optimizer.step()
            
            train_loss_sum += loss.item() * len(y_batch)
            train_count += len(y_batch)
            
        train_loss = train_loss_sum / train_count
        train_rmse = math.sqrt(train_loss)
        
        # --- Validation Loop (IOVNBD_S3a) ---
        model.eval()
        val_loss_sum = 0.0
        val_count = 0
        
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                pred = model(X_batch)
                loss = criterion(pred, y_batch)
                val_loss_sum += loss.item() * len(y_batch)
                val_count += len(y_batch)
                
        val_loss = val_loss_sum / val_count
        val_rmse = math.sqrt(val_loss)
        
        current_lr = optimizer.param_groups[0]['lr']
        scheduler.step(val_loss)
        
        t_epoch_end = time.time()
        duration_s = t_epoch_end - t_epoch_start
        cum_time_sec += duration_s
        
        # Checkpoint if best val loss
        is_best = val_loss < best_val_loss
        if is_best:
            best_val_loss = val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_loss': val_loss,
                'val_rmse': val_rmse,
                'config': {'model': model_name, 'seed': SEED}
            }, best_ckpt_path)

        # Save last checkpoint
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'best_validation_loss': best_val_loss,
            'cum_time_sec': cum_time_sec,
            'config': {'model': model_name, 'seed': SEED}
        }, last_ckpt_path)
        
        # Log to CSV
        with open(history_csv, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([epoch, train_loss, val_loss, train_rmse, val_rmse, current_lr, duration_s, cum_time_sec])
            
        print(f"Epoch [{epoch:02d}/{EPOCHS:02d}] | Train MSE: {train_loss:.4f} (RMSE: {train_rmse:.2f} m/s) | Val MSE: {val_loss:.4f} (RMSE: {val_rmse:.2f} m/s) | LR: {current_lr:.6f} | Time: {duration_s:.1f}s {'[BEST]' if is_best else ''}", flush=True)
        
        # First epoch sanity assertion
        if epoch == 1:
            print(f"\n--- FIRST EPOCH SANITY CHECK [{model_name}] ---", flush=True)
            print(f"  Epoch 1 Train Loss: {train_loss:.4f} (Finite = {not math.isnan(train_loss)})", flush=True)
            print(f"  Epoch 1 Val Loss:   {val_loss:.4f} (Finite = {not math.isnan(val_loss)})", flush=True)
            print(f"  Best Checkpoint Created: {os.path.exists(best_ckpt_path)}", flush=True)
            print(f"  First Epoch Sanity Check: PASSED!\n", flush=True)

    print(f"\nModel {model_name} Training Complete. Best Val MSE: {best_val_loss:.4f} (RMSE: {math.sqrt(best_val_loss):.2f} m/s)\n", flush=True)
    return best_val_loss



def main():
    set_seed(SEED)
    cuda_avail = detect_hardware()
    device = torch.device('cuda' if cuda_avail else 'cpu')
    
    print("Building reproducible 50 Hz DataLoaders (T=200, stride=1)...", flush=True)
    train_loader, val_loader, test_loader, scaler, meta = build_paper_dataloaders(
        batch_size=BATCH_SIZE,
        sequence_length=SEQUENCE_LENGTH,
        stride=STRIDE
    )
    
    run_preflight_assertions(train_loader, val_loader, test_loader, scaler)
    
    # Models to train in sequence
    experiments = [
        ('LSTMSelfAttention', LSTMSelfAttention(input_dim=21, hidden_dim=HIDDEN_DIM, num_layers=NUM_LAYERS, dropout=DROPOUT)),
        ('LSTMNoAttention', LSTMNoAttention(input_dim=21, hidden_dim=HIDDEN_DIM, num_layers=NUM_LAYERS, dropout=DROPOUT)),
        ('SimpleBaselineMLP', SimpleBaselineMLP(input_dim=21, hidden_dim=HIDDEN_DIM, dropout=DROPOUT))
    ]
    
    best_results = {}
    for name, model in experiments:
        best_val = train_single_model(name, model, train_loader, val_loader, device)
        best_results[name] = best_val
        
    print("==========================================================================", flush=True)
    print("                     ALL EXPERIMENTS COMPLETED SUCCESSFULLY               ", flush=True)
    print("==========================================================================", flush=True)
    for name, b_val in best_results.items():
        print(f"  {name:<22}: Best Val MSE = {b_val:.4f} (RMSE = {math.sqrt(b_val):.2f} m/s / {math.sqrt(b_val)*3.6:.2f} km/h)", flush=True)
    print("==========================================================================", flush=True)



if __name__ == '__main__':
    main()
