"""
paper_baseline/tests/test_pipeline_gate.py
SIH26168 Phase 3 Execution Gate Verification Test Suite.

Verifies:
1. Dataset construction & windowing sanity checks (Phase 3B).
2. Data leakage safeguards (Phase 3B).
3. Model implementations & trainable parameter counts (Phase 3C).
4. Forward pass, loss computation, backward pass, and optimizer steps (Phase 3D).
"""

import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from paper_baseline.dataset import (
    load_and_preprocess_session,
    LazySpeedSequenceDataset,
    build_paper_dataloaders,
    TRAIN_SESSIONS,
    VAL_SESSIONS,
    TEST_SESSIONS
)
from paper_baseline.feature_extraction import PaperMinMaxScaler, FEATURE_COLUMNS
from paper_baseline.models import (
    LSTMSelfAttention,
    LSTMNoAttention,
    SimpleBaselineMLP,
    count_parameters,
    get_model_summary
)


def test_dataset_window_counts_and_shapes():
    """Phase 3B: Verify session window counts, input shape (B, 200, 21), and target shape (B, 1)."""
    train_loader, val_loader, test_loader, scaler, meta = build_paper_dataloaders(
        batch_size=32,
        sequence_length=200,
        stride=1
    )
    
    assert meta['train_samples'] > 0, "Train dataset contains 0 samples!"
    assert meta['val_samples'] > 0, "Val dataset contains 0 samples!"
    assert meta['test_samples'] > 0, "Test dataset contains 0 samples!"
    
    # Verify DataLoader iteration shapes
    X_batch, y_batch = next(iter(train_loader))
    assert X_batch.shape == (32, 200, 21), f"Expected (32, 200, 21), got {X_batch.shape}"
    assert y_batch.shape == (32, 1), f"Expected (32, 1), got {y_batch.shape}"
    
    # Check for NaN / Inf
    assert not torch.isnan(X_batch).any(), "NaN detected in training input tensor!"
    assert not torch.isinf(X_batch).any(), "Inf detected in training input tensor!"
    assert not torch.isnan(y_batch).any(), "NaN detected in training target tensor!"
    assert not torch.isinf(y_batch).any(), "Inf detected in training target tensor!"


def test_data_leakage_safeguards():
    """Phase 3B: Verify strict anti-leakage safeguards across scaler and session splits."""
    df_m = load_and_preprocess_session('IOVNBD_M')
    df_s3a = load_and_preprocess_session('IOVNBD_S3a')
    
    scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
    ds_train = LazySpeedSequenceDataset([df_m], scaler=scaler, fit_scaler=True)
    
    m_min_bounds = scaler.min_val.copy()
    m_max_bounds = scaler.max_val.copy()
    
    # Transform S3a without altering scaler bounds
    _ = LazySpeedSequenceDataset([df_s3a], scaler=scaler, fit_scaler=False)
    
    np.testing.assert_array_equal(scaler.min_val, m_min_bounds, err_msg="Scaler min bounds altered during val transform!")
    np.testing.assert_array_equal(scaler.max_val, m_max_bounds, err_msg="Scaler max bounds altered during val transform!")
    
    assert 'reference_speed' not in FEATURE_COLUMNS, "Target label reference_speed found inside feature matrix!"


def test_model_parameter_counts():
    """Phase 3C: Confirm model architectures and trainable parameter counts."""
    m1 = LSTMSelfAttention(input_dim=21, hidden_dim=128, num_layers=2)
    m2 = LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)
    m3 = SimpleBaselineMLP(input_dim=21, hidden_dim=128)
    
    p1 = count_parameters(m1)
    p2 = count_parameters(m2)
    p3 = count_parameters(m3)
    
    assert p1 > 0, "LSTMSelfAttention parameter count is 0"
    assert p2 > 0, "LSTMNoAttention parameter count is 0"
    assert p3 > 0, "SimpleBaselineMLP parameter count is 0"
    
    assert p1 > p2, f"LSTMSelfAttention params ({p1}) should exceed LSTMNoAttention ({p2}) due to attention module"


def test_forward_and_backward_passes():
    """Phase 3D: Test real training batch forward pass, loss, backward pass, and optimizer step for all 3 models."""
    train_loader, _, _, _, _ = build_paper_dataloaders(batch_size=32, sequence_length=200)
    X_batch, y_batch = next(iter(train_loader))
    
    models = {
        'LSTMSelfAttention': LSTMSelfAttention(input_dim=21, hidden_dim=128, num_layers=2),
        'LSTMNoAttention': LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2),
        'SimpleBaselineMLP': SimpleBaselineMLP(input_dim=21, hidden_dim=128)
    }
    
    criterion = nn.MSELoss()
    
    for name, model in models.items():
        model.train()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        optimizer.zero_grad()
        
        # Forward pass
        pred = model(X_batch)
        assert pred.shape == (32, 1), f"{name} output shape is {pred.shape}, expected (32, 1)"
        assert not torch.isnan(pred).any(), f"NaN in {name} predictions!"
        assert not torch.isinf(pred).any(), f"Inf in {name} predictions!"
        
        # Loss computation
        loss = criterion(pred, y_batch)
        assert not torch.isnan(loss), f"NaN loss in {name}!"
        assert loss.item() > 0.0, f"Loss is non-positive in {name}"
        
        # Backward pass
        loss.backward()
        
        # Check gradients
        for param_name, param in model.named_parameters():
            if param.requires_grad:
                assert param.grad is not None, f"Gradient is None for {param_name} in {name}"
                assert not torch.isnan(param.grad).any(), f"NaN gradient in {param_name} of {name}"
                assert not torch.isinf(param.grad).any(), f"Inf gradient in {param_name} of {name}"
                
        # Optimizer step
        optimizer.step()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
