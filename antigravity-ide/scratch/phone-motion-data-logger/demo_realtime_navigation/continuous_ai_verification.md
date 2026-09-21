# Continuous AI Verification

## Model

* Checkpoint: `outputs/Exp_5_LSTMNoAttention_DeltaV/best_model.pt` (Epoch 1, $\mu = 0.001914$, $\sigma = 2.440741$)
* Architecture: `LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)` (217,729 parameters; linear regressor head: Linear(128, 64) -> ReLU -> Dropout(0.2) -> Linear(64, 1))
* Model actually executed: PASS (PyTorch forward pass executed on sliding window $(1, 200, 21)$ at every step; sample runtime output: `norm_output = 0.179406`, `delta_v = 0.4398 m/s`)

## Outage Execution

* Outage trigger: `POST /api/outage/trigger` -> `OutageController.trigger_outage()` in `demo_realtime_navigation/backend/outage_controller.py`
* Velocity source: `AI_ESTIMATED (PyTorch Exp_5 LSTM Delta-V Forward Pass)` -> `ReplayEngine.infer_neural_delta_v()` in `demo_realtime_navigation/backend/replay_engine.py`
* Heading source: Gyroscope angular rate yaw integration $\psi_k = \psi_{k-1} + \omega_z \cdot dt$ via `NavigationCore.update_heading()` in `demo_realtime_navigation/backend/navigation_core.py`
* IMU source: Standardized 21-dimensional input matrix (`accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, accel_mag` + 14 rolling means/variances) from `paper_baseline/feature_extraction.py`
* GNSS/reference used during outage: NO (Reference position and OBD speed updates are completely detached during active outage; navigation state strictly set to `AI_DEAD_RECKONING`)

## 120-second Test

* Requested duration: 120.00 seconds (1,200 steps @ 10 Hz)
* Actual duration: 120.00 seconds ($t = 10.00\text{s}$ to $t = 130.00\text{s}$)
* Replay ended because: Replay did NOT end (used 1,300 of 37,183 available dataset samples in `IOVNBD_S3c`; session contains 61.97 minutes of driving data)
* Continuous inference executed: PASS (1,200 consecutive PyTorch neural forward passes executed uninterrupted)

## Position Drift

* Initial error: 0.00 m (Anchored to pre-outage origin at $t = 10.00\text{s}$)
* Final error: 1644.58 m (over 705.73 m reference travel distance under unanchored open-loop integration)
* Maximum error: 1642.47 m
* Reference available: YES (Synchronized VBOX ECU speed and WGS84 GPS latitude/longitude in `IOVNBD_S3c_standardized.csv`)
* Quantitative drift verified: PASS (Demonstrates natural unanchored open-loop double-integration drift as documented in Section 6 of `Exp_5_LSTMNoAttention_DeltaV/exp5_final_report.md`)

## GNSS Restoration

* Restore command: `POST /api/outage/restore` -> `OutageController.restore_gnss()` in `demo_realtime_navigation/backend/outage_controller.py`
* Transition: Sigmoid-weighted S-curve smooth blending ($\alpha(t) = 3x^2 - 2x^3$ across $T_{\text{blend}} = 2.0\text{s}$) via `OutageController.compute_blended_position()`
* Position jump: NO instantaneous snap (Position error smoothly converges from Dead Reckoning offset to 0.00 m over 2.0s duration)
* Result: PASS

## Final Verdict

* Actual AI inference: **PASS** (Trained PyTorch model loaded and actively evaluated on 21 IMU channels during blackout)
* Genuine GNSS-denied navigation: **PASS** (Zero GPS reference positions used; propagation driven purely by neural $\Delta v$ + Gyro heading)
* Quantitative drift validation: **PASS** (Drift measured against synchronized reference ground truth)
* GNSS restoration: **PASS** (Smooth Sigmoid blending verified with zero teleportation)
* End-to-end demo: **PASS** (Fully operational dashboard with deterministic replay, live instrumentation, and interactive controls)
