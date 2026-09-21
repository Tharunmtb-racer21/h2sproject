# SIH26168 — Model V2 Formal Production Readiness Audit & Decision Matrix

## 1. Executive Safety Decision Matrix

| Criterion | Evaluation Requirement | Result | Pass/Fail | Evidence / Audit Source |
| :--- | :--- | :--- | :---: | :--- |
| **Cross-Session Speed Performance** | Lower speed MAE across all test sessions | **Highway MAE 4.27m/s** vs Pers 3.79m/s offline | **FAIL** | `MODEL_V2_EVALUATION_REPORT.md` (Persistence outperforms AI speed MAE on overall test set) |
| **Cross-Session Position Performance** | Reduced position error across all test sessions | **Motorway 120s: 470.09m vs 566.18m** (Improved)<br>**Urban 60s: 53.91m vs 34.45m** (Worse) | **FAIL** | `compare_speed_models.py` (Model V2 excels on motorways but persistence is superior on sharp urban turns) |
| **Low-Speed Stability** | No numerical divergence when $v_{anchor} \rightarrow 0$ | Denominator safe-clamped to $\max(v_{anchor}, 1.0\text{ m/s})$ | **PASS** | `test_model_v2_safeguards.py` |
| **Stationary False Movement** | Zero false movement during standstill | $1.86\text{ m}$ drift prior to ZUPT trigger at $0.08\text{ m/s}$ crawling | **FAIL** | `test_low_speed_safety.py` |
| **Ground-Truth Leakage Protection** | 100% numerical identity under fake reference | **$0.00000000\text{ m}$ difference** across Runs A, B, and C | **PASS** | `test_adversarial_leakage.py` |
| **Numerical Safety** | Bounded predictions in $[0.0, 3.0]$, NaN/Inf robustness | Output head $3.0 \cdot \text{Sigmoid}(h_{64}) \in [0.0, 3.0]$ | **PASS** | `test_model_v2_safeguards.py` |
| **Reproducibility** | All tests pass with zero non-reproducible manual tweaks | Passed 8/8 nav suite + leakage + square + safeguards | **PASS** | `test_nav_suite.py`, `test_model_v2_safeguards.py` |

---

## 2. Production Deployment Recommendation

### **FINAL PRODUCTION DECISION**: **DO NOT DEPLOY MODEL V2 AS DEFAULT PRODUCTION BASELINE**.

### **Enforced Operating Configuration**:
1. **Production Default**:
   ```text
   PERSISTENCE_PRODUCTION
   ```
   - Uses Constant-Speed Persistence ($v = v_{anchor}$) + EKF Velocity Smoothing + Multi-Signal ZUPT + Gyro Kinematics.
   - Guaranteed stable, zero-leakage production baseline.
2. **Diagnostic Evaluation Mode**:
   ```text
   AI_RATIO_DIAGNOSTIC
   ```
   - Uses Model V2 ($v_{AI} = r_{pred} \cdot v_{anchor}$) for non-production evaluation logging.

---

## 3. Explicit Use Case Mapping

- **Conditions Supporting AI Ratio (`AI_RATIO_DIAGNOSTIC`)**:
  - High-speed highway/motorway driving (`IOVNBD_S3c`) over 30s - 120s outages, where Model V2 achieved a **96.09m position error reduction** compared to persistence (470.09m vs 566.18m).
- **Conditions Supporting Persistence (`PERSISTENCE_PRODUCTION`)**:
  - Urban/suburban driving (`IOVNBD_S3a`) with sharp 90° turns and frequent stop-and-go maneuvers, where gyro heading drift dominates position error.
- **Remaining Limitations**:
  - Model V2 requires additional urban stop-and-go training data before it can be considered for full production replacement.
