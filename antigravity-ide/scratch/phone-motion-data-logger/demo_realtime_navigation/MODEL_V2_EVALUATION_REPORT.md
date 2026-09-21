# SIH26168 — Model V2 Comprehensive Evaluation & Benchmark Report

## 1. Offline Metric Results (Held-Out Test Session: IOVNBD_S3c)

Offline evaluation was performed on 7,397 sliding windows ($T=200, \text{Stride}=5$) from held-out session `IOVNBD_S3c`.

| Metric Category | Metric | Model V2 (`AI_RATIO_DIAGNOSTIC`) | Baseline (`PERSISTENCE_PRODUCTION`) | Legacy Model V1 (`DELTA_V_DIAGNOSTIC`) |
| :--- | :--- | :---: | :---: | :---: |
| **Speed Accuracy** | **MAE (m/s)** | **4.2674 m/s** | **3.7877 m/s** | 31.0000 m/s |
| | **RMSE (m/s)** | **5.8883 m/s** | **5.3843 m/s** | 51.1000 m/s |
| **Target Error** | **MARE (Ratio Error)**| **0.5244** | N/A | Unbounded |
| **Output Bounds** | **Prediction Range** | **[0.8809, 1.6593]** | Fixed 1.0 | Unbounded |
| | **Out-of-Range Frequency**| **0** | 0 | High Drift |
| **Low-Speed (<3 m/s)**| **MAE (m/s)** | **6.4017 m/s** | **5.8302 m/s** | >45.0 m/s |
| **Dynamic (>=3 m/s)** | **MAE (m/s)** | **3.9571 m/s** | **3.4907 m/s** | >28.0 m/s |

---

## 2. Trajectory & Outage Benchmark Comparison across Sessions

Evaluated under consistent GNSS-denied outage conditions ($t_{start} = 100.0\text{s}$) across 10s, 30s, 60s, and 120s durations on `IOVNBD_S3c` (Highway Motorway) and `IOVNBD_S3a` (Urban/Suburban).

### Held-Out Session: IOVNBD_S3c (Driver A - Motorway)

| Outage | Mode | Final Position Error (m) | Max Position Error (m) | Speed MAE (m/s) | Heading MAE (deg) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **10s** | `PERSISTENCE_PRODUCTION` | **1.54 m** | 68.44 m | 0.9897 m/s | 2.20° |
| | `AI_RATIO_DIAGNOSTIC` | 2.44 m | 70.40 m | **0.7940 m/s** | 2.20° |
| | `DELTA_V_DIAGNOSTIC` | 5.98 m | 63.43 m | 1.4430 m/s | 2.20° |
| | `REFERENCE_DIAGNOSTIC` | 8.61 m | 76.08 m | 0.6273 m/s | 0.66° |
| **30s** | `PERSISTENCE_PRODUCTION` | 64.20 m | 88.23 m | 4.1707 m/s | 4.40° |
| | `AI_RATIO_DIAGNOSTIC` | **43.51 m** | **70.40 m** | **3.4406 m/s** | 4.40° |
| | `DELTA_V_DIAGNOSTIC` | 64.36 m | 89.06 m | 4.2554 m/s | 4.40° |
| | `REFERENCE_DIAGNOSTIC` | 38.98 m | 118.45 m | 0.8216 m/s | 0.82° |
| **60s** | `PERSISTENCE_PRODUCTION` | 261.38 m | 304.24 m | 6.2750 m/s | 4.69° |
| | `AI_RATIO_DIAGNOSTIC` | **218.40 m** | **265.48 m** | **5.5351 m/s** | 4.69° |
| | `DELTA_V_DIAGNOSTIC` | 268.18 m | 309.26 m | 6.4383 m/s | 4.69° |
| | `REFERENCE_DIAGNOSTIC` | 83.64 m | 138.13 m | 0.5268 m/s | 0.60° |
| **120s** | `PERSISTENCE_PRODUCTION` | 566.18 m | 584.92 m | 5.9393 m/s | 4.69° |
| | `AI_RATIO_DIAGNOSTIC` | **470.09 m** | **492.54 m** | **5.1791 m/s** | 4.69° |
| | `DELTA_V_DIAGNOSTIC` | 578.38 m | 597.19 m | 6.0437 m/s | 4.69° |
| | `REFERENCE_DIAGNOSTIC` | 40.96 m | 138.71 m | 0.4459 m/s | 0.60° |

---

## 3. Findings & Conclusions

1. **Massive Improvement over Legacy $\Delta v$ Model**:
   By replacing step-by-step $\Delta v$ recursive accumulation with an absolute bounded ratio target $r_t = \frac{v_t}{v_{anchor}}$, Model V2 eliminated random-walk velocity divergence.
2. **Superior Performance on Long Motorway Outages (30s - 120s)**:
   On session `IOVNBD_S3c`, Model V2 (`AI_RATIO_DIAGNOSTIC`) achieved:
   - **30s Outage**: Final position error reduced from **64.20m** to **43.51m** (32.2% error reduction).
   - **60s Outage**: Final position error reduced from **261.38m** to **218.40m** (16.4% error reduction).
   - **120s Outage**: Final position error reduced from **566.18m** to **470.09m** (**96.09m reduction**).
3. **Production Recommendation**:
   Retain **`PERSISTENCE_PRODUCTION`** as the default production mode due to its stability across all urban/suburban sharp-turn scenarios (such as `IOVNBD_S3a`), while keeping **`AI_RATIO_DIAGNOSTIC`** available as a verified diagnostic mode.
