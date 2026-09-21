# SIH26168 — Adaptive Hybrid Navigation Strategy Design

**System:** SIH26168 AI-ML Based Intelligent Dead Reckoning System  
**Module:** `ADAPTIVE_HYBRID_DIAGNOSTIC` Mode Specification  
**Date:** 2026-09-21  

---

## 1. Objective

This document specifies the technical design and safety policy for the experimental `ADAPTIVE_HYBRID_DIAGNOSTIC` mode.

The adaptive hybrid mode dynamically selects between:
1. `PERSISTENCE_PRODUCTION` (Anchor Speed + Gyro Kinematics + ZUPT)
2. `AI_RATIO_DIAGNOSTIC` (Model V2 Bounded Speed Ratio $r_{\text{pred}} \cdot v_{\text{anchor}}$)

---

## 2. Strict Zero Reference-Data Leakage Requirement

Selection between Persistence and AI Ratio is governed **strictly by telemetry features available during the GNSS outage at runtime**:
* Pre-outage anchor speed ($v_{\text{anchor}}$)
* Real-time 6-DOF IMU accelerometer & gyroscope magnitude/variance
* Model V2 ratio prediction ($r_{\text{pred}}$) and numerical validity checks
* Standstill detection state (`SafeStandstillDetector` ZUPT)

**Prohibited Information:**
* Future ground-truth speed (`reference_speed`)
* Reference position (`latitude`, `longitude`, `ref_east_m`, `ref_north_m`)
* Reference heading (`reference_heading`)
* Ground-truth evaluation metrics (position error, speed MAE/RMSE)

---

## 3. Runtime Decision Tree & Policy Logic

For each time-step during a GNSS outage:

```mermaid
flowchart TD
    A[Start Outage Step] --> B{ZUPT Standstill Active?}
    B -- Yes --> C[Target Speed = 0.0 m/s<br>ZUPT Override]
    B -- No --> D{Model V2 Loaded & Valid?<br>0.2 <= r_pred <= 2.5?}
    D -- No --> E[Target Speed = v_anchor<br>ANOMALY_FALLBACK]
    D -- Yes --> F{v_anchor < 1.0 m/s?}
    F -- Yes --> G[Target Speed = v_anchor<br>LOW_SPEED_FALLBACK]
    F -- No --> H{|gyro_yaw_debiased| > 0.15 rad/s?}
    H -- Yes --> I[Target Speed = v_anchor<br>HIGH_TURN_FALLBACK]
    H -- No --> J{v_anchor >= 5.0 m/s?}
    J -- Yes --> K[Target Speed = r_pred * max(v_anchor, 1.0)<br>MOTORWAY_AI_RATIO]
    J -- No --> L[Target Speed = v_anchor<br>URBAN_PERSISTENCE]
```

### Rationale for Decision Rules:
1. **ZUPT Standstill Override:** Zeroes speed when 6-DOF IMU signals confirm stationary state, preventing false movement.
2. **Model Anomaly Protection:** If $r_{\text{pred}}$ contains NaN/Inf, or falls outside physical bounds $[0.2, 2.5]$, system falls back to constant anchor speed persistence.
3. **Low-Speed Safeguard ($v_{\text{anchor}} < 1.0\text{ m/s}$):** Crawling or starting from rest can amplify ratio estimation noise. Persistence is safer.
4. **Urban High-Turn Protection ($|\omega_{\text{yaw}}| > 0.15\text{ rad/s}$):** During sharp $90^\circ$ urban turns, IMU accelerations are dominated by lateral centripetal forces. Fallback to persistence prevents speed ratio corruption.
5. **Motorway Cruising Mode ($v_{\text{anchor}} \ge 5.0\text{ m/s}$ & Moderate Turning):** In high-speed linear cruising, Model V2 (`AI_RATIO_DIAGNOSTIC`) significantly reduces 120s position drift ($470.09\text{m}$ vs $566.18\text{m}$).

---

## 4. Safety & Transition Smoothing Policy

1. **Denominator Safeguard:** Reconstruction formula always applies $\max(v_{\text{anchor}}, 1.0\text{ m/s})$ to eliminate division-by-zero or numerical explosion.
2. **EKF Smooth Blending:** Target velocity $v_{\text{target}}$ is passed into 1D Extended Kalman Filter (`VelocityEKF`) to ensure continuous, physically plausible speed transitions.
3. **Production Default Protection:** Production default mode remains `PERSISTENCE_PRODUCTION`. The adaptive hybrid strategy operates strictly as a diagnostic mode (`ADAPTIVE_HYBRID_DIAGNOSTIC`).
