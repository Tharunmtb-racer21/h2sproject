"""
paper_baseline/models.py
SIH26168 - Paper-Aligned Deep Learning Speed Estimation Models (Shin et al., 2025)

Implements 3 architectures:
1. LSTMSelfAttention: LSTM encoder + temporal self-attention + linear regressor.
2. LSTMNoAttention: Standard LSTM encoder + linear regressor.
3. SimpleBaselineMLP: Non-recurrent MLP baseline for comparative ablation.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple


class TemporalSelfAttention(nn.Module):
    """
    Temporal Self-Attention mechanism over sequence hidden states H of shape (B, T, D).
    Calculates dynamic attention weights across sequence time steps T=200.
    """
    def __init__(self, embed_dim: int):
        super().__init__()
        self.embed_dim = embed_dim
        self.query = nn.Linear(embed_dim, embed_dim)
        self.key = nn.Linear(embed_dim, embed_dim)
        self.value = nn.Linear(embed_dim, embed_dim)
        self.scale = 1.0 / math.sqrt(embed_dim)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # x shape: (B, T, D)
        Q = self.query(x)  # (B, T, D)
        K = self.key(x)    # (B, T, D)
        V = self.value(x)  # (B, T, D)

        attn_scores = torch.bmm(Q, K.transpose(1, 2)) * self.scale  # (B, T, T)
        attn_weights = F.softmax(attn_scores, dim=-1)               # (B, T, T)
        context = torch.bmm(attn_weights, V)                        # (B, T, D)
        
        # Aggregate across time (average attention-weighted representations)
        context_pooled = torch.mean(context, dim=1)                 # (B, D)
        return context_pooled, attn_weights


class LSTMSelfAttention(nn.Module):
    """
    Paper-Aligned Model 1: LSTM with Temporal Self-Attention.
    
    Specifications:
    - Input: (Batch, T=200, Input_Dim=21)
    - LSTM: 2 layers, hidden_dim=128, dropout=0.2 (Implementation assumption - not explicitly specified in source)
    - Attention: Temporal Self-Attention over T=200 hidden states
    - Regressor: Linear(128, 64) -> ReLU -> Dropout(0.2) -> Linear(64, 1)
    """
    def __init__(
        self,
        input_dim: int = 21,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.attention = TemporalSelfAttention(embed_dim=hidden_dim)
        self.regressor = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, 21)
        lstm_out, _ = self.lstm(x)  # lstm_out: (B, T, 128)
        context, _ = self.attention(lstm_out)  # context: (B, 128)
        out = self.regressor(context)  # out: (B, 1)
        return out


class LSTMNoAttention(nn.Module):
    """
    Paper-Aligned Model 2: Standard LSTM without Attention.
    
    Specifications:
    - Input: (Batch, T=200, Input_Dim=21)
    - LSTM: 2 layers, hidden_dim=128, dropout=0.2
    - Takes final time-step hidden state h_T
    - Regressor: Linear(128, 64) -> ReLU -> Dropout(0.2) -> Linear(64, 1)
    """
    def __init__(
        self,
        input_dim: int = 21,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.regressor = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, 21)
        lstm_out, (h_n, c_n) = self.lstm(x)  # lstm_out: (B, T, 128)
        final_state = lstm_out[:, -1, :]      # (B, 128)
        out = self.regressor(final_state)     # (B, 1)
        return out


class SimpleBaselineMLP(nn.Module):
    """
    Paper-Aligned Model 3: Simple Baseline MLP.
    
    Specifications:
    - Input: (Batch, T=200, Input_Dim=21)
    - Temporal Pooling: Global Average Pooling across T=200 -> (Batch, 21)
    - Regressor: Linear(21, 128) -> ReLU -> Dropout(0.2) -> Linear(128, 64) -> ReLU -> Linear(64, 1)
    """
    def __init__(
        self,
        input_dim: int = 21,
        hidden_dim: int = 128,
        dropout: float = 0.2
    ):
        super().__init__()
        self.input_dim = input_dim
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, 21)
        x_pooled = torch.mean(x, dim=1)  # (B, 21)
        out = self.net(x_pooled)         # (B, 1)
        return out


def count_parameters(model: nn.Module) -> int:
    """Counts total trainable parameters in a PyTorch module."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def get_model_summary(model: nn.Module, model_name: str) -> Dict:
    """Returns metadata dictionary summarizing model architecture and parameter count."""
    num_params = count_parameters(model)
    return {
        'name': model_name,
        'class': model.__class__.__name__,
        'trainable_parameters': num_params,
        'formatted_parameters': f"{num_params:,}"
    }
