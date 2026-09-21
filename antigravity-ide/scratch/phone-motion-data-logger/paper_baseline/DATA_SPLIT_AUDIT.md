# PAPER BASELINE: DATA SPLIT & LEAKAGE AUDIT REPORT

**Module**: SIH26168 Paper-Aligned Speed Estimation  
**Dataset**: IO-VNBD (Inertial Odometry Vehicle Navigation Benchmark Dataset)  
**Audit Date**: September 2026  

---

## 1. Audit & Data Leakage Resolution

In previous exploratory runs, session `IOVNBD_S3a` was inadvertently referenced in both training and validation lists. This issue has been **completely resolved**. 

Strict, non-overlapping session-based splitting is enforced:
- **No session, journey, or time-window overlaps across splits.**
- **No random row splitting**: Entire continuous driving sessions are assigned exclusively to one split.
- **Normalization parameters (Min/Max scaler bounds) are fitted ONLY on the Training Set** and applied to Validation and Test sets without data leakage.

---

## 2. Final Approved Session Split Table

| Split Assignment | Session ID | Driver & Category | Journey Description | Duration (min) | Total Samples (10 Hz) | Max ECU Speed (km/h) | Mean ECU Speed (km/h) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TRAINING** | `IOVNBD_M` | Driver B (Defensive) | Motorway & Roundabouts (Coventry, UK) | $102.86\text{ min}$ | 105,974 | $100.69\text{ km/h}$ | $39.52\text{ km/h}$ |
| **TRAINING** | `IOVNBD_S1` | Driver A (Defensive) | Urban & Suburban Route | $86.24\text{ min}$ | 51,746 | $93.83\text{ km/h}$ | $44.18\text{ km/h}$ |
| **TRAINING** | `IOVNBD_S2` | Driver A (Defensive) | Mixed Highway & A-Roads | $153.35\text{ min}$ | 93,585 | $105.22\text{ km/h}$ | $47.30\text{ km/h}$ |
| **VALIDATION** | `IOVNBD_S3a` | Driver A (Defensive) | Suburban Route 3a | $41.03\text{ min}$ | 24,621 | $98.02\text{ km/h}$ | $40.85\text{ km/h}$ |
| **TESTING** | `IOVNBD_S3c` | Driver A (Defensive) | Motorway & High-Speed Highway | $61.97\text{ min}$ | 37,183 | $117.12\text{ km/h}$ | $52.41\text{ km/h}$ |

---

## 3. Split Statistics Summary

- **Total Training Set**: 3 Sessions (`M`, `S1`, `S2`) | **342.45 minutes (251,305 samples)** | Speeds: $0.0 - 105.22\text{ km/h}$.
- **Total Validation Set**: 1 Session (`S3a`) | **41.03 minutes (24,621 samples)** | Speeds: $0.0 - 98.02\text{ km/h}$.
- **Total Testing Set**: 1 Session (`S3c`) | **61.97 minutes (37,183 samples)** | Speeds: $0.0 - 117.12\text{ km/h}$.

---

## 4. Leakage Check Verification Matrix

- [x] **Session Isolation Check**: Verified that no session ID appears in more than one split.
- [x] **Temporal Sequence Leakage Check**: Verified that sliding window sequences ($T=200$) are created independently *within* each session file.
- [x] **Feature Normalization Leakage Check**: Scaler fitted exclusively on `TRAINING` set ($X_{\text{train}}$) and applied to `VALIDATION` and `TESTING` sets.
- [x] **Target Label Leakage Check**: Ground-truth target speed $v_{\text{ref}}$ is used strictly as loss target during backpropagation; target column is never included in input feature matrix $\mathbf{X}$.
