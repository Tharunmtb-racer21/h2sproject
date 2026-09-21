# PAPER BASELINE IO-VNBD DATA PREPARATION REPORT

**Paper Target**: *Deep Learning-Based Vehicle Speed Estimation Using Smartphone Sensors in GNSS-Denied Environment* (Shin et al., 2025).

--- 

## 1. Selected Dataset & Strict Session Split

- **Train Journeys (3 Sessions, 342.45 min, 251,305 samples at 10 Hz)**:
  - `IOVNBD_M_standardized.csv` (Driver B, Motorway/Urban, 102.86 min)
  - `IOVNBD_S1_standardized.csv` (Driver A, Urban/Suburban, 86.24 min)
  - `IOVNBD_S2_standardized.csv` (Driver A, Mixed Highway, 153.35 min)

- **Validation Journey (1 Session, 41.03 min, 24,621 samples at 10 Hz)**:
  - `IOVNBD_S3a_standardized.csv` (Driver A, Suburban, 41.03 min)

- **Test Journey (1 Session, 61.97 min, 37,183 samples at 10 Hz)**:
  - `IOVNBD_S3c_standardized.csv` (Driver A, Motorway/Highway, max speed 117.1 km/h)

--- 

## 2. Sensor & Target Mapping

- **Input Features (D = 21)**:
  - 7 Raw Features: `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`, `accel_mag` (m/s^2 & rad/s).
  - 14 Rolling Statistical Features: Backward-looking rolling mean ($\mu$) and rolling sample variance ($\sigma^2$) over window $T=200$.
- **Target Variable**: `reference_speed` (converted to m/s from vehicle ECU `Velocity (km/hr)`).
- **Sampling Grid & Resampling**: Resampled to **50 Hz** ($dt = 20\text{ ms}$) grid.
- **Sequence Length**: $T = 200$ timesteps (**4.0 seconds** at 50 Hz).
