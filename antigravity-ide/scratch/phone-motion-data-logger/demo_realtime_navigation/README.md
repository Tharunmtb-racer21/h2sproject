# SIH26168 Real-Time Navigation Prototype

Interactive Research Prototype & Demonstration Dashboard for **AI-ML Based Intelligent Dead Reckoning System for Seamless Navigation**.

---

## Quickstart Guide

### 1. Prerequisites
* Python 3.8+
* `numpy`, `pandas` (standard scientific libraries)

### 2. Launching the Dashboard
From the root workspace directory, run:
```bash
python demo_realtime_navigation/run_demo.py
```
This automatically starts the backend server on `http://localhost:8080` and opens your default browser.

To run on a specific port without launching the browser:
```bash
python demo_realtime_navigation/run_demo.py --port 8080 --no-browser
```

---

## Key Features & UI Controls

1. **Playback Controls:**
   * **`▶ PLAY`**: Start real-time trajectory simulation at selected rate ($1\times, 2\times, 5\times$).
   * **`⏸ PAUSE`**: Freeze current position and telemetry.
   * **`⏭ STEP`**: Advance one time-step forward.
   * **`↺ RESET`**: Return to the beginning of the driving session.
2. **Outage Simulation:**
   * **`⚡ 10s / 30s / 60s OUTAGE`**: Instantly trigger simulated GNSS loss. The UI enters `GNSS OUTAGE / DEAD RECKONING` mode with active timer and red trajectory trace.
   * **`🔄 RESTORE GNSS`**: Instantly reconnect GNSS with smooth Sigmoid blending to prevent visual teleportation.
3. **Dataset Session Switching:**
   * Choose between `IOVNBD_S3c` (Highway 117 km/h), `IOVNBD_S3a` (Suburban 87% benchmark), and `IOVNBD_M` (Motorway 102 min).
4. **Live Instrumentation:**
   * **Speedometer:** Dual-needle gauge comparing AI estimated velocity vs true reference speed.
   * **Compass:** Rotating compass card showing true heading angle and cardinal direction.
   * **2D Navigation View:** Real-time East/North metric map with zoom, pan, and vehicle orientation marker.
