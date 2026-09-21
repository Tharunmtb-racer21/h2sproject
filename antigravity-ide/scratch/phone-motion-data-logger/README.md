# Phone Motion Data Logger

A complete, zero-cloud LOCALHOST web application that streams **real hardware sensor data** from a physical mobile browser over a local Wi-Fi network to a Node.js backend on a laptop, rendering a live telemetry dashboard and continuously recording every reading to `data/sensor_data.csv`.

> [!IMPORTANT]
> **Strict Genuine Data Guarantee**: This application contains zero simulated, mock, or fake sensor values. Every telemetry metric comes directly from standard browser W3C Sensor & Geolocation APIs. If a sensor is unsupported or permission is denied, it displays `NOT AVAILABLE` and writes empty fields to the CSV file.

---

## 🏗️ System Architecture

```
📱 Physical Phone (Browser)
   ├── Web Sensor APIs (DeviceMotion, DeviceOrientation, Magnetometer, Geolocation)
   ├── Rate Sampler (1, 5, 10, or 20 Hz)
   └── WebSocket Client
          │
          │ (Local Wi-Fi Network JSON Packets)
          ▼
💻 Laptop Node.js Server (0.0.0.0:3001)
   ├── WebSocket Broadcast Hub
   ├── Automatic LAN IP Detection (`os.networkInterfaces()`)
   └── Continuous CSV Writer (`data/sensor_data.csv`)
          │
          ├── 📊 Live Laptop Telemetry Dashboard (React + Vite @ 0.0.0.0:5173)
          └── 📄 CSV File Exporter & Downloader (`/api/download-csv`)
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Node.js (v18 or higher recommended)
- Laptop and Smartphone connected to the **SAME Wi-Fi Network**.

### 2. Install Dependencies
Open terminal in the project directory:
```bash
cd "C:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger"
npm run setup
```

### 3. Start Frontend & Backend
Run the dev server (launches both Express WebSocket backend on port 3001 and Vite frontend on port 5173):
```bash
npm run dev
```

---

## 📱 Physical Phone Setup & Connection

1. **Find Laptop LAN IP**:
   When `npm run dev` starts, look at the terminal output. The server will output your LAN IP:
   ```
   👉 http://192.168.X.X:5173
   ```
2. **Open Phone Browser**:
   Connect your physical Android/iOS phone to the same Wi-Fi as your laptop, open Chrome or Safari, and navigate to:
   ```
   http://192.168.X.X:5173
   ```
3. **Grant Sensor Permissions**:
   - On iOS Safari / modern Chrome, tap **"Grant iOS / Android Sensor Permissions"**.
   - Allow Motion, Orientation, and Location access when prompted by the browser.
4. **Start Telemetry Stream**:
   - Tap **"START STREAMING"**.
   - Select desired sampling rate (Default: `10 Hz`).
   - Move or tilt the phone to observe real-time motion streaming to your laptop!

---

## 📊 Recorded CSV Schema (`data/sensor_data.csv`)

Every reading automatically appends a timestamped row to `data/sensor_data.csv` with the following columns:

```csv
phone_timestamp,server_received_timestamp,accelerometer_x,accelerometer_y,accelerometer_z,accel_nograv_x,accel_nograv_y,accel_nograv_z,gyroscope_alpha,gyroscope_beta,gyroscope_gamma,orientation_alpha,orientation_beta,orientation_gamma,magnetometer_x,magnetometer_y,magnetometer_z,latitude,longitude,altitude,speed,heading,accuracy
```

---

## 🧪 Real-Hardware Test Procedure

Follow these steps with your physical phone to verify real sensor integration:

1. **TEST 1 (Stationary Baseline)**:
   - Place phone flat on a desk.
   - Observe `Accelerometer Z` reading approximately `~9.8 m/s²` (due to Earth's gravity).
   - Observe `Gyroscope (alpha, beta, gamma)` values near `0.0 deg/s`.
2. **TEST 2 (Rotation - Gyroscope)**:
   - Spin the phone on the desk surface around its center.
   - Observe `Gyroscope Alpha (Z-rotation)` spike dynamically in real time on the laptop dashboard.
3. **TEST 3 (Tilt & Motion - Accelerometer & Orientation)**:
   - Tilt phone forward/backward (Pitch / Beta) and left/right (Roll / Gamma).
   - Observe `Orientation Beta/Gamma` and `Accelerometer X/Y` values react immediately to tilt angle.
4. **TEST 4 (Walk - GPS)**:
   - Walk with the phone.
   - If Geolocation permission is granted, watch `speed` and `latitude/longitude` update.
5. **TEST 5 (CSV Output Verification)**:
   - Open `data/sensor_data.csv` on the laptop (or click **"Download CSV"** in the Laptop Dashboard).
   - Confirm that `phone_timestamp`, `server_received_timestamp`, and real sensor measurements are continuously saved.

---

## 🔒 Browser Security & HTTPS Caveats

- **Localhost vs LAN**: On the laptop (`http://localhost:5173`), browsers treat the context as secure, enabling all sensor APIs unconditionally.
- **LAN Access (`http://192.168.X.X:5173`)**: When connecting via HTTP over LAN IP, modern mobile browsers allow `devicemotion` and `deviceorientation` after user permission grant. However, high-accuracy Geolocation or Generic Sensor API (`Magnetometer`) may require HTTPS on strict mobile browser versions. If restricted by your phone browser, the app cleanly marks those specific sensors as `NOT AVAILABLE` without crashing or generating fake values.
