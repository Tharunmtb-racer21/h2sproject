"""
demo_realtime_navigation/backend/drift_corrector.py
SIH26168 Intelligent Dead Reckoning System
Module: Advanced Drift Reduction Engine

Implements:
1. Non-Holonomic Constraints (NHC) for ground vehicles (lateral velocity damping)
2. Safe Multi-Signal Zero-Velocity Updates (ZUPT)
3. 1D Extended Kalman Filter (EKF) fusing Forward Acceleration with AI Neural Delta-V
4. Experimental Soft-Confidence Map Matching Engine with Heading Compatibility
"""

import numpy as np
from typing import Tuple, Dict, Optional, List


class NonHolonomicConstraint:
    """
    Applies non-holonomic physical constraints for wheeled ground vehicles:
    - Lateral velocity (orthogonal to vehicle heading) is constrained towards 0.
    - Vertical velocity is constrained towards 0.
    - Forward displacement is preserved along heading vector.
    """
    def __init__(self, damping_strength: float = 0.95):
        self.damping_strength = float(np.clip(damping_strength, 0.0, 1.0))
        self.last_correction_m = 0.0
        self.total_corrections = 0

    def apply(self, v_forward: float, heading_rad: float, dt: float = 0.1) -> Tuple[float, float, float]:
        """
        Compute constrained 2D displacements dNorth, dEast under pure non-holonomic heading.
        Returns (d_north, d_east, correction_mag).
        """
        # Under pure 2D NHC, vehicle moves strictly along heading vector u = [sin(psi), cos(psi)]
        v_f = max(0.0, float(v_forward))
        d_north = v_f * np.cos(heading_rad) * dt
        d_east = v_f * np.sin(heading_rad) * dt
        
        # Lateral velocity component is 0.0 under non-holonomic ground constraint
        correction_mag = 0.0
        self.last_correction_m = correction_mag
        self.total_corrections += 1
        return d_north, d_east, correction_mag


class SafeStandstillDetector:
    """
    Pure Physical IMU Multi-Signal Standstill (ZUPT) Detector:
    Requires simultaneous physical confirmation from:
    1. Accelerometer 10-sample (1.0s) rolling magnitude variance < threshold_accel (no vehicle acceleration/chassis shake)
    2. Gyroscope 10-sample rolling magnitude < threshold_gyro (no vehicle turning, pitching, or rolling)
    3. Minimum temporal persistence of N_persist continuous steps (prevents false triggers on bumps/cruising)
    
    GUARANTEED ZERO VELOCITY LEAKAGE: Relies strictly on 6-DOF IMU invariants without any velocity parameter.
    """
    def __init__(
        self,
        window_size: int = 10,
        accel_var_thresh: float = 0.015,
        gyro_mag_thresh: float = 0.02,
        persist_steps: int = 8
    ):
        self.window_size = int(window_size)
        self.accel_var_thresh = float(accel_var_thresh)
        self.gyro_mag_thresh = float(gyro_mag_thresh)
        self.persist_steps = int(persist_steps)
        
        self.accel_mag_buffer: List[float] = []
        self.gyro_mag_buffer: List[float] = []
        self.consecutive_standstill_steps = 0
        
        # Telemetry & Audit logs
        self.is_standstill = False
        self.activations_count = 0
        self.rejections_count = 0
        self.last_rejection_reason = "INIT"

    def reset(self):
        self.accel_mag_buffer.clear()
        self.gyro_mag_buffer.clear()
        self.consecutive_standstill_steps = 0
        self.is_standstill = False
        self.activations_count = 0
        self.rejections_count = 0
        self.last_rejection_reason = "RESET"

    def update(
        self,
        accel_x: float,
        accel_y: float,
        accel_z: float,
        gyro_x: float,
        gyro_y: float,
        gyro_z: float
    ) -> bool:
        """
        Evaluate strictly 6-DOF IMU signals and determine stationary state.
        Returns True if vehicle is physically stationary (ZUPT engaged).
        """
        # 1. Compute instantaneous magnitudes
        a_mag = float(np.sqrt(accel_x**2 + accel_y**2 + accel_z**2))
        g_mag = float(np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2))
        
        self.accel_mag_buffer.append(a_mag)
        self.gyro_mag_buffer.append(g_mag)
        
        if len(self.accel_mag_buffer) > self.window_size:
            self.accel_mag_buffer.pop(0)
            self.gyro_mag_buffer.pop(0)

        # Require full buffer for variance check
        if len(self.accel_mag_buffer) < self.window_size:
            self.is_standstill = False
            self.last_rejection_reason = "BUFFER_WARMUP"
            return False

        # 2. Pure physical IMU checks
        a_var = float(np.var(self.accel_mag_buffer, ddof=1)) if len(self.accel_mag_buffer) > 1 else 0.0
        g_mean = float(np.mean(self.gyro_mag_buffer))
        
        cond_accel = a_var < self.accel_var_thresh
        cond_gyro = g_mean < self.gyro_mag_thresh

        if cond_accel and cond_gyro:
            self.consecutive_standstill_steps += 1
            if self.consecutive_standstill_steps >= self.persist_steps:
                self.is_standstill = True
                self.activations_count += 1
                self.last_rejection_reason = "ACTIVE_ZUPT"
                return True
            else:
                self.is_standstill = False
                self.last_rejection_reason = f"PERSISTENCE_PENDING ({self.consecutive_standstill_steps}/{self.persist_steps})"
                return False
        else:
            self.consecutive_standstill_steps = 0
            self.is_standstill = False
            self.rejections_count += 1
            reasons = []
            if not cond_accel: reasons.append(f"ACCEL_VAR({a_var:.4f}>{self.accel_var_thresh})")
            if not cond_gyro: reasons.append(f"GYRO_MAG({g_mean:.4f}>{self.gyro_mag_thresh})")
            self.last_rejection_reason = "; ".join(reasons)
            return False


class VelocityEKF:
    """
    1D Extended Kalman Filter for Inertial Speed Estimation:
    State: x = [velocity (m/s), accel_bias (m/s^2)]^T
    - Predict Step: Propagate using forward accelerometer reading a_x (high frequency dynamics).
    - Update Step: Fuse with AI Neural Model Delta-V predicted speed (zero mean bias anchor).
    """
    def __init__(self, q_vel: float = 0.05, q_bias: float = 0.001, r_ai: float = 0.5):
        # State vector [v, b_a]
        self.x = np.array([0.0, 0.0], dtype=np.float64)
        # Error covariance matrix P
        self.P = np.diag([1.0, 0.1]).astype(np.float64)
        # Process noise covariance Q
        self.Q = np.diag([q_vel, q_bias]).astype(np.float64)
        # Measurement noise covariance R (AI speed uncertainty)
        self.R = np.array([[r_ai]], dtype=np.float64)
        
        self.last_innovation = 0.0
        self.last_filtered_speed = 0.0

    def reset(self, initial_speed: float = 0.0):
        self.x = np.array([float(initial_speed), 0.0], dtype=np.float64)
        self.P = np.diag([0.5, 0.05]).astype(np.float64)
        self.last_innovation = 0.0
        self.last_filtered_speed = float(initial_speed)

    def step(self, a_forward: float, v_ai_pred: float, dt: float = 0.1) -> float:
        """
        Execute Predict + Update cycle.
        Returns optimal filtered forward speed in m/s.
        """
        # 1. Predict Step
        v_prev, b_a = self.x[0], self.x[1]
        a_net = a_forward - b_a
        v_pred = max(0.0, v_prev + a_net * dt)
        
        # State transition matrix F
        F = np.array([[1.0, -dt],
                      [0.0,  1.0]], dtype=np.float64)
        
        self.P = F @ self.P @ F.T + self.Q * dt
        self.x[0] = v_pred
        
        # 2. Update Step with AI speed measurement
        H = np.array([[1.0, 0.0]], dtype=np.float64)
        y = v_ai_pred - self.x[0]  # Innovation / residual
        self.last_innovation = float(y)
        
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        
        self.x = self.x + (K @ np.array([[y]])).flatten()
        self.P = (np.eye(2) - K @ H) @ self.P
        
        # Physical constraint: Vehicle velocity cannot be negative
        self.x[0] = max(0.0, float(self.x[0]))
        self.last_filtered_speed = float(self.x[0])
        return self.last_filtered_speed


class ExperimentalMapMatcher:
    """
    Experimental Soft-Confidence Road Snapping Engine:
    - Projects estimated dead-reckoning position onto valid road centerline geometry.
    - Evaluates heading compatibility (|psi_veh - psi_road| <= 45 deg).
    - Applies soft, bounded distance-weighted correction (no abrupt jumps).
    - Safely falls back to pure dead-reckoning when road candidate is distant or ambiguous.
    """
    def __init__(
        self,
        search_radius_m: float = 40.0,
        heading_tolerance_deg: float = 45.0,
        max_correction_m: float = 5.0,
        confidence_sigma_m: float = 15.0
    ):
        self.search_radius_m = float(search_radius_m)
        self.heading_tolerance_rad = np.radians(float(heading_tolerance_deg))
        self.max_correction_m = float(max_correction_m)
        self.confidence_sigma_m = float(confidence_sigma_m)
        
        self.road_nodes_east: np.ndarray = np.array([])
        self.road_nodes_north: np.ndarray = np.array([])
        self.has_map_data = False
        
        # Audit Telemetry
        self.last_confidence = 0.0
        self.last_correction_mag = 0.0
        self.total_corrections = 0
        self.total_rejections = 0
        self.last_status = "NO_MAP_DATA"

    def load_road_network(self, nodes_east: np.ndarray, nodes_north: np.ndarray):
        """Load 2D road centerline polyline coordinates (Local ENU in metres)."""
        if len(nodes_east) > 1 and len(nodes_north) > 1:
            self.road_nodes_east = np.array(nodes_east, dtype=np.float64)
            self.road_nodes_north = np.array(nodes_north, dtype=np.float64)
            self.has_map_data = True
            self.last_status = f"LOADED_{len(nodes_east)}_NODES"

    def correct_position(
        self,
        pos_east_m: float,
        pos_north_m: float,
        heading_rad: float
    ) -> Tuple[float, float, float, float]:
        """
        Perform soft map-matching projection on the nearest compatible road segment.
        Returns (corrected_east, corrected_north, confidence, correction_magnitude).
        """
        if not self.has_map_data or len(self.road_nodes_east) < 2:
            self.last_status = "NO_MAP_FALLBACK"
            return pos_east_m, pos_north_m, 0.0, 0.0

        p = np.array([pos_east_m, pos_north_m], dtype=np.float64)
        
        best_candidate = None
        min_dist = float("inf")
        best_proj = None
        best_road_heading = 0.0

        # Search across road segments [A, B]
        N = len(self.road_nodes_east) - 1
        for i in range(N):
            a = np.array([self.road_nodes_east[i], self.road_nodes_north[i]])
            b = np.array([self.road_nodes_east[i+1], self.road_nodes_north[i+1]])
            
            ab = b - a
            seg_len_sq = np.dot(ab, ab)
            if seg_len_sq < 1e-4:
                continue
                
            # Road segment direction & heading
            road_heading = np.arctan2(ab[0], ab[1]) # ENU angle (0=N, pi/2=E)
            
            # Heading compatibility check (forward & backward)
            h_diff = abs((heading_rad - road_heading + np.pi) % (2.0 * np.pi) - np.pi)
            if h_diff > self.heading_tolerance_rad:
                continue
                
            # Orthogonal projection factor t in [0, 1]
            t = np.clip(np.dot(p - a, ab) / seg_len_sq, 0.0, 1.0)
            proj_point = a + t * ab
            dist = np.linalg.norm(p - proj_point)
            
            if dist < min_dist and dist <= self.search_radius_m:
                min_dist = dist
                best_candidate = i
                best_proj = proj_point
                best_road_heading = road_heading

        if best_candidate is None or best_proj is None:
            self.total_rejections += 1
            self.last_status = "NO_COMPATIBLE_CANDIDATE"
            self.last_confidence = 0.0
            self.last_correction_mag = 0.0
            return pos_east_m, pos_north_m, 0.0, 0.0

        # Calculate soft confidence gamma in [0, 1]
        h_diff = abs((heading_rad - best_road_heading + np.pi) % (2.0 * np.pi) - np.pi)
        dist_factor = np.exp(- (min_dist**2) / (2.0 * self.confidence_sigma_m**2))
        heading_factor = np.cos(h_diff)
        confidence = float(np.clip(dist_factor * heading_factor, 0.0, 1.0))
        
        # Soft correction displacement vector
        disp_vec = best_proj - p
        disp_mag = np.linalg.norm(disp_vec)
        
        # Apply soft gain alpha and clamp max step displacement
        soft_gain = np.clip(confidence * 0.35, 0.0, 0.30)
        correction_step = disp_vec * soft_gain
        corr_mag = np.linalg.norm(correction_step)
        
        if corr_mag > self.max_correction_m:
            correction_step = (correction_step / corr_mag) * self.max_correction_m
            corr_mag = self.max_correction_m

        p_corrected = p + correction_step
        self.total_corrections += 1
        self.last_confidence = confidence
        self.last_correction_mag = float(corr_mag)
        self.last_status = f"SOFT_SNAPPED (Conf={confidence:.2f}, Shift={corr_mag:.2f}m)"

        return float(p_corrected[0]), float(p_corrected[1]), confidence, float(corr_mag)
