# IO-VNBD DATASET INVENTORY

**Dataset Path**: C:\Users\Keerthana N\Desktop\IO-VNBD  
**Dataset Name**: Inertial and Odometry Vehicle Navigation Benchmark Dataset (IO-VNBD)  
**Scope**: Public benchmark dataset recorded in the United Kingdom, France, and Nigeria covering 40+ hours (> 1,300 km) of research vehicle ECU sensors and 58+ hours (> 4,400 km) of Android smartphone 10 Hz IMU telemetry.

---

## 1. Directory Structure & File Counts

- **Total Recursive Files**: 794 files
- **Top-Level Folders**:
  1. SYNCHRONISED_DATA / Synchronised V abd S datasets: 213 pre-synchronized paired CSV files (144 S-V pairs).
  2. Unsynchronised V and S Dataset: 85 raw CSV files categorized by driver (Driver A, B, C, D, E).
  3. Documentation: README.md, README_1.pdf.

---

## 2. Sensor Equipment & Signal Categorization

### A. Smartphone Sensors (S-*.csv @ 10 Hz)
- **Accelerometer**: ACCELEROMETER X/Y/Z ($	ext{m/s}^2$), GRAVITY X/Y/Z ($	ext{m/s}^2$).
- **Gyroscope**: GYROSCOPE Yaw/Pitch/Roll ($	ext{rad/s}$).
- **Magnetometer**: MAGNETIC FIELD X/Y/Z ($\mu	ext{T}$).
- **GNSS**: GPS LATITUDE, GPS LONGITUDE, GPS ALTITUDE (m), GPS SPEED (km/h), GPS ACCURACY (m), GPS ORIENTATION (°), GPS SATELLITES IN RANGE.
- **Timestamp**: TIME SINCE START (ms), DATE (YYYY-MO-DD HH-MI-SS_SSS).

### B. Vehicle ECU / OBD2 Sensors (V-*.csv @ 10 Hz)
- **Velocity Ground-Truth**: Velocity (km/hr) (True GPS/ECU vehicle speed ground truth).
- **Indicated Speed**: Indicated Vehicle Speed (km/hr).
- **Wheel Speeds**: Wheel Speed Front Left/Right, Rear Left/Right ($	ext{rad/sec}$).
- **Kinematics**: Heading (degrees), Yaw Rate (deg/sec), Indicated Longitudinal Acceleration (g), Indicated Lateral Acceleration (g), Steering Angle (degrees).
- **CAN Bus**: Engine Speed (rev/min), Brake Position, Clutch Position, Gear Requested, Gear Employed.

---

## 3. Driver & Scenario Breakdown

- **Driver A** (S category): Journey S1, S2, S3a, S3c, S4 (Mixed motorway & urban driving, UK).
- **Driver B** (M category): Journey M (Motorway & roundabouts, UK).
- **Driver C** (St category): Journey St1 (Stop-and-go urban traffic).
- **Driver E** (Vf, Vta, Vtb, Vw categories): Journeys Vw1 - Vw14 (Country roads & highway driving).
