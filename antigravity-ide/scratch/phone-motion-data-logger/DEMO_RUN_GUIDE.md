# SIH168 — Hackathon Demo Run Guide
**AI-ML Based Intelligent Dead Reckoning System**

---

## Quick Start (60 Seconds)

```powershell
# From project root:
cd c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger

# Start the server
python demo_realtime_navigation/run_demo.py --port 8080

# Dashboard opens automatically at: http://localhost:8080
```

If the browser does not open automatically, navigate to **http://localhost:8080** manually.

---

## Dashboard Controls Reference

| Button | Action |
|--------|--------|
| Play   | Start data replay from beginning |
| Pause  | Pause replay |
| Speed 1x / 2x / 5x | Change replay speed |
| Simulate Outage | Cut GNSS signal (starts dead reckoning) |
| Restore GNSS | Reconnect GNSS (sigmoid blend-back) |
| Reset  | Return to t=0, clear all state |

---

## Step-by-Step Demo Sequence

### Step 1 — Show GNSS-Locked Navigation
1. Click **Play** — trajectory traces on map
2. Point to top status bar: **"GNSS LOCKED"** (green)
3. Note: speed, heading, position all sourced from GPS hardware
4. Say: *"This is normal operation with full satellite fix."*

### Step 2 — Simulate GNSS Outage
1. Click **Simulate Outage** button
2. Status bar changes to **"AI DEAD RECKONING"** (yellow/amber)
3. Dashboard switches from GNSS position to AI-computed position
4. Say: *"GPS is now cut. The system runs entirely on IMU sensor data — no GPS, no reference speed."*

### Step 3 — Show Dead Reckoning Running
1. Let replay advance 20–30 seconds in outage mode
2. Point to **velocity** — AI-estimated from neural model
3. Point to **heading** — corrected yaw from gyroscope integration
4. Point to **position trace** — ENU integration using corrected outputs
5. Say: *"The AI model was trained on 5 sessions of real driving data. It estimates vehicle speed from raw IMU features. Heading is independently corrected for sensor mounting orientation."*

### Step 4 — Explain Algorithm Stack (NHC, ZUPT, EKF)
While outage is active:
- **NHC**: *"A ground vehicle cannot slide sideways. We constrain lateral velocity to near-zero — this removes a major drift source."*
- **ZUPT**: *"When the car stops at a traffic light, IMU noise would accumulate. ZUPT detects genuine stops using only accelerometer variance and gyro magnitude — no speed sensor needed."*
- **EKF**: *"A 1-D Kalman Filter fuses the neural velocity estimate with NHC feedback, smoothing noise and preventing spikes."*

### Step 5 — Restore GNSS
1. Click **Restore GNSS**
2. Status: `AI_DEAD_RECKONING` -> `GNSS_RESTORE_BLENDING` -> `GNSS_LOCKED`
3. Position smoothly converges — no jump
4. Say: *"When GPS returns, we sigmoid-blend back to GPS over 2 seconds. This prevents a position jump that would appear with an instant switch."*

### Step 6 — Reset and Repeat
- Click **Reset** and replay from start for any follow-up questions

---

## Expected Dashboard Outputs

| Metric | Expected Range | Source |
|--------|----------------|--------|
| Speed (GNSS mode) | 0–80 km/h | VBOX GPS hardware |
| Speed (DR mode) | 0–80 km/h | Neural network (IMU only) |
| Heading | 0–360 deg | Gyro-integrated, yaw-corrected |
| GNSS Status | LOCKED / DEAD_RECKONING / BLENDING | System state machine |
| EKF Velocity | Smooth, noise-reduced | 1-D Kalman filter |
| Position Error (30s outage) | ~17 m typical | Measured offline vs ground truth |
| Restoration Jump | < 5 m | Sigmoid blending verified |

All displayed values are real-time system outputs. No values are hardcoded.

---

## Jury Q&A Scripts

**"What problem are you solving?"**
> GPS fails in tunnels, underground parking, urban canyons, and bridges. Our system uses a trained AI model to estimate vehicle motion from an inertial sensor alone — keeping navigation alive even when GPS is completely unavailable.

**"How is this better than existing dead reckoning?"**
> Traditional dead reckoning uses fixed equations. We use a PyTorch neural network trained on real driving sessions that learns speed from raw IMU feature patterns. We also add three physics-based corrections: NHC prevents sideways drift, ZUPT resets velocity at stops, and EKF smooths the estimate.

**"Is this real sensor data?"**
> Yes. The IMU data is recorded from a phone mounted inside a real vehicle on real roads. The neural model was trained offline and runs in real time on CPU only — no GPU required.

**"What is your benchmark error?"**
> In our offline evaluation on the IOVNBD_S3c dataset, with GNSS cut for 30 seconds, mean position error is approximately 17 metres. For 120-second outages, mean error is approximately 44 metres. Error grows roughly linearly with outage duration.

**"What are the limitations?"**
> The model was trained on a limited dataset in specific road conditions. Performance may degrade on sharp turns, very high speeds, or roads not represented in training data. This is a research prototype — not a production navigation system.

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Page not loading | Confirm server is running — check terminal for "Serving on port 8080" |
| Speed always 0 | Click Play first — replay must be started |
| Map not showing | Scroll down — map canvas is below metric cards |
| Outage button grayed | Start replay first, then trigger outage |
| Server crashes | Restart: python demo_realtime_navigation/run_demo.py --port 8080 |
| Browser blocks localhost | Use Chrome or Edge; disable HTTPS-only mode |

---

## Architecture Quick Reference

```
Smartphone IMU (ax, ay, az, gx, gy, gz)
    |
    v
Feature Extraction (20 statistical features)
    |
    v
Training-Fitted Scaler (scaler_params.json)
    |
    v
PyTorch Neural Network --> Speed Estimate
    |
    v
Corrected Yaw (yaw_rate = -gyro_y, sensor-frame)
    |
    v
NHC -- Non-Holonomic Constraint (lateral -> 0)
    |
    v
ZUPT -- Standstill Detection (var < 0.015, |w| < 0.02 rad/s)
    |
    v
EKF -- 1-D Velocity Kalman Filter
    |
    v
ENU Dead-Reckoning Integration
    |
    v
Sigmoid GNSS Blending (2s transition on restore)
    |
    v
Dashboard (Flask, http://localhost:8080)
```

---

*SIH168 | Tharunmtb-racer21/h2sproject | Research Prototype*
