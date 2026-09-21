# SIH26168 — Model V2 Low-Speed & Standstill Safety Audit Report

## 1. Safety Audit Objective & Methodology

A dedicated empirical safety audit (`demo_realtime_navigation/test_low_speed_safety.py`) was executed to evaluate Model V2 (`LSTMAbsoluteSpeedRatio`) across low-speed, standstill, crawling, and stop-and-go kinematic regimes.

### Regimes Tested:
1. **Standstill Outage Initiation** ($v_{anchor} = 0.08\text{ m/s}$)
2. **Crawling Motion Outage** ($0.1\text{ m/s} \le v_{anchor} < 1.0\text{ m/s}$)
3. **Low-Speed Urban Range** ($1.0\text{ m/s} \le v_{anchor} \le 3.0\text{ m/s}$)
4. **Dynamic Acceleration & Deceleration Regimes** ($a_x > 1.5\text{ m/s}^2$ and $a_x < -1.5\text{ m/s}^2$)

---

## 2. Empirical Findings & Metric Table

| Test Scenario | Regimes / Anchor Speed | Measured Metric / Result | Safety Requirement | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Zero Anchor Speed** | $v_{anchor} = 0.00\text{ m/s}$ | Denominator safe-clamped to $1.0\text{ m/s}$ | $v_{pred} \ne \text{NaN} / \text{Inf}$ | **PASS** |
| **Crawling Anchor Speed** | $v_{anchor} = 0.98\text{ m/s}$ | safe_anchor = $1.00\text{ m/s}$, Speed MAE = $0.1302\text{ m/s}$ | Unbounded spike prevented | **PASS** |
| **Standstill False Movement** | $v_{anchor} = 0.08\text{ m/s}$ | False Standstill Movement = $1.8627\text{ m}$ over 30s | Minimal drift during stop | **WARNING** |
| **Output Range Bound** | All test windows | Predictions bounded in $[0.8809, 1.6593] \subset [0.0, 3.0]$ | $r_{pred} \in [0.0, 3.0]$ | **PASS** |
| **ZUPT Override Interaction** | Multi-signal standstill | ZUPT forces $v_{fused} = 0.0\text{ m/s}$ when $\sigma_a^2 < 0.015$ | Hard safety clamp | **PASS** |
| **Dynamic Accel Steps** | $a_x > 1.5\text{ m/s}^2$ | 1,795 dynamic steps evaluated | Smooth EKF speed update | **PASS** |
| **Dynamic Decel Steps** | $a_x < -1.5\text{ m/s}^2$ | 2,035 dynamic steps evaluated | Non-negative speed clamp | **PASS** |

---

## 3. Detailed Safety Evaluation & Observations

1. **Zero Denominator Safeguard**:
   - For all $v_{anchor} < 1.0\text{ m/s}$, the denominator safeguard $\max(v_{anchor}, 1.0\text{ m/s})$ prevented mathematical division-by-zero or numerical explosion ($v / 0.001 \rightarrow \infty$).
2. **Output Head Bounded Activation**:
   - The output activation $r_{pred} = 3.0 \cdot \text{Sigmoid}(h_{64})$ strictly constrained all ratio predictions within $[0.0, 3.0]$.
3. **ZUPT & AI Ratio Interaction**:
   - When the vehicle comes to a complete standstill during an outage, the pure physical IMU Multi-Signal ZUPT (`SafeStandstillDetector`) safely overrides AI ratio speed and clamps speed to $0.0\text{ m/s}$.
   - However, when initiating an outage during crawling speed ($0.08\text{ m/s}$) prior to full standstill activation, slight ratio fluctuations can produce ~1.86m drift over 30s before ZUPT triggers.

---

## 4. Safety Audit Recommendations

- Maintain **`PERSISTENCE_PRODUCTION`** as the default production mode for urban drives with frequent stops.
- Keep **`AI_RATIO_DIAGNOSTIC`** as a verified diagnostic mode for highway and motorway navigation.
