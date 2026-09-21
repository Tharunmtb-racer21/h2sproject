# IO-VNBD DATA QUALITY & SELECTION REPORT

## 1. Quality Overview of Standardized Selected Sessions

| Session ID | Duration (min) | Total Samples | Max ECU Speed (km/h) | Mean Speed (km/h) | Moving (min) | Stationary (min) | IMU Nulls | GNSS Nulls |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IOVNBD_M** | 102.93 m | 105974 | 100.69 km/h | 33.47 km/h | 160.02 m | 16.61 m | 0 | 0 |
| **IOVNBD_S1** | 86.24 m | 51746 | 93.83 km/h | 26.4 km/h | 78.11 m | 8.13 m | 0 | 0 |
| **IOVNBD_S2** | 153.35 m | 93585 | 105.22 km/h | 28.21 km/h | 136.45 m | 19.52 m | 0 | 0 |
| **IOVNBD_S3a** | 41.03 m | 24621 | 98.02 km/h | 37.94 km/h | 37.75 m | 3.29 m | 0 | 0 |
| **IOVNBD_S3c** | 61.97 m | 37183 | 117.12 km/h | 42.31 km/h | 57.76 m | 4.21 m | 0 | 0 |

---

## 2. Session Data Assignment & Purpose Mapping Matrix

| Purpose | Selected Session Files | Required Columns | Technical Rationale |
| :--- | :--- | :--- | :--- |
| **AI Speed Training** | `IOVNBD_M`, `IOVNBD_S1`, `IOVNBD_S2`, `IOVNBD_S3a` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, Accel Norm, ECU `reference_speed` | 4 sessions covering 384.48 min (275,926 samples), speeds from 0 to 105.2 km/h across urban, motorway, & roundabout scenarios. |
| **AI Speed Validation** | `IOVNBD_S3a` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, Accel Norm, ECU `reference_speed` | 41.03 min independent session (24,621 samples), suburban driving with frequent speed variation. |
| **AI Speed Testing** | `IOVNBD_S3c` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, Accel Norm, ECU `reference_speed` | Independent session (Driver A) with unseen velocity profile (0 to 117.12 km/h). |
| **GNSS Outage Simulation** | `IOVNBD_M`, `IOVNBD_S2` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, WGS84 Lat/Lon, ECU `reference_speed` | Long continuous driving trajectories (102 min & 153 min) with valid GPS coordinates for 5s, 15s, 30s, 60s blackout tests. |
| **Dead Reckoning Integrator** | `IOVNBD_M`, `IOVNBD_S3c` | Accel X/Y/Z, Gyro Yaw/Pitch/Roll, ECU `reference_heading`, `reference_speed` | Rich rotational yaw dynamics, sharp turns, roundabouts, and straight highway segments. |
| **Navigation Trajectory Eval** | `IOVNBD_M`, `IOVNBD_S2`, `IOVNBD_S3c` | WGS84 Lat/Lon, ECU `reference_heading`, `reference_speed` | Complete WGS84 ground-truth coordinates and course-over-ground angles for trajectory error metrics. |
