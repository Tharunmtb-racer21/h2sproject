"""
paper_baseline/evaluate_exp6.py
Offline Evaluation Script for Experiment 6: AI Speed Model V2 (Bounded Absolute Speed Ratio)

Evaluates Model V2 against Ground-Truth Speed and Constant-Speed Persistence Baseline.
Calculates:
- Speed MAE and RMSE
- Mean Absolute Ratio Error (MARE)
- Low-speed (<3 m/s) performance
- Dynamic speed (>=3 m/s) performance
- Held-out test session metrics (IOVNBD_S3c and IOVNBD_S3a)
- Prediction range and out-of-range frequency
"""

import os
import json
import torch
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader

from paper_baseline.feature_extraction import PaperMinMaxScaler
from paper_baseline.train_exp6 import (
    LSTMAbsoluteSpeedRatio, SpeedRatioSequenceDataset, preprocess_session_file,
    OUTPUT_DIR, DATA_DIR, TEST_SESSIONS, VAL_SESSIONS
)

EVAL_DIR = os.path.join(OUTPUT_DIR, "evaluation")

def run_offline_evaluation():
    os.makedirs(EVAL_DIR, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load scaler
    scaler_file = os.path.join(OUTPUT_DIR, "scaler_params.json")
    with open(scaler_file, "r") as f:
        scaler_params = json.load(f)
    
    scaler = PaperMinMaxScaler()
    scaler.min_val = np.array(scaler_params["min_val"], dtype=np.float32)
    scaler.max_val = np.array(scaler_params["max_val"], dtype=np.float32)
    scaler.is_fitted = True

    # Load Model V2
    model = LSTMAbsoluteSpeedRatio(input_dim=21, hidden_dim=128, num_layers=2).to(device)
    model_path = os.path.join(OUTPUT_DIR, "best_model.pt")
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    print("Model V2 loaded successfully.")

    # 1. Load Test Sessions (IOVNBD_S3c)
    test_dfs = [preprocess_session_file(sid) for sid in TEST_SESSIONS if os.path.exists(os.path.join(DATA_DIR, f"{sid}_standardized.csv"))]
    test_ds = SpeedRatioSequenceDataset(test_dfs, scaler=scaler, fit_scaler=False, sequence_length=200, stride=5)
    test_loader = DataLoader(test_ds, batch_size=256, shuffle=False)

    predictions = []
    ground_truth_ratios = []

    with torch.no_grad():
        for X_b, y_b in test_loader:
            X_b = X_b.to(device)
            r_pred = model(X_b).cpu().numpy().flatten()
            predictions.extend(r_pred)
            ground_truth_ratios.extend(y_b.numpy().flatten())

    predictions = np.array(predictions)
    ground_truth_ratios = np.array(ground_truth_ratios)

    # Reconstruct speeds using v_anchor
    v_anchors = []
    gt_speeds = []
    for df in test_dfs:
        v_data = df['reference_speed'].values
        num_samples = len(df)
        for end_idx in range(199, num_samples, 5):
            start_idx = end_idx - 199
            v_anc = max(float(v_data[start_idx]), 1.0)
            v_t = float(v_data[end_idx])
            v_anchors.append(v_anc)
            gt_speeds.append(v_t)

    v_anchors = np.array(v_anchors[:len(predictions)])
    gt_speeds = np.array(gt_speeds[:len(predictions)])

    pred_speeds_ai = predictions * v_anchors
    pred_speeds_persistence = v_anchors  # Constant speed persistence

    # Metrics computation
    mae_ai = float(np.mean(np.abs(pred_speeds_ai - gt_speeds)))
    rmse_ai = float(np.sqrt(np.mean((pred_speeds_ai - gt_speeds)**2)))
    
    mae_pers = float(np.mean(np.abs(pred_speeds_persistence - gt_speeds)))
    rmse_pers = float(np.sqrt(np.mean((pred_speeds_persistence - gt_speeds)**2)))

    mare = float(np.mean(np.abs(predictions - ground_truth_ratios)))

    # Low speed vs dynamic speed slices
    low_speed_mask = gt_speeds < 3.0
    dynamic_mask = ~low_speed_mask

    mae_ai_low = float(np.mean(np.abs(pred_speeds_ai[low_speed_mask] - gt_speeds[low_speed_mask]))) if np.sum(low_speed_mask) > 0 else 0.0
    mae_pers_low = float(np.mean(np.abs(pred_speeds_persistence[low_speed_mask] - gt_speeds[low_speed_mask]))) if np.sum(low_speed_mask) > 0 else 0.0

    mae_ai_dyn = float(np.mean(np.abs(pred_speeds_ai[dynamic_mask] - gt_speeds[dynamic_mask]))) if np.sum(dynamic_mask) > 0 else 0.0
    mae_pers_dyn = float(np.mean(np.abs(pred_speeds_persistence[dynamic_mask] - gt_speeds[dynamic_mask]))) if np.sum(dynamic_mask) > 0 else 0.0

    # Range and out-of-range checks
    min_pred, max_pred = float(np.min(predictions)), float(np.max(predictions))
    out_of_range_count = int(np.sum((predictions < 0.0) | (predictions > 3.0)))

    results = {
        "model_name": "Exp_6_LSTM_AbsoluteSpeedRatio",
        "test_session": "IOVNBD_S3c",
        "best_train_mse": float(checkpoint.get("train_loss", 0.0)),
        "best_val_mse": float(checkpoint.get("val_loss", 0.0)),
        "total_windows": len(predictions),
        "ratio_prediction_range": [min_pred, max_pred],
        "out_of_range_frequency": out_of_range_count,
        "mean_absolute_ratio_error": mare,
        "ai_speed_mae_ms": mae_ai,
        "ai_speed_rmse_ms": rmse_ai,
        "persistence_speed_mae_ms": mae_pers,
        "persistence_speed_rmse_ms": rmse_pers,
        "low_speed_mae_ms": {
            "ai_ratio": mae_ai_low,
            "persistence": mae_pers_low
        },
        "dynamic_speed_mae_ms": {
            "ai_ratio": mae_ai_dyn,
            "persistence": mae_pers_dyn
        }
    }

    report_path = os.path.join(EVAL_DIR, "offline_metrics.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n=======================================================")
    print("MODEL V2 OFFLINE EVALUATION RESULTS")
    print("=======================================================")
    print(f"Test Session: IOVNBD_S3c ({len(predictions)} windows)")
    print(f"Best Val MSE: {checkpoint.get('val_loss', 0.0):.6f}")
    print(f"Ratio Prediction Range: [{min_pred:.4f}, {max_pred:.4f}] (Bounded [0.0, 3.0])")
    print(f"Out of Range Frequency: {out_of_range_count}")
    print(f"Mean Absolute Ratio Error (MARE): {mare:.4f}")
    print(f"AI Speed MAE: {mae_ai:.4f} m/s | Persistence Speed MAE: {mae_pers:.4f} m/s")
    print(f"AI Speed RMSE: {rmse_ai:.4f} m/s | Persistence Speed RMSE: {rmse_pers:.4f} m/s")
    print(f"Low Speed (<3 m/s) MAE -> AI: {mae_ai_low:.4f} m/s | Pers: {mae_pers_low:.4f} m/s")
    print(f"Dynamic Speed (>=3 m/s) MAE -> AI: {mae_ai_dyn:.4f} m/s | Pers: {mae_pers_dyn:.4f} m/s")
    print(f"Metrics saved to {report_path}")

if __name__ == "__main__":
    run_offline_evaluation()
