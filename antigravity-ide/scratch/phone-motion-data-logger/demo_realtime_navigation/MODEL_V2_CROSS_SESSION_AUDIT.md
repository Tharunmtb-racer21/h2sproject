# SIH26168 — Model V2 Cross-Session Validation & Audit Report

## 1. Methodology & Benchmark Configuration

Cross-session evaluation was conducted under strictly identical operating conditions across two benchmark datasets:
- **`IOVNBD_S3c`**: Held-out test drive (Driver A - Motorway / Highway, 0 to 117.1 km/h).
- **`IOVNBD_S3a`**: Validation drive (Driver A - Urban / Suburban with 90° turns).

### Enforced Standardized Conditions:
- **Outage Start Timestamp**: $t = 100.0\text{s}$ ($1000^{\text{th}}$ sample)
- **Playback Frequency**: $10\text{ Hz}$ ($dt = 0.1\text{s}$)
- **Sliding Feature Window**: $T=200$ samples ($4.0\text{s}$) @ 50 Hz resampled IMU rates
- **Denominator Safeguard**: $\max(v_{anchor}, 1.0\text{ m/s})$
- **Speed Bounds**: $r_{pred} \in [0.0, 3.0]$
- **Coordinate Conversion**: Local ENU spherical Earth projection centered on initial session fix $(Lat_0, Lon_0)$.

---

## 2. Reconciled Metric Table

| Session | Outage Horizon | Operating Mode | Final Pos Error (m) | Max Pos Error (m) | Speed MAE (m/s) | Heading MAE (deg) | Ground-Truth Ref Leakage |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **`IOVNBD_S3c`** | **10s** | `PERSISTENCE_PRODUCTION` | **1.54 m** | 68.44 m | 0.9897 m/s | 2.20° | NONE |
| | | `AI_RATIO_DIAGNOSTIC` | 2.44 m | 70.40 m | **0.7940 m/s** | 2.20° | NONE |
| | | `DELTA_V_DIAGNOSTIC` | 5.98 m | 63.43 m | 1.4430 m/s | 2.20° | NONE |
| | | `REFERENCE_DIAGNOSTIC` | 8.61 m | 76.08 m | 0.6273 m/s | 0.66° | EVAL ONLY |
| **`IOVNBD_S3c`** | **30s** | `PERSISTENCE_PRODUCTION` | 64.20 m | 88.23 m | 4.1707 m/s | 4.40° | NONE |
| | | `AI_RATIO_DIAGNOSTIC` | **43.51 m** | **70.40 m** | **3.4406 m/s** | 4.40° | NONE |
| | | `DELTA_V_DIAGNOSTIC` | 64.36 m | 89.06 m | 4.2554 m/s | 4.40° | NONE |
| | | `REFERENCE_DIAGNOSTIC` | 38.98 m | 118.45 m | 0.8216 m/s | 0.82° | EVAL ONLY |
| **`IOVNBD_S3c`** | **60s** | `PERSISTENCE_PRODUCTION` | 261.38 m | 304.24 m | 6.2750 m/s | 4.69° | NONE |
| | | `AI_RATIO_DIAGNOSTIC` | **218.40 m** | **265.48 m** | **5.5351 m/s** | 4.69° | NONE |
| | | `DELTA_V_DIAGNOSTIC` | 268.18 m | 309.26 m | 6.4383 m/s | 4.69° | NONE |
| | | `REFERENCE_DIAGNOSTIC` | 83.64 m | 138.13 m | 0.5268 m/s | 0.60° | EVAL ONLY |
| **`IOVNBD_S3c`** | **120s** | `PERSISTENCE_PRODUCTION` | 566.18 m | 584.92 m | 5.9393 m/s | 4.69° | NONE |
| | | `AI_RATIO_DIAGNOSTIC` | **470.09 m** | **492.54 m** | **5.1791 m/s** | 4.69° | NONE |
| | | `DELTA_V_DIAGNOSTIC` | 578.38 m | 597.19 m | 6.0437 m/s | 4.69° | NONE |
| | | `REFERENCE_DIAGNOSTIC` | 40.96 m | 138.71 m | 0.4459 m/s | 0.60° | EVAL ONLY |
| **`IOVNBD_S3a`** | **10s** | `PERSISTENCE_PRODUCTION` | 12.19 m | 70.72 m | **2.7117 m/s** | 17.77° | NONE |
| | | `AI_RATIO_DIAGNOSTIC` | **8.61 m** | 81.76 m | 3.9426 m/s | 17.77° | NONE |
| | | `DELTA_V_DIAGNOSTIC` | 12.86 m | 70.28 m | 2.6402 m/s | 17.77° | NONE |
| | | `REFERENCE_DIAGNOSTIC` | 52.82 m | 59.66 m | 0.7940 m/s | 0.61° | EVAL ONLY |
| **`IOVNBD_S3a`** | **30s** | `PERSISTENCE_PRODUCTION` | **40.12 m** | **86.79 m** | **2.4517 m/s** | 20.75° | NONE |
| | | `AI_RATIO_DIAGNOSTIC` | 69.09 m | 111.02 m | 2.5525 m/s | 20.75° | NONE |
| | | `DELTA_V_DIAGNOSTIC` | 34.31 m | 81.22 m | 2.5113 m/s | 20.75° | NONE |
| | | `REFERENCE_DIAGNOSTIC` | 43.95 m | 77.98 m | 0.6709 m/s | 0.65° | EVAL ONLY |
| **`IOVNBD_S3a`** | **60s** | `PERSISTENCE_PRODUCTION` | **34.45 m** | **86.79 m** | 2.7390 m/s | 17.75° | NONE |
| | | `AI_RATIO_DIAGNOSTIC` | 53.91 m | 121.36 m | **2.3616 m/s** | 17.75° | NONE |
| | | `DELTA_V_DIAGNOSTIC` | 42.81 m | 94.33 m | 2.9180 m/s | 17.75° | NONE |
| | | `REFERENCE_DIAGNOSTIC` | 41.22 m | 85.12 m | 0.7102 m/s | 0.62° | EVAL ONLY |

---

## 3. Reconciliation Analysis of Discrepancies

- **Explanation of Discrepancy between earlier reports and Model V2 report**:
  - Earlier reports (`reconcile_benchmarks.py`) evaluated persistence without the $25\text{ m/s}$ pre-outage physical speed cap or using raw kinematic unrolling.
  - `compare_speed_models.py` uses `ReplayEngine`'s full live state pipeline including EKF velocity smoothing, pre-outage speed capping, and multi-signal ZUPT.
- **Cross-Session Variance**:
  - Model V2 achieves significant position error reductions on straight motorway driving (`IOVNBD_S3c` 120s: **470.09m** vs **566.18m** persistence error).
  - On urban turning drives (`IOVNBD_S3a`), gyro heading drift ($17.75^\circ - 20.75^\circ$) dominates position error, making Constant-Speed Persistence slightly more stable (**34.45m** vs **53.91m** error at 60s).

---

## 4. Ground-Truth Leakage Audit Verification

The 3-run adversarial leakage suite (`test_adversarial_leakage.py`) executed with **100% numerical identity ($0.00000000\text{ m}$ difference)** across:
- **Run A**: Normal ground-truth telemetry
- **Run B**: NaN-corrupted reference telemetry during outage
- **Run C**: Adversarial fake telemetry ($+10\text{km}$ pos, $3\text{x}$ speed, $+180^\circ$ heading)

**Conclusion**: Neither `PERSISTENCE_PRODUCTION` nor `AI_RATIO_DIAGNOSTIC` leaks ground-truth reference values into model inputs or state propagation.
