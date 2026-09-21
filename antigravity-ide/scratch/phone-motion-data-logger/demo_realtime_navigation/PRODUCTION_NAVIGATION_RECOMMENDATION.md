# SIH26168 — Production Navigation Recommendation

**System:** SIH26168 AI-ML Based Intelligent Dead Reckoning System  
**Audit Target:** Production Default Configuration & Readiness Matrix  
**Date:** 2026-09-21  

---

## 1. Formal Production Recommendation

```text
RECOMMENDATION: RETAIN PERSISTENCE_PRODUCTION AS DEFAULT PRODUCTION BASELINE
```

### Mandatory Rules:
1. Production default MUST REMAIN: `PERSISTENCE_PRODUCTION`.
2. Do NOT automatically replace `PERSISTENCE_PRODUCTION` with `AI_RATIO_DIAGNOSTIC` or `ADAPTIVE_HYBRID_DIAGNOSTIC`.
3. Retain `AI_RATIO_DIAGNOSTIC`, `ADAPTIVE_HYBRID_DIAGNOSTIC`, `DELTA_V_DIAGNOSTIC`, and `REFERENCE_DIAGNOSTIC` for diagnostic evaluation and live dashboard telemetry logging.

---

## 2. Readiness Evaluation Matrix

| Decision Criterion | Result | Pass / Fail | Evidence |
|---|:---:|:---:|---|
| **Cross-Session Speed Performance** | Mixed | **CONDITIONAL** | Model V2 AI Ratio outperforms Persistence on Motorway (`S3c` 120s: $470.09\text{m}$ vs $566.18\text{m}$), but Persistence is superior on Urban (`S3a` 60s: $34.45\text{m}$ vs $53.91\text{m}$). |
| **Cross-Session Position Performance** | Mixed | **CONDITIONAL** | Motorway position error reduced by $96.09\text{m}$; Urban position error degraded by $19.46\text{m}$ due to gyro heading drift during $90^\circ$ turns. |
| **Low-Speed Stability ($v < 1\text{ m/s}$)** | Stable | **PASS** | $\max(v_{\text{anchor}}, 1.0\text{ m/s})$ denominator safeguard prevents division-by-zero or numerical explosion near standstill. |
| **Stationary False Movement** | $0.0000\text{ m}$ | **PASS** | `SafeStandstillDetector` (ZUPT) zeroes speed during stationary intervals ($a_{\text{var}} < 0.015\text{ m}^2/\text{s}^4, g_{\text{mean}} < 0.02\text{ rad/s}$). |
| **Ground-Truth Leakage Protection** | $0.0000\text{ m}$ | **PASS** | 3-Run Adversarial Leakage test confirmed 100% numerical identity ($0.00000000\text{m}$ diff) when reference data is corrupted during outage. |
| **Numerical & Bound Safety** | $[0.0, 3.0]$ | **PASS** | Softplus activation and clipping enforce strict physical bounds on ratio output. NaN/Inf inputs revert to fallback cleanly. |
| **Automated Suite Reproducibility** | 7/7 Suite | **PASS** | Full automated test suite passes reproducibly with zero exceptions. |

---

## 3. Operational Categorization

### 3.1 Production-Supported Behavior (`PERSISTENCE_PRODUCTION`)
* **Default Active Mode:** Constant-Speed Persistence using last GNSS speed anchor $v_0$.
* **Smoothing & Stabilization:** 1D EKF velocity smoothing + Multi-signal ZUPT standstill detection + Non-Holonomic Constraints (NHC).
* **Heading Integration:** Pre-outage debiased & scaled gyro yaw rate integration ($\text{yaw\_rate\_raw} = -\text{gyro\_y}$).
* **Scope:** Standard deployment for all production user sessions.

### 3.2 Diagnostic-Only Behavior
* `AI_RATIO_DIAGNOSTIC`: Logged for telemetry and offline benchmarking. Highly recommended for motorway driving sessions ($v_{\text{anchor}} > 5.0\text{ m/s}$).
* `ADAPTIVE_HYBRID_DIAGNOSTIC`: Logged for telemetry. Dynamically switches to AI ratio during motorway cruising and reverts to persistence during urban turns.
* `DELTA_V_DIAGNOSTIC`: Legacy delta-v model retained for comparative logging.
* `REFERENCE_DIAGNOSTIC`: Ground-truth oracle baseline used strictly for offline post-hoc evaluation.

---

## 4. Requirements for Future Production Model Upgrades

Before Model V2 or Adaptive Hybrid can be promoted to production default, the following requirements must be satisfied:
1. **Multi-Session Urban Dataset:** Expand dataset beyond `IOVNBD_S3a` to include 10+ urban driving sessions with frequent stop-and-go maneuvers.
2. **Dynamic 3D Orientation Calibration:** Implement automatic phone-to-vehicle gravity vector frame alignment ($\mathbf{R}_{\text{phone} \to \text{vehicle}}$) to reduce urban heading drift below $10^\circ$ MAE over 120s.
3. **Formal Verification:** Re-evaluate readiness matrix across the expanded dataset.
