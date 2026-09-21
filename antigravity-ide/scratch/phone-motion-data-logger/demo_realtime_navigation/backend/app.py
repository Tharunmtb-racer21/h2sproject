"""
SIH26168 Intelligent Dead Reckoning System
Module: Application Web Server & REST API

Provides:
- Static UI file serving (HTML, CSS, JS) on http://localhost:8080
- REST API endpoints for playback control, live telemetry, and outage injection:
    GET  /api/status            -> Full system status, active mode, and current telemetry
    GET  /api/telemetry         -> Current frame telemetry, position, speeds, status
    GET  /api/initial_path      -> Complete reference path & session metadata
    POST /api/control           -> Play / Pause / Reset / Rate / Step
    POST /api/outage/trigger    -> Trigger 10s / 30s / 60s / manual outage
    POST /api/outage/restore    -> Restore GNSS signal with Sigmoid blending
    POST /api/session/load      -> Switch dataset session (S3c, S3a, M)
    GET  /api/sensor/status     -> Live sensor receiver health (Next phase stub)
    GET  /api/metrics           -> Verified scientific performance benchmarks
"""

import os
import json
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from .replay_engine import ReplayEngine
from .sensor_receiver import LiveSensorReceiver


class DemoServerState:
    def __init__(self):
        self.replay_engine = ReplayEngine()
        self.live_sensor_receiver = LiveSensorReceiver()
        self.active_mode = "REPLAY"  # REPLAY, SIMULATION, LIVE_SENSOR
        self.lock = threading.Lock()
        self.running = True
        
        # Background streaming loop
        self.bg_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.bg_thread.start()

    def _playback_loop(self):
        """Continuous background tick loop advancing replay when is_playing=True."""
        while self.running:
            with self.lock:
                if self.replay_engine.is_playing:
                    self.replay_engine.step()
            # 20 Hz update rate (0.05s)
            time.sleep(0.05)


server_state = DemoServerState()


class NavigationRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set static assets directory
        static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
        super().__init__(*args, directory=static_dir, **kwargs)

    def _send_json_response(self, data, status_code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/api/status", "/api/telemetry"):
            with server_state.lock:
                frame = server_state.replay_engine.get_current_frame()
                frame["active_mode"] = server_state.active_mode
                frame["session_id"] = server_state.replay_engine.current_session_id
                frame["server_status"] = "ONLINE"
                frame["ai_model_loaded"] = server_state.replay_engine.ai_model_loaded
            self._send_json_response(frame)

        elif path == "/api/initial_path":
            with server_state.lock:
                ref_path = server_state.replay_engine.cached_ref_path
                session_meta = {
                    "session_id": server_state.replay_engine.current_session_id,
                    "total_samples": server_state.replay_engine.total_samples,
                    "ref_path": ref_path,
                }
            self._send_json_response(session_meta)

        elif path == "/api/sensor/status":
            status = server_state.live_sensor_receiver.get_status()
            self._send_json_response(status)

        elif path == "/api/metrics":
            metrics = {
                "velocity_s3c": {
                    "dataset": "IOVNBD_S3c (Held-Out Test)",
                    "rmse_mps": 2.3505,
                    "rmse_kmh": 8.46,
                    "mae_mps": 1.6479,
                    "mae_kmh": 5.93,
                    "r2": 0.9190,
                    "pearson_r": 0.9601,
                },
                "outage_benchmarks": [
                    {
                        "duration_s": 10,
                        "avg_dist_m": 113.11,
                        "ai_rmse_m": 53.71,
                        "persistence_rmse_m": 49.60,
                        "diff_m": "+4.11m (Persistence baseline advantage)",
                    },
                    {
                        "duration_s": 30,
                        "avg_dist_m": 325.77,
                        "ai_rmse_m": 105.52,
                        "persistence_rmse_m": 100.42,
                        "diff_m": "+5.10m (Parity)",
                    },
                    {
                        "duration_s": 60,
                        "avg_dist_m": 634.44,
                        "ai_rmse_m": 131.27,
                        "persistence_rmse_m": 214.94,
                        "diff_m": "-83.67m (38.9% AI error reduction)",
                    },
                ]
            }
            self._send_json_response(metrics)

        else:
            # Serve static files (HTML, CSS, JS)
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path == "/api/control":
            action = payload.get("action")
            with server_state.lock:
                if action == "play":
                    server_state.replay_engine.set_playing(True)
                elif action == "pause":
                    server_state.replay_engine.set_playing(False)
                elif action == "reset":
                    server_state.replay_engine.reset_playback()
                elif action == "rate":
                    rate = payload.get("rate", 1.0)
                    server_state.replay_engine.set_playback_rate(rate)
                elif action == "step":
                    server_state.replay_engine.step(1)
            
            self._send_json_response({"status": "SUCCESS", "action": action})

        elif path == "/api/outage/trigger":
            duration_s = payload.get("duration_s", None)
            with server_state.lock:
                res = server_state.replay_engine.trigger_simulated_outage(duration_s=duration_s)
                server_state.active_mode = "SIMULATION"
            self._send_json_response(res)

        elif path == "/api/outage/restore":
            with server_state.lock:
                res = server_state.replay_engine.restore_gnss()
            self._send_json_response(res)

        elif path == "/api/session/load":
            session_id = payload.get("session_id", "IOVNBD_S3c")
            with server_state.lock:
                try:
                    res = server_state.replay_engine.load_session(session_id)
                    res["status"] = "SUCCESS"
                except Exception as e:
                    res = {"status": "ERROR", "message": str(e)}
            self._send_json_response(res)

        else:
            self._send_json_response({"status": "NOT_FOUND"}, status_code=404)


def run_server(port=8080):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, NavigationRequestHandler)
    print(f"[OK] SIH26168 Real-Time Navigation Server running at: http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping navigation server...")
        server_state.running = False
        httpd.server_close()


if __name__ == "__main__":
    run_server()
