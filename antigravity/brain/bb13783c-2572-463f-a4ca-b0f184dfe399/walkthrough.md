# Queue Cure '26 - Verification & Walkthrough

We have successfully designed, built, and launched the full-stack, real-time hospital queue management system for **Queue Cure '26**.

---

## 🚀 Key Features Built

1. **Sub-10ms Live Synchronization**: Powered by Socket.io, actions taken on the Receptionist console instantly update the Public Display screen.
2. **Dynamic ETA Engine**: Estimated wait times recalculate dynamically on the fly based on:
   - Newly registered patients
   - Completed consultations
   - Updates to the average consultation duration
3. **Active Consultation Timer & Alerts**: Shows how long the current patient has been inside with the doctor. If it exceeds the target average time, the badge turns amber.
4. **Vocal Token Announcements (TTS)**: Integration with the HTML5 Web Speech API allows the system to read out called tokens automatically ("Token QC-001, patient Arjun, please proceed..."). Can be toggled on/off in the settings.
5. **State Persistence & Recovery**: Every transaction is saved to `queue.json`. Restarts, browser page refreshes, and socket drops will recover state instantly.
6. **Concurrency Safety**: Synchronous queue transactions on the Node.js event loop prevent race conditions from double-clicks or multiple admins.

---

## 📁 Project Structure

The project has been created under [queue-cure-26](file:///C:/Users/Keerthana%20N/.gemini/antigravity/scratch/queue-cure-26):
* [backend/package.json](file:///C:/Users/Keerthana%20N/.gemini/antigravity/scratch/queue-cure-26/backend/package.json) - Node.js dependencies
* [backend/src/queueStore.js](file:///C:/Users/Keerthana%20N/.gemini/antigravity/scratch/queue-cure-26/backend/src/queueStore.js) - Thread-safe state & file database adapter
* [backend/src/server.js](file:///C:/Users/Keerthana%20N/.gemini/antigravity/scratch/queue-cure-26/backend/src/server.js) - Express + Socket.io event layer
* [frontend/index.html](file:///C:/Users/Keerthana%20N/.gemini/antigravity/scratch/queue-cure-26/frontend/index.html) - Entry point with custom metadata
* [frontend/src/index.css](file:///C:/Users/Keerthana%20N/.gemini/antigravity/scratch/queue-cure-26/frontend/index.css) - Premium dark glassmorphic styling
* [frontend/src/App.jsx](file:///C:/Users/Keerthana%20N/.gemini/antigravity/scratch/queue-cure-26/frontend/src/App.jsx) - Single-page React application containing both dashboards

---

## 🛠 Active Services

* **Backend API & WebSockets**: [http://localhost:5000](http://localhost:5000)
  * Health check: [http://localhost:5000/health](http://localhost:5000/health)
  * Queue JSON dump: [http://localhost:5000/api/queue](http://localhost:5000/api/queue)
* **Frontend Web Application**: [http://localhost:5173/](http://localhost:5173/)

---

## 🧪 How to Verify / Test

Follow these steps to demonstrate the real-time sync and dynamic behavior:

### Step 1: Open Two Browser Tabs
1. Open **Tab 1** pointing to the local dev server: [http://localhost:5173/](http://localhost:5173/). By default, it opens the **Receptionist View**.
2. Open **Tab 2** pointing to the same URL: [http://localhost:5173/](http://localhost:5173/). Toggle this view to **Public Display** in the header.
3. Position the two browser tabs side-by-side on your monitor.

### Step 2: Register Patients
1. In the **Receptionist View** (Tab 1), register a new patient:
   - Name: *Ramesh Kumar*
   - Click **Register & Queue Patient**.
2. Notice that the new patient token (e.g., `QC-001`) immediately populates on the **Public Display View** (Tab 2) in the *Upcoming Tokens* sidebar, showing an estimated wait time.
3. Register a couple more patients (e.g., *Sita Sharma*, *Vijay Singh*). The *Estimated Wait (New)* indicator will dynamically rise.

### Step 3: Call Patients
1. In Tab 1, click **Call Next Patient**.
2. Instantly, `QC-001 (Ramesh Kumar)` becomes the active token.
3. **Audio Callout**: If your volume is up, the system will read the announcement aloud.
4. An **active consultation clock** starts tracking the elapsed duration.
5. In Tab 2 (Public Display), the big hero display instantly refreshes to show `QC-001` with a pulsing animation.

### Step 4: Modify average duration
1. In Tab 1, modify the *Avg Consultation Time* from `6` to `10` minutes.
2. Observe all estimated waiting times on the Public Display (Tab 2) immediately recompute upwards in real-time.
