# GROUND TRUTH VERIFICATION REPORT: IO-VNBD DATASET

**Documentation Source**: `C:\Users\Keerthana N\Desktop\IO-VNBD\README_1.pdf`  
**Authors**: Uche Onyekpe, Vasile Palade, Stratis Kanarachos, Alicja Szkolnik (*Coventry University, UK*)  

---

## 1. Confirmed Hardware Equipment & Setup

According to Section 2 (*Equipments & Experiment Setup*) of `README_1.pdf`:
1. **Racelogic VBOX Video HD2 CAN-Bus Data Logger (10 Hz)**: Connects directly to the research vehicle CAN bus interface to record vehicle speed, individual wheel speeds, steering angle, gear, brake position, etc.
2. **Racelogic VBOX Video HD2 GPS Antenna (10 Hz)**: Centrally mounted on the top roof of the vehicle (Ford Fiesta Titanium) to provide high-accuracy reference location coordinates (Latitude, Longitude) and course-over-ground heading at 10 Hz.
3. **Smartphone Sensor Application**: AndroSensor application running on smartphone mounted in a rigid holder attached to the vehicle dashboard (sampling IMU at 10 Hz).

---

## 2. Signal Verification Table

| Column Name in Dataset | Physical Meaning Confirmed by Documentation | Hardware Source | Unit | Reliability Status |
| :--- | :--- | :--- | :--- | :--- |
| `Velocity (km/hr)` in `V-*.csv` | **Primary Vehicle Reference Velocity Ground-Truth**. True vehicle forward speed measured via Racelogic VBOX HD2 10 Hz GPS/CAN logger. | Racelogic VBOX Video HD2 Logger (10 Hz) | $\text{km/h}$ | **VERIFIED PRIMARY GROUND TRUTH** |
| `Indicated Vehicle Speed (km/hr)` in `V-*.csv` | Vehicle dashboard speedometer output read directly from CAN bus. Derived from wheel speed sensors; includes speedometer calibration offset. | Vehicle CAN Bus (Ford Fiesta ECU) | $\text{km/h}$ | **VERIFIED SECONDARY REFERENCE** |
| `Wheel Speed Front Left/Right`, `Rear Left/Right` | Individual wheel angular velocities read directly from CAN bus wheel speed encoders. | Vehicle CAN Bus Wheel Encoders | $\text{rad/s}$ | **VERIFIED WHEEL ODOMETRY** |
| `Heading (degrees)` in `V-*.csv` | True vehicle course-over-ground heading angle measured by roof-mounted VBOX GPS antenna. | Racelogic VBOX Video HD2 GPS Antenna | Degrees ($^\circ$) | **VERIFIED HEADING REFERENCE** |
| `Yaw Rate (deg/sec)` in `V-*.csv` | Vehicle body rotational rate around vertical axis read from vehicle stability system / CAN bus. | Vehicle CAN Bus Yaw Rate Sensor | $\text{deg/s}$ | **VERIFIED YAW RATE REFERENCE** |
| `GPS SPEED (Kmh)` in `S-*.csv` | Low-cost smartphone built-in GPS receiver speed. Subject to smartphone GPS drops and urban canyon multipath noise. | Smartphone Internal GPS Receiver | $\text{km/h}$ | **VERIFIED SECONDARY SMARTPHONE METRIC** |

---

## 3. Justification of Target Signal Selection

- **Primary Target Selected**: `reference_speed` derived from vehicle ECU `Velocity (km/hr)` in `V-*.csv`.
- **Rationale**: Measured directly by professional-grade Racelogic VBOX Video HD2 instrumentation (accuracy $\pm 0.1\text{ km/h}$). It is immune to smartphone GPS outages, tilt variations, or indoor signal blockages.
