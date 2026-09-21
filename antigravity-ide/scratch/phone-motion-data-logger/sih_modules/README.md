# ISRO SIH26168 Intelligent Dead Reckoning - Extended Module Suite

This directory contains the independent, modular Python implementation of Modules A through E for the **ISRO Smart India Hackathon Problem Statement SIH26168: AI-ML based Intelligent Dead Reckoning System for Seamless Navigation**.

---

## 1. Suite Architecture & Directory Structure

```
sih_modules/
├── alignment.py           # Module A: Phone-to-vehicle frame alignment & orientation shift detection
├── disturbance.py         # Module B: Signal processing disturbance & road anomaly detector
├── outage_simulator.py    # Module C: GNSS outage simulator & blackout masking engine
├── dead_reckoning.py      # Module D: Modular 2D Dead Reckoning (DR) motion integrator
├── fusion_engine.py       # Module E: GNSS/IMU Fusion & temporal handover blending engine
├── tests/                 # Unit test suite (11 passing tests)
│   ├── test_alignment.py
│   ├── test_disturbance.py
│   ├── test_outage_simulator.py
│   ├── test_dead_reckoning.py
│   └── test_fusion_engine.py
├── run_pipeline.py        # End-to-end integration pipeline runner
├── plots/                 # Generated trajectory maps & blackout figures
│   ├── sensor_data_dead_reckoning_fusion.png
│   └── SESSION-20260917_215707_dead_reckoning_fusion.png
├── SIH_EXTENDED_PIPELINE_REPORT.json
└── README.md
```

---

## 2. Module Technical Breakdown

### Module A: Phone-to-Vehicle Frame Alignment (`alignment.py`)
- **Static Alignment**: Pitch $\theta = \arcsin(-a_x/g)$ and Roll $\phi = \arctan2(a_y, a_z)$ derived from static gravity vector.
- **Dynamic Yaw Alignment**: Principal Component Analysis (PCA) on horizontal acceleration during forward vehicle launch to align phone yaw with vehicle heading.
- **Mounting Shift Detection**: Computes angular cosine distance between current gravity vector and baseline calibration: $\alpha = \arccos\left(\frac{\vec{g}_1 \cdot \vec{g}_2}{\|\vec{g}_1\| \|\vec{g}_2\|}\right)$. Flags alerts when $\alpha > 15^\circ$.
- **Limitations**: Assumes rigid mount relative to vehicle frame during a driving trip.

### Module B: Disturbance & Anomaly Detection (`disturbance.py`)
- Detects road bumps ($|a_{v,z} - g| > 3.0\text{ m/s}^2$), hard braking ($a_{v,x} < -2.5\text{ m/s}^2$), sharp acceleration ($a_{v,x} > 1.8\text{ m/s}^2$), turning maneuvers ($\|\omega_{v,z}\| > 0.35\text{ rad/s}$), and engine/chassis vibration ($\sigma^2(a_{v,z}) > 2.0$).
- Outputs boolean disturbance flag and dynamic confidence score ($0.0 - 1.0$).

### Module C: GNSS Outage Simulation Engine (`outage_simulator.py`)
- Artificially masks GNSS measurements over configurable time intervals ($T_{outage} = 15 - 30\text{ s}$).
- Sets GNSS position, speed, and fix flags to NaN/0 during blackout.
- Ensures only realistic dead-reckoning inputs (IMU, AI speed, Cell ID) are exposed during the outage.

### Module D: Modular 2D Dead Reckoning Engine (`dead_reckoning.py`)
- Integrates AI forward speed $\hat{v}_{fwd}$ and yaw rate $\omega_{v,z}$ over uniform $dt = 0.01\text{ s}$:
  $$\psi(t_k) = \psi(t_{k-1}) + \omega_{v,z}(t_k) \cdot dt$$
  $$N(t_k) = N(t_{k-1}) + \hat{v}_{fwd}(t_k) \cdot \cos(\psi(t_k)) \cdot dt, \quad E(t_k) = E(t_{k-1}) + \hat{v}_{fwd}(t_k) \cdot \sin(\psi(t_k)) \cdot dt$$
- **Non-Holonomic Constraints (NHC)**: Enforces $v_{lateral} = 0$.
- **Drift Monitoring**: Computes distance traveled, absolute positioning error (RMSE, MAE, Max Error), and Cumulative Drift Rate ($\% = \frac{\Delta p}{D_{\text{outage}}} \times 100\%$).
- **Explicit Note**: Speed alone cannot determine position. Position is obtained by integrating forward speed along the direction of orientation (heading).

### Module E: GNSS/IMU Fusion & Handover Engine (`fusion_engine.py`)
- Fuses GNSS fix and Dead Reckoning trajectory during open sky.
- Operates pure Dead Reckoning mode during GNSS blackout.
- **Sigmoid Temporal Handover**: Upon GNSS signal restoration, applies Sigmoid weighting over $T_{blend} = 2.0\text{ s}$ to smoothly transition back to GNSS fix without position jumping/snapping:
  $$w(t) = \frac{1}{1 + \exp\left(-k(t - t_{restore} - T_{blend}/2)\right)}$$

---

## 3. How to Run Unit Tests & Pipeline

### Run Unit Test Suite
```bash
python -m pytest sih_modules/tests
```
*(All 11 unit tests pass in ~1.0 second).*

### Run End-to-End Pipeline Evaluation
```bash
python sih_modules/run_pipeline.py
```
*(Generates quantitative JSON report and visual trajectory PNG figures in `sih_modules/plots/`).*

---

## 4. Unfinished SIH Requirements & Next Phase Roadmap

To complete the full SIH26168 problem statement, the following components remain to be implemented:

1. **OpenStreetMap (OSM) Map-Matching Engine**: Topological Hidden Markov Model (HMM) snapping dead-reckoned position to road graph edges to eliminate lateral heading drift.
2. **15-State Error-State Kalman Filter (ESKF)**: Full 3D strapdown kinematics with explicit online IMU bias estimation ($\mathbf{b}_a, \mathbf{b}_g$).
3. **Cellular Signal RTT / Fingerprint Bounding**: Using Cell ID tower locations and RSSI signal strength to bound maximum drift circles during multi-minute outages.
4. **Android On-Device C++ NDK Engine**: Porting PyTorch / Python modules to C++ ONNX Runtime for sub-10ms real-time mobile execution.
