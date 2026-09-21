# SAMPLING RATE ANALYSIS AND LIMITATIONS REPORT

**Module**: SIH26168 Scientific Sanity Check  
**Dataset Reference**: IO-VNBD (`README_1.pdf`)  
**Target Paper Reference**: Shin et al. (2025), *Deep Learning-Based Vehicle Speed Estimation Using Smartphone Sensors in GNSS-Denied Environment*  

---

## 1. Documentation Evidence from `README_1.pdf`

### Page 1 Documentation Text:
> *"The vehicle tracking dataset was recorded using a research vehicle equipped with ego-motion sensors on public roads in the United Kingdom, Nigeria, and France. The sensors include a GPS receiver, inertial navigation sensors, wheel-speed sensors amongst other sensors found on the car as well as the inertial navigation sensors and GPS receiver in an android smart phone sampling at 10HZ."*  
> — **`README_1.pdf`, Page 1, Abstract**

### Page 4 Documentation Text (Table 3 - ECU & VBOX Data):
> *Row 9: `Sampleperiod`: `seconds` (0.1 seconds = 10 Hz)*  
> *Row 5: `velocity`: `kmh` (10 Hz CAN/VBOX reference velocity)*  
> — **`README_1.pdf`, Page 4, Table 3**

---

## 2. Sampling Rate & Information Bandwidth Comparison

| Property | Paper Specification (Shin et al., 2025) | IO-VNBD Benchmark Dataset | Resampled Pipeline State |
| :--- | :--- | :--- | :--- |
| **a) Original Sensor Sampling Rate** | $50\text{ Hz}$ ($dt = 20\text{ ms}$) | **$10\text{ Hz}$** ($dt = 100\text{ ms}$) | $10\text{ Hz}$ Native Input |
| **b) Resampled Model Input Rate** | $50\text{ Hz}$ ($dt = 20\text{ ms}$) | N/A | **$50\text{ Hz}$** ($dt = 20\text{ ms}$) |
| **c) Actual Independent Information Rate** | $50\text{ Hz}$ (Nyquist $= 25\text{ Hz}$) | **$10\text{ Hz}$** (Nyquist $= 5\text{ Hz}$) | **$10\text{ Hz}$** (Nyquist $= 5\text{ Hz}$) |
| **Window Length ($T$)** | $T = 200$ samples | $T = 40$ native samples | $T = 200$ resampled samples |
| **Window Physical Duration** | $4.0\text{ seconds}$ | $4.0\text{ seconds}$ | **$4.0\text{ seconds}$** |

---

## 3. Scientific Validity of 10 Hz to 50 Hz Resampling

1. **Temporal Dimension Alignment**: Resampling the native 10 Hz IO-VNBD IMU streams to a 50 Hz time grid using linear interpolation produces a uniform time interval of $dt = 20\text{ ms}$. This allows the sequence generator to construct tensor windows of size $T = 200$, matching the temporal duration ($4.0\text{ seconds}$) of the paper's model architecture.
2. **Information Bandwidth Limitation**: Linear interpolation increases the row count (from 40 rows to 200 rows per 4-second window) but **does NOT add physical high-frequency inertial signals** above $5\text{ Hz}$. High-frequency road vibration dynamics between $5\text{ Hz}$ and $25\text{ Hz}$ are absent from the dataset.
3. **Scientific Distinction**: The resampled model operates on smooth, interpolated 50 Hz trajectories. While structural and architectural alignment with Shin et al. (2025) is maintained ($T=200, \text{dim}=21$), this pipeline is an **interpolated 50 Hz approximation**, not a genuine high-frequency 50 Hz physical measurement reproduction.

---

## 4. Final Scientific Statement & Limitation

- **Status**: **LIMITATION ACKNOWLEDGED**
- **Impact**: The model accurately captures low-frequency motion trends, accelerations, and macro-maneuvers up to $5\text{ Hz}$. High-frequency chassis chatter ($>5\text{ Hz}$) is smoothed out by the original 10 Hz sensor hardware.
