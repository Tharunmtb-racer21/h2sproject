# PAPER VS IMPLEMENTATION COMPARISON MATRIX

**Reference Paper**: *Deep Learning-Based Vehicle Speed Estimation Using Smartphone Sensors in GNSS-Denied Environment* (Shin, Li, & Kim, *Applied Sciences*, Aug 2025, Vol. 15, Art. 8824).

---

## 1. Three-Way Technical Separation Matrix

| Feature / Method | 1. Paper Reproduction | 2. SIH26168 Requirement | 3. Proposed Engineering Extension | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Inputs** | Accelerometer $(a_x, a_y, a_z)$, Gyroscope $(\omega_x, \omega_y, \omega_z)$, Accel Norm $\|a\|$. | Smartphone 6-DOF IMU, GNSS, Cell ID, Cell RSSI. | Dual-stage Butterworth LPF + FFT engine vibration notch filter. | **VERIFIED** |
| **Magnetometer** | **EXCLUDED** (indoor EM interference degrades stability). | Allowed, but unreliable indoors. | Excluded from AI speed model; used only for coarse static heading fallback. | **VERIFIED** |
| **Coordinate Frame** | Local Smartphone Body Frame (used directly without global transformation). | Vehicle Navigation Frame / Earth Frame. | 2-Stage Dynamic Alignment (Static Gravity for Pitch/Roll, Dynamic PCA for Yaw). | **VERIFIED** |
| **Statistical Features** | Sample Mean $\mu$ and Sample Variance $\sigma^2$ over window $T$ (14 channels). | Not specified. | 14 channels (rolling mean & rolling sample variance, $ddof=1$). | **VERIFIED** |
| **Input Feature Dim ($D$)** | $7\text{ Raw} + 14\text{ Statistical} = 21\text{ features per timestep}$. | Not specified. | 21-dimensional feature matrix $\mathbf{X} \in \mathbb{R}^{T \times 21}$. | **VERIFIED** |
| **Sampling Frequency** | **50 Hz** ($dt = 20\text{ ms}$). | High frequency (100 Hz preferred on Android). | Unified 50 Hz grid for paper baseline; 100 Hz for full ESKF pipeline. | **VERIFIED** |
| **Sequence Length ($T$)** | $T = 200$ timesteps (**4.0 seconds** at 50 Hz). | Real-time low-latency update. | $T = 200$ at 50 Hz ($4.0\text{s}$); window stride = 10 timesteps. | **VERIFIED** |
| **Model Architecture** | 2-Layer Stacked LSTM ($64 \rightarrow 32$) + Self-Attention + FC layers. | AI/ML speed estimation. | PyTorch `LSTMSelfAttention`, `LSTMNoAttention`, `SimpleBaselineMLP`. | **VERIFIED** |
| **Self-Attention** | Scaled Dot-Product Attention on $H_2 \in \mathbb{R}^{T \times 32}$ ($Q, K, V \in \mathbb{R}^{32 \times 32}$). | AI motion learning. | $Q=H_2 W_Q, K=H_2 W_K, V=H_2 W_V$, $\text{softmax}(QK^T/\sqrt{32})V$. | **VERIFIED** |
| **Ground-Truth Target** | **OBD2 Vehicle Speed Interface** (True vehicle wheel speed). | High-accuracy reference velocity. | OBD2 wheel speed / High-precision GNSS velocity. | **VERIFIED** |
| **Phone Postures** | Tested 4 orientations: Pitch $90^\circ$, $60^\circ$, $30^\circ$, Landscape. | Support phone holder mounting. | Current log data has near-flat pitch ($-0.8^\circ$). $90^\circ/60^\circ$ tests **NOT VERIFIED ON CURRENT LOGS**. | **NOT VERIFIED (Dataset Limit)** |
| **Training Dataset** | 41.8 km driving across underground parking facility (Seoul Emart). | Seamless navigation across outages. | Current `data/` folder has only ~64s of moving data ($<4.3\text{ km/h}$). | **REQUIRES DATA** |
| **GNSS Outage Simulation** | Offline evaluation in underground parking lot. | Seamless navigation during signal loss (tunnels, urban canyons). | Configurable blackout simulator (5s, 15s, 30s, 60s windows). | **VERIFIED (Engineering)** |
| **3D State Estimation (ESKF)**| **NOT IN PAPER** (Paper only estimates speed). | 15-State Error-State Kalman Filter (ESKF). | 15-State ESKF fusing AI speed $\hat{v}_{fwd}$ and NHC ($v_{lat}=0$). | **PROPOSED EXTENSION** |
| **Map Matching** | **NOT IN PAPER** (Open-loop odometry only). | OpenStreetMap road network graph matching. | HMM Map Matcher snapping trajectory to OSM edges. | **PROPOSED EXTENSION** |
| **Seamless Handover** | **NOT IN PAPER** | Smooth re-acquisition without position snapping. | Sigmoid Temporal Blending ($T_{blend}=2.0\text{s}$) upon GNSS restoration. | **PROPOSED EXTENSION** |

---

## 2. Unverified or Discrepant Architectural Items

1. **Sampling Rate Discrepancy**:
   - The research paper explicitly specifies **50 Hz** sampling frequency.
   - Our previous preprocessing ran at **100 Hz**, causing $T=200$ to correspond to 2.0 seconds instead of 4.0 seconds.
   - **Correction**: The dedicated `paper_baseline/` module MUST resample data to exactly 50 Hz so $T=200$ corresponds to 4.0 seconds.

2. **Ground Truth Target Discrepancy**:
   - The paper trained models using **OBD2 vehicle speed** (true vehicle wheel speed from CAN bus).
   - Our current dataset relied on smartphone GPS velocity, which is missing during indoor recordings and lacks high-speed vehicle driving dynamics.

3. **Orientation Evaluation Gap**:
   - The paper evaluated models across four phone orientations: Pitch $90^\circ$ (upright), Pitch $60^\circ$ (slanted), Pitch $30^\circ$ (steep slant), and Landscape mode.
   - Our recorded dataset contains only a single phone mounting posture with pitch $\approx -0.8^\circ$ and roll $\approx 1.2^\circ$.

---

## 3. Mathematical Specifications of the Paper Architecture

### Feature Vector Formulation ($D = 21$)
For time step $t \in [1, T]$:
$$\mathbf{x}_t = \left[ a_x, a_y, a_z, \omega_x, \omega_y, \omega_z, \|a\|, \mu_{a_x}, \mu_{a_y}, \mu_{a_z}, \mu_{\omega_x}, \mu_{\omega_y}, \mu_{\omega_z}, \mu_{\|a\|}, \sigma^2_{a_x}, \sigma^2_{a_y}, \sigma^2_{a_z}, \sigma^2_{\omega_x}, \sigma^2_{\omega_y}, \sigma^2_{\omega_z}, \sigma^2_{\|a\|} \right]^T$$

Where sample mean $\mu$ and sample variance $\sigma^2$ are computed over window $T$:
$$\mu = \frac{1}{T} \sum_{i=1}^T x_i, \quad \sigma^2 = \frac{1}{T-1} \sum_{i=1}^T (x_i - \mu)^2$$

### Self-Attention Layer Formulation
1. **Stacked LSTM Outputs**:
   $$H_1 = \text{LSTM}_1(\mathbf{X}) \in \mathbb{R}^{T \times 64}, \quad H_2 = \text{LSTM}_2(H_1) \in \mathbb{R}^{T \times 32}$$
2. **Linear Projections**:
   $$Q = H_2 W_Q, \quad K = H_2 W_K, \quad V = H_2 W_V \quad (W_Q, W_K, W_V \in \mathbb{R}^{32 \times 32})$$
3. **Scaled Dot-Product Attention**:
   $$\mathbf{A} = \text{softmax}\left( \frac{Q K^T}{\sqrt{32}} \right) V \in \mathbb{R}^{T \times 32}$$
4. **Concatenation & Temporal Pooling**:
   $$\mathbf{C} = [H_2 \parallel \mathbf{A}] \in \mathbb{R}^{T \times 64}, \quad \mathbf{c} = \frac{1}{T} \sum_{t=1}^T \mathbf{C}_t \in \mathbb{R}^{64}$$
5. **Regression Output**:
   $$\hat{v} = \mathbf{W}_2 \cdot \text{ReLU}(\mathbf{W}_1 \mathbf{c} + \mathbf{b}_1) + b_2$$
