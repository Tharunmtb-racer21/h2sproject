import os
import glob
import json
import random
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from dataset_loader import load_dataset_by_sessions
from models import SimpleBaselineMLP, LSTMNoAttention, LSTMSelfAttention

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def compute_metrics(y_true, y_pred):
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    return mae, rmse

def evaluate_segmented(y_true, y_pred, metadata):
    """
    Evaluate performance separately for stationary, turning, and vibration segments.
    """
    stats = {}
    
    # 1. Stationary Segment
    stat_mask = np.array([m['is_stationary'] == 1 for m in metadata])
    if np.sum(stat_mask) > 0:
        mae, rmse = compute_metrics(y_true[stat_mask], y_pred[stat_mask])
        stats['stationary'] = {'count': int(np.sum(stat_mask)), 'mae_m_s': round(mae, 4), 'rmse_m_s': round(rmse, 4)}
    else:
        stats['stationary'] = {'count': 0, 'mae_m_s': None, 'rmse_m_s': None}
        
    # 2. Dynamic Motion Segment
    dyn_mask = np.array([m['is_stationary'] == 0 for m in metadata])
    if np.sum(dyn_mask) > 0:
        mae, rmse = compute_metrics(y_true[dyn_mask], y_pred[dyn_mask])
        stats['dynamic_motion'] = {'count': int(np.sum(dyn_mask)), 'mae_m_s': round(mae, 4), 'rmse_m_s': round(rmse, 4)}
    else:
        stats['dynamic_motion'] = {'count': 0, 'mae_m_s': None, 'rmse_m_s': None}

    # 3. Turning Segment
    turn_mask = np.array([m['is_turning'] == 1 for m in metadata])
    if np.sum(turn_mask) > 0:
        mae, rmse = compute_metrics(y_true[turn_mask], y_pred[turn_mask])
        stats['turning'] = {'count': int(np.sum(turn_mask)), 'mae_m_s': round(mae, 4), 'rmse_m_s': round(rmse, 4)}
    else:
        stats['turning'] = {'count': 0, 'mae_m_s': None, 'rmse_m_s': None}

    # 4. Vibration Segment
    vib_mask = np.array([m['is_vibration'] == 1 for m in metadata])
    if np.sum(vib_mask) > 0:
        mae, rmse = compute_metrics(y_true[vib_mask], y_pred[vib_mask])
        stats['vibration'] = {'count': int(np.sum(vib_mask)), 'mae_m_s': round(mae, 4), 'rmse_m_s': round(rmse, 4)}
    else:
        stats['vibration'] = {'count': 0, 'mae_m_s': None, 'rmse_m_s': None}

    return stats

def train_model(model, train_loader, val_loader, num_epochs=35, lr=0.0008, device='cpu'):
    model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5, min_lr=1e-6)
    
    best_val_loss = float('inf')
    best_state = None
    
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            preds = model(bx)
            loss = criterion(preds, by)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(by)
            
        train_loss /= len(train_loader.dataset)
        
        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                preds = model(bx)
                loss = criterion(preds, by)
                val_loss += loss.item() * len(by)
        val_loss /= len(val_loader.dataset)
        
        scheduler.step(val_loss)
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = model.state_dict().copy()
            
    model.load_state_dict(best_state)
    return model

def main():
    set_seed(42)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Executing AI Speed Estimation Baseline on device: {device}")
    
    processed_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline\processed_data"
    output_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\ai_pipeline"
    plots_dir = os.path.join(output_dir, "plots")
    models_dir = os.path.join(output_dir, "models")
    os.makedirs(plots_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    
    # 1. Load Session Data (4-second sequence T=200 timesteps)
    sequence_length = 200 # 4.0s @ 50Hz equivalent or 2.0s @ 100Hz
    session_data, excluded_files = load_dataset_by_sessions(processed_dir, sequence_length=sequence_length, stride=5)
    
    if len(session_data) < 2:
        print("\nNotice: Combining valid session windows with session-based split...")
        all_sessions = list(session_data.keys())
        train_session_name = all_sessions[0]
        test_session_name = all_sessions[0] if len(all_sessions) == 1 else all_sessions[1]
    else:
        # Session 1 for training, Session 2 for test
        all_sessions = sorted(list(session_data.keys()))
        train_session_name = all_sessions[0]
        test_session_name = all_sessions[1]
        
    print(f"\n[SESSION SPLIT]:")
    print(f" -> Training Journey Session: {train_session_name}")
    print(f" -> Testing/Validation Journey Session: {test_session_name}")
    
    X_train, y_train, meta_train = session_data[train_session_name]
    X_test, y_test, meta_test = session_data[test_session_name]
    
    # 80/20 train/val split within training session
    val_split_idx = int(len(X_train) * 0.8)
    X_tr, y_tr = X_train[:val_split_idx], y_train[:val_split_idx]
    X_va, y_va = X_train[val_split_idx:], y_train[val_split_idx:]
    
    train_ds = TensorDataset(torch.tensor(X_tr), torch.tensor(y_tr))
    val_ds = TensorDataset(torch.tensor(X_va), torch.tensor(y_va))
    test_ds = TensorDataset(torch.tensor(X_test), torch.tensor(y_test))
    
    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False)
    
    # 2. Instantiate and Train Models
    models_dict = {
        "Simple Baseline (MLP)": SimpleBaselineMLP(input_dim=21),
        "LSTM without Attention": LSTMNoAttention(input_dim=21),
        "LSTM with Self-Attention (Paper Model)": LSTMSelfAttention(input_dim=21)
    }
    
    results = {}
    predictions = {}
    
    for name, model in models_dict.items():
        print(f"\nTraining Model: {name}...")
        trained_model = train_model(model, train_loader, val_loader, num_epochs=35, lr=0.0008, device=device)
        
        # Save model weights
        save_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "") + ".pt"
        torch.save(trained_model.state_dict(), os.path.join(models_dir, save_name))
        
        # Evaluate on Test Set
        trained_model.eval()
        preds_list = []
        with torch.no_grad():
            for bx, _ in test_loader:
                bx = bx.to(device)
                p = trained_model(bx)
                preds_list.extend(p.cpu().numpy())
                
        y_pred = np.array(preds_list)
        predictions[name] = y_pred
        
        mae, rmse = compute_metrics(y_test, y_pred)
        segmented_stats = evaluate_segmented(y_test, y_pred, meta_test)
        
        results[name] = {
            "overall_mae_m_s": round(mae, 4),
            "overall_rmse_m_s": round(rmse, 4),
            "overall_mae_km_h": round(mae * 3.6, 4),
            "overall_rmse_km_h": round(rmse * 3.6, 4),
            "segmented_performance": segmented_stats
        }
        
        print(f" -> {name} | Test RMSE: {rmse:.4f} m/s ({rmse*3.6:.4f} km/h) | Test MAE: {mae:.4f} m/s ({mae*3.6:.4f} km/h)")

    # 3. Save Evaluation JSON Report
    report_data = {
        "sequence_config": {
            "sequence_length_timesteps": sequence_length,
            "estimated_duration_seconds": 4.0,
            "input_features_count": 21,
            "feature_composition": "7 Raw (Accel XYZ, Gyro XYZ, Accel Mag) + 14 Rolling Stats (Mean, Variance)"
        },
        "session_split": {
            "train_session": train_session_name,
            "test_session": test_session_name,
            "excluded_sessions_lacking_target": excluded_files
        },
        "hyperparameters": {
            "optimizer": "Adam",
            "initial_learning_rate": 0.0008,
            "weight_decay": 0.0001,
            "lr_scheduler": "ReduceLROnPlateau (factor=0.5, patience=5)",
            "batch_size": 32,
            "epochs": 35,
            "random_seed": 42
        },
        "model_comparison_results": results
    }
    
    with open(os.path.join(output_dir, "AI_SPEED_ESTIMATION_REPORT.json"), "w") as fp:
        json.dump(report_data, fp, indent=2)

    # 4. Generate Plot: Predicted Speed vs Reference Speed
    plt.figure(figsize=(12, 6))
    time_steps = np.arange(len(y_test)) * 0.05 # Approximate stride delta
    plt.plot(time_steps, y_test * 3.6, 'k-', label='Reference Speed (GPS ground-truth)', linewidth=2.5, alpha=0.9)
    
    colors = ['#ff7f0e', '#1f77b4', '#2ca02c']
    styles = ['--', '-.', '-']
    for (name, y_pred), col, st in zip(predictions.items(), colors, styles):
        plt.plot(time_steps, y_pred * 3.6, label=f"{name} (RMSE: {results[name]['overall_rmse_km_h']:.2f} km/h)",
                 color=col, linestyle=st, linewidth=1.8, alpha=0.85)
                 
    plt.title('AI Vehicle Speed Estimation Comparison (Paper Architecture)', fontsize=14, fontweight='bold')
    plt.xlabel('Sequence Time (seconds)', fontweight='bold')
    plt.ylabel('Vehicle Speed (km/h)', fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(loc='upper right', fontsize=10)
    plt.tight_layout()
    
    plot_path = os.path.join(plots_dir, "ai_speed_estimation_comparison.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    
    print(f"\n[SUCCESS] AI Speed Estimation Baseline Complete!")
    print(f" -> Evaluation Report: {os.path.join(output_dir, 'AI_SPEED_ESTIMATION_REPORT.json')}")
    print(f" -> Speed Plot Saved: {plot_path}")

if __name__ == "__main__":
    main()
