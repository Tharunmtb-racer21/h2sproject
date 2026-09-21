"""
SIH26168 Intelligent Dead Reckoning System
Module: Replay Engine & Dataset Streamer (Direct PyTorch Neural Model Integration)

Handles:
- Loading standardized IO-VNBD benchmark sessions (S3c, S3a, M)
- Extracting 21 paper-aligned IMU features (7 raw + 14 rolling statistical moments)
- Executing actual PyTorch LSTMNoAttention forward pass inference (best_model.pt)
- Velocity reconstruction: v_reconstructed = v_anchor + sum(predicted delta_v)
- Kinematic 2D Dead Reckoning (ENU Frame) under simulated continuous/timed outages
- Zero-Velocity Updates (ZUPT) and non-negative clamping: max(0, v)
"""

import os
import time
import numpy as np
import pandas as pd
import torch
from .navigation_core import NavigationCore
from .outage_controller import OutageController, GNSSState
from .drift_corrector import NonHolonomicConstraint, SafeStandstillDetector, VelocityEKF
from paper_baseline.feature_extraction import extract_paper_features, FEATURE_COLUMNS, PaperMinMaxScaler


class ReplayEngine:
    def __init__(self, data_dir=None, model_path=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if data_dir is None:
            self.data_dir = os.path.join(base_dir, "data", "iovnbd_selected")
        else:
            self.data_dir = data_dir

        if model_path is None:
            self.model_path = os.path.join(base_dir, "outputs", "Exp_5_LSTMNoAttention_DeltaV", "best_model.pt")
        else:
            self.model_path = model_path

        self.available_sessions = {
            "IOVNBD_S3c": "IOVNBD_S3c_standardized.csv",
            "IOVNBD_S3a": "IOVNBD_S3a_standardized.csv",
            "IOVNBD_M": "IOVNBD_M_standardized.csv",
        }

        self.current_session_id = "IOVNBD_S3c"
        self.df = None
        self.features_matrix = None
        self.total_samples = 0
        self.current_index = 0
        
        # Playback state
        self.is_playing = False
        self.playback_rate = 1.0
        self.target_fps = 20.0
        self.dt = 0.05
        
        # Navigation & Outage sub-engines
        self.nav_core = NavigationCore()
        self.outage_controller = OutageController(blend_duration_s=2.0)
        
        # Modular Drift Reduction (Pure IMU Invariants & Zero Leakage)
        self.nhc = NonHolonomicConstraint(damping_strength=0.95)
        self.zupt = SafeStandstillDetector(window_size=10, accel_var_thresh=0.015, gyro_mag_thresh=0.02, persist_steps=8)
        self.ekf = VelocityEKF()
        
        # Precomputed/cached full ground truth path for canvas
        self.cached_ref_path = []
        self.cached_dr_path = []
        
        # Online Gyroscope Heading Calibration (bias + scale)
        self.gyro_bias_samples = []           # circular buffer for median-bias estimation
        self.online_gyro_bias = 0.0           # median yaw-rate bias (rad/s)
        self.yaw_scale_numerator = 0.0        # LSQ numerator for scale: sum(g_db * ref_yr)
        self.yaw_scale_denominator = 1e-9     # LSQ denominator: sum(g_db^2)
        self.online_yaw_scale = 1.0           # calibrated yaw rate scale factor
        self.yaw_rate_ema = 0.0               # exponential moving average of yaw rate
        self.yaw_ema_alpha = 0.4              # EMA weight (0=smooth, 1=raw)

        # Pre-Outage Speed History (for physics-based velocity cap during dead reckoning)
        self.pre_outage_speed_history = []    # rolling buffer of ref speeds while GNSS locked
        self.pre_outage_speed_cap = 30.0      # m/s — max plausible speed from last GNSS window
        self.dr_imu_speed = 0.0              # IMU-integrated speed (accel_x integration)
        self.dr_imu_speed_ema = 0.0          # EMA of IMU speed for smoothing
        
        # PyTorch Neural Model Checkpoint details
        self.ai_model = None
        self.ai_model_loaded = False
        self.mu_delta_v = 0.001914
        self.std_delta_v = 2.440741
        self.last_inference_output = None
        self.checkpoint_epoch = 1
        self._load_pytorch_model()

        # Load default session
        self.load_session("IOVNBD_S3c")

    def _load_pytorch_model(self):
        """Load trained Exp_5 PyTorch neural network checkpoint."""
        try:
            if os.path.exists(self.model_path):
                from paper_baseline.models import LSTMNoAttention
                ckpt = torch.load(self.model_path, map_location="cpu", weights_only=False)
                self.ai_model = LSTMNoAttention(input_dim=21, hidden_dim=128, num_layers=2)
                self.ai_model.load_state_dict(ckpt["model_state_dict"])
                self.ai_model.eval()
                self.ai_model_loaded = True
                self.mu_delta_v = float(ckpt.get("mu_delta_v", 0.001914))
                self.std_delta_v = float(ckpt.get("std_delta_v", 2.440741))
                self.checkpoint_epoch = int(ckpt.get("epoch", 1))
                print(f"[OK] PyTorch Neural Model initialized: Epoch={self.checkpoint_epoch}, mu={self.mu_delta_v:.4f}, std={self.std_delta_v:.4f}")
        except Exception as e:
            print(f"[INFO] PyTorch model load notice: {e}")
            self.ai_model_loaded = False

    def load_session(self, session_id):
        """Load, prepare, and extract 21 IMU features for a benchmark session."""
        if session_id not in self.available_sessions:
            raise ValueError(f"Unknown session {session_id}. Available: {list(self.available_sessions.keys())}")

        filename = self.available_sessions[session_id]
        filepath = os.path.join(self.data_dir, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dataset file not found at: {filepath}")

        # 1. Load CSV
        self.df = pd.read_csv(filepath)
        self.current_session_id = session_id
        self.total_samples = len(self.df)
        self.current_index = 0
        self.is_playing = False

        # 2. Extract 21 Paper Features (7 raw + 14 rolling stats)
        df_feat = extract_paper_features(self.df, window_size=200)
        feat_cols = [c for c in FEATURE_COLUMNS if c in df_feat.columns]
        raw_features = df_feat[feat_cols].values.astype(np.float32)  # shape (N, 21)

        # Apply strictly training-fitted PaperMinMaxScaler to match Exp_5 training
        scaler_json_path = os.path.join(os.path.dirname(__file__), "scaler_params.json")
        if os.path.exists(scaler_json_path):
            import json
            with open(scaler_json_path, "r") as f:
                s_data = json.load(f)
            scaler = PaperMinMaxScaler(feature_range=(0.0, 1.0))
            scaler.min_val = np.array(s_data["min_val"], dtype=np.float32)
            scaler.max_val = np.array(s_data["max_val"], dtype=np.float32)
            scaler.is_fitted = True
            self.features_matrix = scaler.transform(raw_features)
        else:
            self.features_matrix = raw_features

        # 3. Precompute origin coordinates for Local ENU conversion
        lat0 = float(self.df["latitude"].iloc[0])
        lon0 = float(self.df["longitude"].iloc[0])
        heading0 = float(self.df["reference_heading"].iloc[0])

        r_earth = 6378137.0
        d_lat_rad = np.radians(self.df["latitude"].values - lat0)
        d_lon_rad = np.radians(self.df["longitude"].values - lon0)
        
        self.df["ref_north_m"] = d_lat_rad * r_earth
        self.df["ref_east_m"] = d_lon_rad * r_earth * np.cos(np.radians(lat0))

        # Reset navigation sub-engines
        self.nav_core.reset(origin_lat=lat0, origin_lon=lon0, origin_heading_deg=heading0)
        self.outage_controller.reset()

        # Build full reference path cache
        sample_step = max(1, len(self.df) // 2000)
        self.cached_ref_path = [
            [round(float(e), 2), round(float(n), 2)]
            for e, n in zip(self.df["ref_east_m"].iloc[::sample_step], self.df["ref_north_m"].iloc[::sample_step])
        ]
        
        self.cached_dr_path = []
        return {
            "session_id": self.current_session_id,
            "total_samples": self.total_samples,
            "duration_s": round(float(self.df["relative_time_s"].iloc[-1]), 1) if "relative_time_s" in self.df.columns else round(self.total_samples * 0.1, 1),
            "origin_lat": lat0,
            "origin_lon": lon0,
            "origin_heading": heading0,
        }

    def infer_neural_delta_v(self, current_idx, window_len=200):
        """
        Execute actual PyTorch forward pass on sliding 200-timestep IMU window.
        Returns predicted delta_v in m/s.
        """
        if not self.ai_model_loaded or self.features_matrix is None:
            return 0.0

        # Construct sliding window [current_idx - window_len + 1 : current_idx + 1]
        start_idx = max(0, current_idx - window_len + 1)
        win = self.features_matrix[start_idx : current_idx + 1]

        # Zero-pad if at very beginning of drive
        if len(win) < window_len:
            pad = np.repeat(win[:1], window_len - len(win), axis=0)
            win = np.vstack([pad, win])

        tensor_win = torch.tensor(win, dtype=torch.float32).unsqueeze(0)  # shape (1, 200, 21)
        
        with torch.no_grad():
            pred_norm = self.ai_model(tensor_win).item()

        # De-standardize delta_v: y = y_norm * std + mu
        delta_v_mps = pred_norm * self.std_delta_v + self.mu_delta_v
        self.last_inference_output = {
            "norm_output": round(float(pred_norm), 6),
            "delta_v_mps": round(float(delta_v_mps), 4),
            "window_shape": list(tensor_win.shape),
        }
        return delta_v_mps

    def reset_playback(self):
        """Reset replay pointer to beginning."""
        self.current_index = 0
        self.is_playing = False
        lat0 = float(self.df["latitude"].iloc[0])
        lon0 = float(self.df["longitude"].iloc[0])
        heading0 = float(self.df["reference_heading"].iloc[0])
        self.nav_core.reset(origin_lat=lat0, origin_lon=lon0, origin_heading_deg=heading0)
        self.outage_controller.reset()
        self.cached_dr_path = []
        self.gyro_bias_samples = []
        self.online_gyro_bias = 0.0
        self.yaw_scale_numerator = 0.0
        self.yaw_scale_denominator = 1e-9
        self.online_yaw_scale = 1.0
        self.yaw_rate_ema = 0.0
        self.pre_outage_speed_history = []
        self.pre_outage_speed_cap = 30.0
        self.dr_imu_speed = 0.0
        self.dr_imu_speed_ema = 0.0

    def set_playing(self, playing):
        self.is_playing = bool(playing)

    def set_playback_rate(self, rate):
        self.playback_rate = max(0.1, min(10.0, float(rate)))

    def step(self, stride=None):
        """Advance replay by one or more time steps and compute dead reckoning."""
        if self.df is None or self.total_samples == 0:
            return None

        if self.current_index >= self.total_samples - 1:
            self.is_playing = False
            return self.get_current_frame()

        if stride is None:
            actual_stride = max(1, int(round(self.playback_rate)))
        else:
            actual_stride = max(1, int(stride))

        self.current_index = min(self.total_samples - 1, self.current_index + actual_stride)
        return self.process_current_frame()

    def process_current_frame(self):
        """Execute active state update, PyTorch inference, and 2D dead reckoning."""
        row = self.df.iloc[self.current_index]

        # Extract current sensor & ground truth values
        rel_time_s = float(row["relative_time_s"]) if "relative_time_s" in row else float(self.current_index * 0.1)
        ref_east_m = float(row["ref_east_m"])
        ref_north_m = float(row["ref_north_m"])
        ref_speed_mps = float(row["reference_speed"])
        ref_speed_kmh = float(row["reference_speed_kmh"])
        ref_heading_deg = float(row["reference_heading"])
        
        # Raw IMU
        accel_x = float(row["accel_x"])
        accel_y = float(row["accel_y"])
        accel_z = float(row["accel_z"])
        gyro_x = float(row["gyro_x"]) if "gyro_x" in row else 0.0
        gyro_y = float(row["gyro_y"]) if "gyro_y" in row else 0.0
        gyro_z = float(row["gyro_z"])
        
        # Vehicle Vertical Yaw-Rate Extraction from Smartphone Frame
        # In upright dashboard mount, vehicle vertical yaw rotation corresponds to -gyro_y
        yaw_rate_raw = -gyro_y
        
        # Rolling acceleration variance proxy
        accel_var = float((accel_x**2 + accel_y**2 + (accel_z - 9.81)**2))

        # 1. Update Outage Controller state
        last_dr_east = self.nav_core.pos_east_m
        last_dr_north = self.nav_core.pos_north_m
        self.outage_controller.update(rel_time_s, last_dr_east, last_dr_north)
        outage_status = self.outage_controller.get_telemetry_status()

        # 2. Velocity Estimation & Dead Reckoning Propagation
        if not outage_status["outage_active"] and not outage_status["is_blending"]:
            # Calibrate gyro bias (median) and yaw scale (LSQ) while GNSS is available
            if self.current_index > 0:
                prev_hdg = float(self.df["reference_heading"].iloc[self.current_index - 1])
                # Use wrapped heading delta to handle 0/360 crossover
                raw_hdg_delta = (ref_heading_deg - prev_hdg + 180.0) % 360.0 - 180.0
                hdg_delta_abs = abs(raw_hdg_delta)

                # Straight-line: collect bias samples (median is more robust than mean)
                if hdg_delta_abs < 0.2:
                    self.gyro_bias_samples.append(yaw_rate_raw)
                    if len(self.gyro_bias_samples) > 300:
                        self.gyro_bias_samples.pop(0)
                    self.online_gyro_bias = float(np.median(self.gyro_bias_samples))

                # Turning segment: accumulate LSQ terms for yaw scale calibration
                # ref_yaw_rate = heading change in rad/s
                ref_yaw_rate = float(np.radians(raw_hdg_delta) / 0.1)
                if hdg_delta_abs > 0.3:  # only on genuine turns
                    g_debiased = yaw_rate_raw - self.online_gyro_bias
                    self.yaw_scale_numerator += g_debiased * ref_yaw_rate
                    self.yaw_scale_denominator += g_debiased * g_debiased
                    # Update scale only when enough turning data collected
                    if self.yaw_scale_denominator > 0.1:
                        raw_scale = self.yaw_scale_numerator / self.yaw_scale_denominator
                        # Clamp scale to physically plausible range [0.5, 2.0]
                        self.online_yaw_scale = float(np.clip(raw_scale, 0.5, 2.0))

            # Collect pre-outage speed history for physics-based DR velocity cap
            self.pre_outage_speed_history.append(float(ref_speed_mps))
            if len(self.pre_outage_speed_history) > 200:  # keep last 20s @ 10Hz
                self.pre_outage_speed_history.pop(0)
            if len(self.pre_outage_speed_history) >= 5:
                # Cap = max observed pre-outage speed * 2.5 (generous upper bound).
                # Minimum 25 m/s (90 km/h) so a slow-segment outage doesn't under-cap.
                observed_max = float(np.max(self.pre_outage_speed_history))
                self.pre_outage_speed_cap = max(observed_max * 2.5, 25.0)


            # Reset IMU speed integrator to current GNSS speed
            self.dr_imu_speed = float(ref_speed_mps)
            self.dr_imu_speed_ema = float(ref_speed_mps)

            # Normal GNSS locked mode: Use ground-truth anchor
            self.nav_core.set_position_enu(ref_east_m, ref_north_m)
            self.nav_core.set_heading_deg(ref_heading_deg)
            dr_state = self.nav_core.propagate_step(
                speed_mps=ref_speed_mps,
                heading_deg=ref_heading_deg,
                dt=0.1,
                accel_var=accel_var
            )
            active_east = ref_east_m
            active_north = ref_north_m
            nav_mode = "GNSS_LOCKED"
            displayed_speed_kmh = ref_speed_kmh
            displayed_speed_mps = ref_speed_mps
            displayed_speed_source = "REFERENCE_OBD (Ground Truth)"
            ai_speed_mps = ref_speed_mps
            ai_speed_kmh = ref_speed_kmh
        else:
            # Under GNSS OUTAGE or BLENDING: Execute actual PyTorch neural delta-v inference!
            pred_delta_v = self.infer_neural_delta_v(self.current_index, window_len=200)

            dt_step = 0.1
            v_anchor = self.outage_controller.anchor_speed_mps
            outage_elapsed = self.outage_controller.current_outage_elapsed_s

            # 1. Physics-Clamped AI Velocity Estimation
            # PyTorch Exp_5 LSTM model predicts delta_v from pre-outage anchor speed v_anchor
            v_raw_ai = max(0.0, v_anchor + pred_delta_v)

            # Cap velocity to plausible pre-outage vehicle speed upper bound
            v_reconstructed = float(np.clip(v_raw_ai, 0.0, self.pre_outage_speed_cap))

            # EKF Velocity Smoothing with forward acceleration
            a_clamped = float(np.clip(accel_x, -4.0, 4.0))
            v_fused = self.ekf.step(a_forward=a_clamped, v_ai_pred=v_reconstructed, dt=dt_step)
            v_reconstructed = float(np.clip(v_fused, 0.0, self.pre_outage_speed_cap))

            # 2. Pure Physical IMU Multi-Signal ZUPT (Zero velocity leakage)
            is_standstill = self.zupt.update(
                accel_x=accel_x,
                accel_y=accel_y,
                accel_z=accel_z,
                gyro_x=gyro_x,
                gyro_y=gyro_y,
                gyro_z=gyro_z
            )
            if is_standstill:
                v_reconstructed = 0.0
                self.ekf.v_est = 0.0
                self.dr_imu_speed = 0.0
                self.dr_imu_speed_ema = 0.0


            # 3. Advance 2D kinematic position using AI velocity + Gyro yaw rate (bias + scale corrected)
            # Apply: bias removal → scale correction → EMA smoothing → physical clamp
            yaw_rate_debiased = yaw_rate_raw - self.online_gyro_bias
            yaw_rate_scaled = yaw_rate_debiased * self.online_yaw_scale
            # EMA smoothing to suppress jitter without removing genuine turns
            self.yaw_rate_ema = (self.yaw_ema_alpha * yaw_rate_scaled
                                 + (1.0 - self.yaw_ema_alpha) * self.yaw_rate_ema)
            # Hard clamp: road vehicle cannot yaw faster than 90 deg/s
            yaw_rate_corrected = float(np.clip(self.yaw_rate_ema, -np.radians(90), np.radians(90)))
            self.nav_core.update_heading(yaw_rate_corrected, dt=dt_step)
            
            # 4. Non-Holonomic Constraint (NHC) propagation & step update
            dr_state = self.nav_core.propagate_step(
                speed_mps=v_reconstructed,
                heading_deg=None,
                dt=dt_step
            )
            
            # Compute blended position if in restoration phase
            blended_e, blended_n, alpha = self.outage_controller.compute_blended_position(
                gnss_east_m=ref_east_m,
                gnss_north_m=ref_north_m,
                dr_east_m=self.nav_core.pos_east_m,
                dr_north_m=self.nav_core.pos_north_m
            )
            
            active_east = blended_e
            active_north = blended_n
            nav_mode = "AI_DEAD_RECKONING" if outage_status["outage_active"] else "GNSS_RESTORE_BLENDING"
            displayed_speed_mps = v_reconstructed
            displayed_speed_kmh = v_reconstructed * 3.6
            displayed_speed_source = "AI_ESTIMATED (PyTorch Exp_5 LSTM Delta-V Forward Pass)"
            ai_speed_mps = v_reconstructed
            ai_speed_kmh = v_reconstructed * 3.6

        # Append to live DR trail
        if len(self.cached_dr_path) == 0 or self.current_index % 2 == 0:
            self.cached_dr_path.append([round(active_east, 2), round(active_north, 2)])
            if len(self.cached_dr_path) > 3000:
                self.cached_dr_path.pop(0)

        position_error_m = float(np.sqrt((active_east - ref_east_m)**2 + (active_north - ref_north_m)**2))

        return {
            "index": self.current_index,
            "total_samples": self.total_samples,
            "relative_time_s": round(rel_time_s, 2),
            "progress_pct": round((self.current_index / max(1, self.total_samples - 1)) * 100.0, 1),
            "is_playing": self.is_playing,
            "playback_rate": self.playback_rate,
            
            # Live Coordinates
            "active_east_m": round(active_east, 2),
            "active_north_m": round(active_north, 2),
            "ref_east_m": round(ref_east_m, 2),
            "ref_north_m": round(ref_north_m, 2),
            "position_error_m": round(position_error_m, 2),
            
            # Speeds
            "displayed_speed_kmh": round(displayed_speed_kmh, 1),
            "displayed_speed_mps": round(displayed_speed_mps, 2),
            "displayed_speed_source": displayed_speed_source,
            "ai_speed_kmh": round(ai_speed_kmh, 1),
            "ref_speed_kmh": round(ref_speed_kmh, 1),
            
            # Heading & IMU
            "heading_deg": round(float(np.degrees(self.nav_core.heading_rad)) % 360.0, 1),
            "accel_x": round(accel_x, 3),
            "accel_y": round(accel_y, 3),
            "accel_z": round(accel_z, 3),
            "gyro_z": round(gyro_z, 4),
            
            # GNSS & Outage Status
            "gnss_state": outage_status["state"],
            "nav_mode": nav_mode,
            "outage_active": outage_status["outage_active"],
            "outage_elapsed_s": outage_status["outage_elapsed_s"],
            "outage_target_s": outage_status["outage_target_s"],
            "is_blending": outage_status["is_blending"],
            "blend_progress": outage_status["blend_progress"],
            
            # PyTorch Inference Metadata
            "last_inference_output": self.last_inference_output,
            "checkpoint_epoch": self.checkpoint_epoch,

            # Gyro Calibration State (for dashboard display)
            "gyro_bias": round(self.online_gyro_bias, 6),
            "yaw_scale": round(self.online_yaw_scale, 4),
            
            # Live trajectory snippet
            "current_dr_point": [round(active_east, 2), round(active_north, 2)],
        }

    def get_current_frame(self):
        return self.process_current_frame()

    def trigger_simulated_outage(self, duration_s=None):
        """Trigger blackout at current playback location."""
        frame = self.get_current_frame()
        return self.outage_controller.trigger_outage(
            current_time_s=frame["relative_time_s"],
            duration_s=duration_s,
            current_east_m=frame["ref_east_m"],
            current_north_m=frame["ref_north_m"],
            current_speed_mps=frame["displayed_speed_mps"],
            current_heading_deg=frame["heading_deg"],
        )

    def restore_gnss(self):
        """Restore GNSS signal immediately."""
        frame = self.get_current_frame()
        return self.outage_controller.restore_gnss(
            current_time_s=frame["relative_time_s"],
            last_dr_east_m=self.nav_core.pos_east_m,
            last_dr_north_m=self.nav_core.pos_north_m,
        )
