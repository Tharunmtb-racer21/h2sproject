# SIH26168 — Model V2 Technical Design Document: Bounded Absolute Speed Ratio ($r_t$)

## 1. Executive Summary & Design Motivation

The previous velocity prediction target formulation ($\Delta v = v_t - v_{t-1}$) suffered from cumulative random-walk velocity drift when integrated recursively over extended GNSS outage blackouts ($60\text{s} - 120\text{s}$). 

**Model V2** (`Exp_6_LSTM_AbsoluteSpeedRatio`) reformulates the speed prediction target as a **Bounded Absolute Speed Ratio**:

$$r_t = \frac{v_t}{v_{anchor}}$$

where:
- $v_t$: Instantaneous ground-truth speed at target timestamp $t$.
- $v_{anchor}$: Vehicle speed at the start of the GNSS outage window ($t_{anchor}$).
- $r_t$: Non-dimensional speed scaling ratio bounded in $[0.0, 3.0]$.

---

## 2. Mathematical Formulation & Low-Speed Safeguards

### Target Equation:
$$r_t = \text{clip}\left(\frac{v_t}{\max(v_{anchor}, 1.0\text{ m/s})}, 0.0, 3.0\right)$$

### Key Safeguards:
1. **Zero / Low-Speed Division Prevention**:
   The denominator is clamped to $\max(v_{anchor}, 1.0\text{ m/s})$ ($3.6\text{ km/h}$). When anchor speed is low or standstill ($v_{anchor} < 1.0\text{ m/s}$), dividing by $1.0\text{ m/s}$ prevents extreme numerical spikes ($v_t / 0.01 = 100$).
2. **Bounded Sigmoid Activation Head**:
   The output head of `LSTMAbsoluteSpeedRatio` forces all predictions mathematically into $[0.0, 3.0]$:
   $$r_{pred} = 3.0 \cdot \sigma(\mathbf{W}_{out} \cdot h_{64} + b_{out})$$
   where $\sigma(z) = \frac{1}{1 + e^{-z}}$. This guarantees zero negative velocity predictions ($r_{pred} \ge 0.0$) and caps maximum ratio to $3.0\text{x}$ without silent un-documented clipping.
3. **Inference Velocity Reconstruction**:
   $$v_{AI} = r_{pred} \cdot \max(v_{anchor}, 0.0)$$
   Because $v_{AI}$ is computed as a direct multiplicative scaling of $v_{anchor}$, **no recursive step integration is performed**, completely eliminating random-walk velocity divergence over long outages!

---

## 3. Data Leakage Safeguards & Feature Engineering

- **21 Paper-Aligned Features**:
  - 7 Raw IMU Channels: `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`, `accel_mag`
  - 14 Rolling Moments: 7-channel rolling mean + 7-channel rolling variance over $T=200$ sliding window ($4.0\text{s}$ @ 50Hz).
- **Strict Anti-Leakage Scaler**:
  - `PaperMinMaxScaler` is fitted strictly on the Training set (`IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2`).
  - Validation (`IOVNBD_S3a`) and Test (`IOVNBD_S3c`) sets apply `transform()` using frozen training min/max bounds.
- **Strict Outage Data Isolation**:
  - During live inference (`AI_RATIO_DIAGNOSTIC`), reference speed and heading are never passed to the model or navigation core.

---

## 4. Multi-Mode Operating Architecture

`ReplayEngine` provides four distinct speed modes:

1. **`PERSISTENCE_PRODUCTION`** (Default Production Baseline):
   - $v = v_{anchor}$ + EKF velocity smoothing + Multi-Signal ZUPT standstill zeroing.
   - Guaranteed stable, zero-leakage production baseline.
2. **`AI_RATIO_DIAGNOSTIC`** (Model V2 Evaluation Mode):
   - $v_{AI} = r_{pred} \cdot v_{anchor}$.
   - Diagnostic mode evaluating dynamic speed ratio predictions.
3. **`DELTA_V_DIAGNOSTIC`** (Legacy Model V1 Diagnostic Mode):
   - $v_{AI} = v_{anchor} + \Delta v$.
   - Retained for legacy model evaluation.
4. **`REFERENCE_DIAGNOSTIC`** (Non-Production Evaluation Only):
   - $v = v_{reference}$. Marked explicitly as non-production evaluation diagnostic.
