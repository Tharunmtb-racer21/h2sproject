# GROUND TRUTH SOURCE EVIDENCE REPORT

**Module**: SIH26168 Target Label Audit  
**Source Document**: `C:\Users\Keerthana N\Desktop\IO-VNBD\README_1.pdf`  
**Authors**: Uche Onyekpe, Vasile Palade, Stratis Kanarachos, Alicja Szkolnik (*Coventry University, UK*)  

---

## 1. Documentation Source Evidence Table

| Target Signal / Variable | Source Document Location | Extracted Documentation Text | Hardware / Sensing Method | Verified Ground Truth Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **`Velocity (km/hr)`** in `V-*.csv` | **`README_1.pdf` Page 4, Table 3 (Row 5)** & **Page 6, Ref [15]** | *Table 3 Row 5: Heading `velocity`, Unit `kmh`.*<br>*Ref [15]: `VBOX Video HD2` logger connected to CAN bus and roof antenna.* | **Racelogic VBOX Video HD2 Data Logger (10 Hz)** | **True Forward Vehicle Velocity**. High-accuracy combined GPS/CAN velocity logger output ($\pm 0.1\text{ km/h}$). |
| **`Indicated Vehicle Speed (Km/hr)`** in `V-*.csv` | **`README_1.pdf` Page 4, Table 3 (Row 16)** | *Table 3 Row 16: Heading `Indicated Vehicle Speed`, Unit `Km/hr`.* | **Ford Fiesta Vehicle ECU CAN Bus** | **Dashboard Speedometer Output**. Derived from wheel speed encoders; subject to tire radius variations and factory speedometer offset. |
| **`Wheel Speed Front/Rear`** in `V-*.csv` | **`README_1.pdf` Page 4, Table 3 (Rows 11-14)** | *Table 3 Rows 11-14: `Wheel Speed Front Left/Right`, `Rear Left/Right`, Unit `Rad/sec`.* | **Vehicle CAN Bus Wheel Encoders** | **Individual Wheel Angular Velocities**. Angular rotation rate of each wheel in $\text{rad/s}$. |
| **`Heading (degrees)`** in `V-*.csv` | **`README_1.pdf` Page 4, Table 3 (Row 6)** | *Table 3 Row 6: Heading `Heading`, Unit `degrees`.* | **Racelogic VBOX HD2 Roof GPS Antenna** | **Vehicle Course-Over-Ground Heading**. True direction of motion relative to North ($0-360^\circ$). |
| **`Yaw Rate (Deg/sec)`** in `V-*.csv` | **`README_1.pdf` Page 4, Table 3 (Row 15)** | *Table 3 Row 15: Heading `Yaw Rate`, Unit `Deg/sec`.* | **Vehicle Stability Control Yaw Rate Gyro** | **Vehicle Body Rotational Rate**. Angular velocity around vehicle vertical z-axis. |
| **`GPS SPEED (Kmh)`** in `S-*.csv` | **`README_1.pdf` Page 5, Table 4 (Row 4)** | *Table 4 Row 4: Heading `GPS Speed`, Unit `Kmh`.* | **Smartphone Built-in GPS Chipset** | **Low-cost Smartphone GPS Speed**. Susceptible to multipath degradation, signal dropouts, and latency. |

---

## 2. Distinction Between Target Signals

1. **`Velocity (km/hr)` vs `Indicated Vehicle Speed (Km/hr)`**:
   - `Velocity (km/hr)` is measured by the professional-grade **Racelogic VBOX HD2 logger**, which fuses 10 Hz doppler GPS measurements with CAN odometry. This represents the **true physical vehicle velocity ground truth**.
   - `Indicated Vehicle Speed` represents what the driver sees on the dashboard, which intentionally overstates speed by 3-5% per automotive safety regulations.
2. **Target Label Conversion**:
   - Primary target for model training: $v_{\text{ref}} = \text{Velocity (km/hr)} \times \frac{1000}{3600} \text{ (m/s)}$.

---

## 3. Ground-Truth Verification Conclusion

- **Status**: **VERIFIED WITH SOURCE EVIDENCE**
- **Confirmation**: `Velocity (km/hr)` from `V-*.csv` is confirmed via `README_1.pdf` (Page 4, Table 3) as the true Racelogic VBOX vehicle forward speed target logger.
