import torch
import torch.nn as nn
import torch.nn.functional as F

class SimpleBaselineMLP(nn.Module):
    """
    Model 1: Simple Baseline MLP operating on sequence-averaged statistical features.
    """
    def __init__(self, input_dim=21, hidden_dim=64):
        super(SimpleBaselineMLP, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, 32)
        self.out = nn.Linear(32, 1)

    def forward(self, x):
        # x shape: (B, T, D)
        # Average over sequence length T
        x_avg = torch.mean(x, dim=1) # (B, D)
        h1 = self.relu(self.fc1(x_avg))
        h2 = self.relu(self.fc2(h1))
        out = self.out(h2)
        return out.squeeze(-1)

class LSTMNoAttention(nn.Module):
    """
    Model 2: 2-Layer Stacked LSTM without attention.
    - 1st Layer: 64 hidden units
    - 2nd Layer: 32 hidden units
    - Temporal Mean Pooling -> Fully Connected Layer -> Scalar Speed
    """
    def __init__(self, input_dim=21, hidden_dim1=64, hidden_dim2=32):
        super(LSTMNoAttention, self).__init__()
        self.lstm1 = nn.LSTM(input_dim, hidden_dim1, batch_first=True)
        self.lstm2 = nn.LSTM(hidden_dim1, hidden_dim2, batch_first=True)
        self.fc = nn.Linear(hidden_dim2, 1)

    def forward(self, x):
        # x shape: (B, T, D)
        h1, _ = self.lstm1(x) # (B, T, 64)
        h2, _ = self.lstm2(h1) # (B, T, 32)
        
        # Temporal Mean Pooling
        context = torch.mean(h2, dim=1) # (B, 32)
        out = self.fc(context)
        return out.squeeze(-1)

class SelfAttentionLayer(nn.Module):
    """
    Self-Attention Layer following Shin et al. (2025):
    Query, Key, Value linear projections with scaling factor 1/sqrt(d_k).
    """
    def __init__(self, d_model=32):
        super(SelfAttentionLayer, self).__init__()
        self.d_k = d_model
        self.W_q = nn.Linear(d_model, d_model, bias=False)
        self.W_k = nn.Linear(d_model, d_model, bias=False)
        self.W_v = nn.Linear(d_model, d_model, bias=False)

    def forward(self, x):
        # x shape: (B, T, 32)
        Q = self.W_q(x) # (B, T, 32)
        K = self.W_k(x) # (B, T, 32)
        V = self.W_v(x) # (B, T, 32)

        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.d_k ** 0.5) # (B, T, T)
        attn_weights = F.softmax(scores, dim=-1)
        attn_output = torch.matmul(attn_weights, V) # (B, T, 32)
        return attn_output, attn_weights

class LSTMSelfAttention(nn.Module):
    """
    Model 3: Proposed Architecture from Paper (Shin et al., 2025).
    - 2-Layer Stacked LSTM (64 -> 32)
    - Self-Attention Mechanism on H2
    - Concatenation of Attention Output + H2 -> Temporal Pooling -> FC Layer -> Speed
    """
    def __init__(self, input_dim=21, hidden_dim1=64, hidden_dim2=32):
        super(LSTMSelfAttention, self).__init__()
        self.lstm1 = nn.LSTM(input_dim, hidden_dim1, batch_first=True)
        self.lstm2 = nn.LSTM(hidden_dim1, hidden_dim2, batch_first=True)
        self.attention = SelfAttentionLayer(d_model=hidden_dim2)
        self.fc1 = nn.Linear(hidden_dim2 * 2, 32)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(32, 1)

    def forward(self, x):
        # x shape: (B, T, D)
        h1, _ = self.lstm1(x) # (B, T, 64)
        h2, _ = self.lstm2(h1) # (B, T, 32)
        
        attn_out, _ = self.attention(h2) # (B, T, 32)
        
        # Concatenate Attention Output with LSTM output H2
        combined = torch.cat([h2, attn_out], dim=-1) # (B, T, 64)
        
        # Temporal Pooling
        context = torch.mean(combined, dim=1) # (B, 64)
        
        dense = self.relu(self.fc1(context)) # (B, 32)
        out = self.fc2(dense) # (B, 1)
        return out.squeeze(-1)

if __name__ == "__main__":
    dummy_input = torch.randn(8, 200, 21)
    
    m1 = SimpleBaselineMLP()
    m2 = LSTMNoAttention()
    m3 = LSTMSelfAttention()
    
    print("M1 output shape:", m1(dummy_input).shape)
    print("M2 output shape:", m2(dummy_input).shape)
    print("M3 output shape:", m3(dummy_input).shape)
    print("All models instantiated successfully!")
