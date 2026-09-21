# SIH168 / ISRO Problem Statement Requirement Audit

**Problem Statement Code:** SIH168 / SIH26168 (ISRO)  
**Title:** AI-ML Based Intelligent Dead Reckoning System for Seamless Navigation  
**Audit Date:** 2026-09-20  
**Audit Standard:** Strict Senior Navigation Engineer & SIH Evaluator Review  

---

## 1. Official Problem Statement Extraction & Decomposition

### 1.1 Objective & Scope
The official requirement asks for an **intelligent, smartphone-based dead-reckoning navigation system** that bridges GNSS signal outages (tunnels, underground parking garages, urban canyons, flyovers) using onboard smartphone sensors (IMU, magnetometer, cellular signals) enhanced by AI/ML algorithms to provide **continuous, seamless positioning and velocity estimation**.

---

## 2. Technical Requirement Analysis

### 2.1 Output Requirements: Velocity vs Heading vs Position
* **Is Velocity alone sufficient?** **NO**. Velocity estimation (speed $\hat{v}$) is only a kinematic sub-component. Dead reckoning by definition computes the vehicle's position vector $\mathbf{p}(t) = [x(t), y(t), z(t)]^T$ or geodetic coordinates $(\text{Lat}, \text{Lon})$.
* **Is Heading required?** **YES**. Position propagation strictly requires 2D/3D heading orientation $\psi(t)$:
  $$N(t_k) = N(t_{k-1}) + \int_{t_{k-1}}^{t_k} v(t) \cos(\psi(t)) dt, \quad E(t_k) = E(t_{k-1}) + \int_{t_{k-1}}^{t_k} v(t) \sin(\psi(t)) dt$$
  A $1^\circ$ heading error on a vehicle traveling at 60 km/h generates approximately $0.29\text{ m}$ of cross-track position error every second.
* **Are Latitude/Longitude Mandatory?** **YES for end-user navigation, but Local ENU/NED X–Y trajectory is the required mathematical intermediate**. A complete system must maintain local tangent plane coordinates (East-North-Up) anchored to the last known WGS84 GNSS coordinate ($\text{Lat}_0, \text{Lon}_0$) and convert updated local displacement back to WGS84 for map display.

---

### 2.2 What Does "Seamless Navigation" Technically Require?
1. **Continuous Availability:** Position and speed updates must continue without interruption at a minimum of 10–50 Hz when GNSS drops to 0.
2. **Outage Handover Detection:** Automatic detection of GNSS signal degradation (horizontal dilution of precision HDOP increase, satellite drop, signal timeout).
3. **Smooth Re-acquisition (No Snapping/Jumping):** When GNSS returns, the system must not tele-transport or snap abruptly across dozens of meters; it must apply smooth temporal blending (e.g., Sigmoid handover or Kalman filter state reset).
4. **Zero-Velocity Update (ZUPT):** Automatic detection of traffic stops to prevent unbounded dead-reckoning position drift while stationary.
5. **Physical Realizability:** Non-negative velocity ($\hat{v} \ge 0$), bounded acceleration, and non-holonomic constraints (vehicle cannot slip sideways: $v_{\text{lateral}} \approx 0$).

---

### 2.3 What Parts of the Research Paper Methodology are Essential?
*Reference Paper:* Shin, Li, & Kim, *Deep Learning-Based Vehicle Speed Estimation Using Smartphone Sensors in GNSS-Denied Environment*, Applied Sciences, Aug 2025.

1. **50 Hz Sampling Frequency Grid:** 200 timesteps ($4.0\text{ s}$ temporal window) is the physically motivated window length required to average road vibration while capturing vehicular acceleration.
2. **21-Dimensional Statistical Feature Formulation:**
   $$\mathbf{x}_t = [a_x, a_y, a_z, \omega_x, \omega_y, \omega_z, \|a\|, \mu_{a_x\dots \|a\|}, \sigma^2_{a_x\dots \|a\|}]$$
   The rolling statistical moments ($\mu, \sigma^2$) encode low-frequency kinetic state changes.
3. **Galilean Invariance Awareness (Our Stage 5 Discovery):** Accelerometers measure proper acceleration $\frac{dv}{dt}$, not absolute velocity $v$. Therefore, formulating the neural learning target as relative velocity change ($\Delta v = v_{\text{end}} - v_{\text{start}}$) with an anchor speed is mathematically required to eliminate dynamic range collapse.
4. **Integration with Kinematic / Filter Framework:** The paper only estimated 1D scalar speed; full SIH navigation requires feeding this speed into a directional integration / Kalman filter engine.
