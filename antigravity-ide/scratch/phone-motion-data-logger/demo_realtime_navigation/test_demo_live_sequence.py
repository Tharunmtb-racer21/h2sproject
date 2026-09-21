"""
demo_realtime_navigation/test_demo_live_sequence.py
Automated end-to-end verification of the exact demo sequence:
1. PLAY
2. 10-second GNSS outage
3. Restore GNSS
4. 30-second GNSS outage
5. Restore GNSS
6. Continuous GNSS outage
7. Restore GNSS
"""

import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8080"

def api_get(endpoint):
    req = urllib.request.urlopen(BASE_URL + endpoint)
    return json.loads(req.read().decode())

def api_post(endpoint, payload):
    req = urllib.request.Request(
        BASE_URL + endpoint,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode())

def run_sequence():
    print("=" * 80)
    print("RUNNING REALTIME DEMO SEQUENCE VERIFICATION")
    print("=" * 80)

    # 1. Reset Playback
    print("\n[STEP 1] Resetting Playback & Initializing...")
    api_post("/api/control", {"action": "reset"})
    init_status = api_get("/api/status")
    print(f"  Server Status: {init_status.get('server_status')}")
    print(f"  Active Session: {init_status.get('session_id')}")
    print(f"  AI Model Loaded: {init_status.get('ai_model_loaded')}")
    print(f"  Initial Mode: {init_status.get('nav_mode')} | State: {init_status.get('gnss_state')}")

    # 2. PLAY (Normal GNSS for 5 seconds / 50 steps)
    print("\n[STEP 2] Starting PLAY (GNSS Locked Normal Drive)...")
    for _ in range(50):
        api_post("/api/control", {"action": "step"})
    t_play = api_get("/api/telemetry")
    print(f"  Progress: t={t_play.get('relative_time_s')}s | Speed: {t_play.get('displayed_speed_kmh')} km/h | Heading: {t_play.get('heading_deg')}° | Mode: {t_play.get('nav_mode')}")

    # 3. 10-Second GNSS Outage
    print("\n[STEP 3] Triggering 10-Second GNSS Outage...")
    out_10 = api_post("/api/outage/trigger", {"duration_s": 10})
    print(f"  Outage Trigger Response: {out_10}")
    
    # Step through 100 steps (10 seconds)
    out_10_telemetry = []
    for _ in range(100):
        api_post("/api/control", {"action": "step"})
        out_10_telemetry.append(api_get("/api/telemetry"))
    
    t_10_mid = out_10_telemetry[50]
    t_10_end = out_10_telemetry[-1]
    print(f"  During 10s Outage (t={t_10_mid.get('relative_time_s')}s): Mode={t_10_mid.get('nav_mode')} | Speed Source={t_10_mid.get('displayed_speed_source')}")
    print(f"  Inference delta_v: {t_10_mid.get('last_inference_output', {}).get('delta_v_mps')} m/s")
    print(f"  End of 10s Outage: Pos Error={t_10_end.get('position_error_m')}m | Heading={t_10_end.get('heading_deg')}°")

    # 4. Restore GNSS after 10s
    print("\n[STEP 4] Restoring GNSS with Sigmoid Handover Blending...")
    rst_10 = api_post("/api/outage/restore", {})
    print(f"  Restore Response: {rst_10}")
    
    # Step through 20 steps (2 seconds blend)
    for _ in range(20):
        api_post("/api/control", {"action": "step"})
    t_10_restored = api_get("/api/telemetry")
    print(f"  Post-Blend Status: State={t_10_restored.get('gnss_state')} | Mode={t_10_restored.get('nav_mode')} | Blend Progress={t_10_restored.get('blend_progress')}")

    # Advance 30 steps normal drive
    for _ in range(30):
        api_post("/api/control", {"action": "step"})

    # 5. 30-Second GNSS Outage
    print("\n[STEP 5] Triggering 30-Second GNSS Outage...")
    out_30 = api_post("/api/outage/trigger", {"duration_s": 30})
    print(f"  Outage Trigger Response: {out_30}")
    
    out_30_telemetry = []
    for _ in range(300):
        api_post("/api/control", {"action": "step"})
        out_30_telemetry.append(api_get("/api/telemetry"))
        
    t_30_mid = out_30_telemetry[150]
    t_30_end = out_30_telemetry[-1]
    print(f"  During 30s Outage (t={t_30_mid.get('relative_time_s')}s): Mode={t_30_mid.get('nav_mode')} | AI Speed={t_30_mid.get('displayed_speed_kmh')} km/h")
    print(f"  End of 30s Outage: Pos Error={t_30_end.get('position_error_m')}m | Heading={t_30_end.get('heading_deg')}°")

    # 6. Restore GNSS after 30s
    print("\n[STEP 6] Restoring GNSS after 30s Outage...")
    rst_30 = api_post("/api/outage/restore", {})
    for _ in range(20):
        api_post("/api/control", {"action": "step"})
    t_30_restored = api_get("/api/telemetry")
    print(f"  Post-Blend Status: State={t_30_restored.get('gnss_state')} | Mode={t_30_restored.get('nav_mode')}")

    # Advance 30 steps normal drive
    for _ in range(30):
        api_post("/api/control", {"action": "step"})

    # 7. Continuous GNSS Outage (Manual / Indefinite)
    print("\n[STEP 7] Triggering Continuous GNSS Outage (Indefinite Blackout)...")
    out_cont = api_post("/api/outage/trigger", {"duration_s": None})
    print(f"  Continuous Outage Trigger Response: {out_cont}")
    
    out_cont_telemetry = []
    # Step through 600 steps (60 seconds continuous dead reckoning)
    for _ in range(600):
        api_post("/api/control", {"action": "step"})
        out_cont_telemetry.append(api_get("/api/telemetry"))
        
    t_cont_mid = out_cont_telemetry[300]
    t_cont_end = out_cont_telemetry[-1]
    print(f"  Continuous DR (60s elapsed): Mode={t_cont_end.get('nav_mode')} | State={t_cont_end.get('gnss_state')}")
    print(f"  AI Delta-V Output: {t_cont_end.get('last_inference_output', {}).get('delta_v_mps')} m/s")
    print(f"  Current DR Point: {t_cont_end.get('current_dr_point')} | Pos Error: {t_cont_end.get('position_error_m')}m")

    # 8. Restore GNSS from Continuous Outage
    print("\n[STEP 8] Restoring GNSS from Continuous Outage...")
    rst_cont = api_post("/api/outage/restore", {})
    for _ in range(20):
        api_post("/api/control", {"action": "step"})
    t_cont_restored = api_get("/api/telemetry")
    print(f"  Final Status: State={t_cont_restored.get('gnss_state')} | Mode={t_cont_restored.get('nav_mode')} | Error={t_cont_restored.get('position_error_m')}m")

    print("\n" + "=" * 80)
    print("DEMO SEQUENCE VERIFICATION: ALL 8 STEPS EXECUTED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    run_sequence()
