import pandas as pd
import numpy as np
from demo_realtime_navigation.backend.drift_corrector import SafeStandstillDetector

df = pd.read_csv("data/iovnbd_selected/IOVNBD_S3c_standardized.csv")
ax = df["accel_x"].values
ay = df["accel_y"].values
az = df["accel_z"].values
gx = df["gyro_x"].values
gy = df["gyro_y"].values
gz = df["gyro_z"].values
ref_v = df["reference_speed"].values

for persist in [5, 8, 10]:
    zupt = SafeStandstillDetector(window_size=10, accel_var_thresh=0.015, gyro_mag_thresh=0.02, persist_steps=persist)
    triggers = []
    for k in range(1200):
        idx = 100 + k
        is_st = zupt.update(ax[idx], ay[idx], az[idx], gx[idx], gy[idx], gz[idx])
        if is_st:
            triggers.append((idx, idx * 0.1, ref_v[idx]))

    print(f"\n=======================================================")
    print(f"PERSIST_STEPS = {persist} (accel_var_thresh=0.015, gyro_mag_thresh=0.02)")
    print(f"Total Triggers: {len(triggers)}")
    if len(triggers) == 0:
        continue
    df_trig = pd.DataFrame(triggers, columns=["idx", "time_s", "ref_speed"])
    df_trig["gap"] = df_trig["idx"].diff() > 1
    df_trig["episode"] = df_trig["gap"].cumsum()

    for ep_id, group in df_trig.groupby("episode"):
        t_start = group["time_s"].iloc[0]
        t_end = group["time_s"].iloc[-1]
        dur = round(t_end - t_start + 0.1, 2)
        mean_speed = group["ref_speed"].mean()
        max_speed = group["ref_speed"].max()
        print(f"  Episode {ep_id+1}: [{t_start:5.1f}s - {t_end:5.1f}s] ({dur:4.1f}s, {len(group):3d} pts) | Mean GT Speed: {mean_speed:6.3f} m/s | Max GT Speed: {max_speed:6.3f} m/s")
