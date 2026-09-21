import json

with open(r'c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\IOVNBD_AUDIT_TEMP.json') as f:
    data = json.load(f)

print(f"Total Sessions Audited: {len(data)}")
valid_train = [d for d in data if d['suitable_for_ai_speed_training']]
print(f"Sessions suitable for AI speed training: {len(valid_train)}")

print("\nTop 15 Longest Driving Sessions with Paired Vehicle ECU Speed Ground-Truth:")
sorted_sessions = sorted(valid_train, key=lambda x: x['duration_seconds'], reverse=True)
for s in sorted_sessions[:15]:
    sid = s['session_id']
    dcat = s['driver_category']
    dur = s['duration_minutes']
    v_max = s['vehicle_ecu_speed_max_kmh']
    s_rows = s['num_samples_smartphone']
    print(f" -> Session: {sid:12s} | Category: {dcat:25s} | Duration: {dur:6.2f} min | Max ECU Speed: {v_max:6.2f} km/h | Samples: {s_rows}")
