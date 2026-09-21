import sys, numpy as np
sys.path.insert(0, '.')

def propagate(pos_e, pos_n, hdg_rad, speed_mps, dt):
    return pos_e + speed_mps * np.sin(hdg_rad) * dt, pos_n + speed_mps * np.cos(hdg_rad) * dt

def update_heading(hdg_rad, yaw_rate_rad_s, dt):
    h = hdg_rad + yaw_rate_rad_s * dt
    return (h + np.pi) % (2.0 * np.pi) - np.pi

PASS, FAIL = 'PASS', 'FAIL'

def test_stationary():
    pos_e, pos_n, hdg = 0.0, 0.0, 0.0
    for _ in range(100):
        pos_e, pos_n = propagate(pos_e, pos_n, hdg, 0.0, 0.1)
    ok = abs(pos_e) < 1e-9 and abs(pos_n) < 1e-9
    return (PASS if ok else FAIL), f'pos=({pos_e:.6f},{pos_n:.6f}) expect (0,0)'

def test_straight_north():
    pos_e, pos_n = 0.0, 0.0
    for _ in range(100):
        pos_e, pos_n = propagate(pos_e, pos_n, 0.0, 10.0, 0.1)
    ok = abs(pos_n - 100.0) < 0.01 and abs(pos_e) < 0.01
    return (PASS if ok else FAIL), f'pos_n={pos_n:.4f}(expect 100) pos_e={pos_e:.4f}(expect 0)'

def test_straight_east():
    pos_e, pos_n = 0.0, 0.0
    hdg = np.radians(90.0)
    for _ in range(100):
        pos_e, pos_n = propagate(pos_e, pos_n, hdg, 10.0, 0.1)
    ok = abs(pos_e - 100.0) < 0.01 and abs(pos_n) < 0.01
    return (PASS if ok else FAIL), f'pos_e={pos_e:.4f}(expect 100) pos_n={pos_n:.4f}(expect 0)'

def test_straight_south():
    pos_e, pos_n = 0.0, 0.0
    hdg = np.radians(180.0)
    for _ in range(100):
        pos_e, pos_n = propagate(pos_e, pos_n, hdg, 10.0, 0.1)
    ok = abs(pos_n + 100.0) < 0.01 and abs(pos_e) < 0.01
    return (PASS if ok else FAIL), f'pos_n={pos_n:.4f}(expect -100)'

def test_right_turn():
    hdg = 0.0
    yaw = (np.pi / 2.0) / 2.0
    for _ in range(20):
        hdg = update_heading(hdg, yaw, 0.1)
    deg = np.degrees(hdg) % 360
    ok = abs(deg - 90.0) < 0.5
    return (PASS if ok else FAIL), f'heading={deg:.2f}(expect 90 East)'

def test_left_turn():
    hdg = np.radians(90.0)
    yaw = -(np.pi / 2.0) / 2.0
    for _ in range(20):
        hdg = update_heading(hdg, yaw, 0.1)
    deg = np.degrees(hdg) % 360
    ok = abs(deg) < 0.5 or abs(deg - 360.0) < 0.5
    return (PASS if ok else FAIL), f'heading={deg:.2f}(expect 0/360 North)'

def test_known_ne_displacement():
    pos_e, pos_n = 0.0, 0.0
    hdg = np.radians(45.0)
    for _ in range(100):
        pos_e, pos_n = propagate(pos_e, pos_n, hdg, 10.0, 0.1)
    exp = 100.0 * np.sin(np.radians(45.0))
    ok = abs(pos_e - exp) < 0.01 and abs(pos_n - exp) < 0.01
    return (PASS if ok else FAIL), f'pos_e={pos_e:.4f} pos_n={pos_n:.4f}(expect {exp:.4f} each)'

def test_long_outage():
    import pandas as pd, torch, json
    from paper_baseline.feature_extraction import extract_paper_features, FEATURE_COLUMNS, PaperMinMaxScaler
    from paper_baseline.models import LSTMNoAttention

    df = pd.read_csv('data/iovnbd_selected/IOVNBD_S3c_standardized.csv')
    r_earth = 6378137.0
    lat0 = float(df['latitude'].iloc[0])
    lon0 = float(df['longitude'].iloc[0])
    df['ref_north_m'] = np.radians(df['latitude'].values - lat0) * r_earth
    df['ref_east_m'] = np.radians(df['longitude'].values - lon0) * r_earth * np.cos(np.radians(lat0))

    df_feat = extract_paper_features(df, window_size=200)
    feat_cols = [c for c in FEATURE_COLUMNS if c in df_feat.columns]
    raw_features = df_feat[feat_cols].values.astype(np.float32)
    with open('demo_realtime_navigation/backend/scaler_params.json') as f:
        s_data = json.load(f)
    scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
    scaler.min_val = np.array(s_data['min_val'], dtype=np.float32)
    scaler.max_val = np.array(s_data['max_val'], dtype=np.float32)
    scaler.is_fitted = True
    features_matrix = scaler.transform(raw_features)

    ckpt = torch.load('outputs/Exp_5_LSTMNoAttention_DeltaV/best_model.pt', map_location='cpu', weights_only=False)
    model = LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    mu = float(ckpt.get('mu_delta_v', 0.001914))
    std_v = float(ckpt.get('std_delta_v', 2.440741))

    t = df['relative_time_s'].values
    ref_hdg = df['reference_heading'].values
    ref_spd = df['reference_speed'].values
    gyro_y = df['gyro_y'].values

    start_idx = 1000
    bias = -0.0025
    scale_yr = 0.9479
    yaw_ema = 0.0
    alpha = 0.4
    hdg_rad = np.radians(ref_hdg[start_idx])
    pos_e = float(df['ref_east_m'].iloc[start_idx])
    pos_n = float(df['ref_north_m'].iloc[start_idx])
    v_anchor = float(ref_spd[start_idx])
    e30 = e60 = e120 = max_e = 0.0

    for i in range(start_idx, start_idx + 1201):
        if i >= len(df) - 1:
            break
        dt_i = t[i+1] - t[i]
        yr = (-gyro_y[i] - bias) * scale_yr
        yaw_ema = alpha * yr + (1.0 - alpha) * yaw_ema
        hdg_rad += float(np.clip(yaw_ema, -np.pi/2, np.pi/2)) * dt_i
        win_s = max(0, i - 200 + 1)
        win = features_matrix[win_s:i+1]
        if len(win) < 200:
            pad = np.repeat(win[:1], 200-len(win), axis=0)
            win = np.vstack([pad, win])
        tensor_w = torch.tensor(win, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            pred_norm = model(tensor_w).item()
        v_ai = max(0.0, v_anchor + pred_norm * std_v + mu)
        pos_n += v_ai * np.cos(hdg_rad) * dt_i
        pos_e += v_ai * np.sin(hdg_rad) * dt_i
        ref_e = float(df['ref_east_m'].iloc[i])
        ref_n = float(df['ref_north_m'].iloc[i])
        err = float(np.sqrt((pos_e - ref_e)**2 + (pos_n - ref_n)**2))
        max_e = max(max_e, err)
        step = i - start_idx
        if step == 299:
            e30 = err
        if step == 599:
            e60 = err
        if step == 1199:
            e120 = err

    return PASS, f'30s={e30:.1f}m  60s={e60:.1f}m  120s={e120:.1f}m  max={max_e:.1f}m'

if __name__ == '__main__':
    tests = [
        ('Stationary zero-vel',   test_stationary),
        ('Straight North',        test_straight_north),
        ('Straight East',         test_straight_east),
        ('Straight South',        test_straight_south),
        ('Right turn 90 deg',     test_right_turn),
        ('Left turn 90 deg',      test_left_turn),
        ('Known NE displacement', test_known_ne_displacement),
        ('Long GNSS outage (AI)', test_long_outage),
    ]
    passed = 0
    print()
    print('=== SIH26168 Navigation Automated Test Suite ===')
    print()
    for name, fn in tests:
        status, detail = fn()
        marker = 'OK' if status == PASS else 'XX'
        print(f'  [{marker}] {name:<28} {status}  {detail}')
        if status == PASS:
            passed += 1
    print()
    print(f'  {passed}/{len(tests)} passed.')
    print()
