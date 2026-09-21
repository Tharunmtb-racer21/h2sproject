"""
SIH26168 Intelligent Dead Reckoning System
Module: Outage Controller & Seamless Handover Engine

Handles:
- GNSS state machine: AVAILABLE -> OUTAGE / DEAD RECKONING -> RESTORED / BLENDING
- Outage timing (10s, 30s, 60s, or continuous manual)
- Pre-outage anchor preservation (E0, N0, v0)
- Sigmoid-weighted smooth position blending upon GNSS return to prevent visual jumps
"""

import numpy as np


class GNSSState:
    AVAILABLE = "AVAILABLE"
    OUTAGE = "OUTAGE"
    RESTORED = "RESTORED"


class OutageController:
    def __init__(self, blend_duration_s=2.0):
        self.blend_duration_s = float(blend_duration_s)
        self.reset()

    def reset(self):
        self.state = GNSSState.AVAILABLE
        self.outage_active = False
        self.outage_start_time = None
        self.outage_target_duration_s = None
        self.current_outage_elapsed_s = 0.0
        
        # Anchor states at outage trigger
        self.anchor_east_m = 0.0
        self.anchor_north_m = 0.0
        self.anchor_speed_mps = 0.0
        self.anchor_heading_deg = 0.0
        
        # Blending states
        self.restored_start_time = None
        self.blend_elapsed_s = 0.0
        self.is_blending = False
        self.pre_restore_dr_east = 0.0
        self.pre_restore_dr_north = 0.0

    def trigger_outage(self, current_time_s, duration_s=None, current_east_m=0.0, current_north_m=0.0, current_speed_mps=0.0, current_heading_deg=0.0):
        """Trigger a simulated GNSS outage blackout."""
        self.state = GNSSState.OUTAGE
        self.outage_active = True
        self.outage_start_time = float(current_time_s)
        self.outage_target_duration_s = float(duration_s) if duration_s is not None else None
        self.current_outage_elapsed_s = 0.0
        
        # Save exact anchor point
        self.anchor_east_m = float(current_east_m)
        self.anchor_north_m = float(current_north_m)
        self.anchor_speed_mps = float(current_speed_mps)
        self.anchor_heading_deg = float(current_heading_deg)
        
        self.is_blending = False
        return {
            "status": "OUTAGE_TRIGGERED",
            "duration_s": self.outage_target_duration_s,
            "anchor_east": self.anchor_east_m,
            "anchor_north": self.anchor_north_m,
            "anchor_speed": self.anchor_speed_mps,
        }

    def restore_gnss(self, current_time_s, last_dr_east_m=0.0, last_dr_north_m=0.0):
        """Restore GNSS signal and initiate smooth Sigmoid handover blending."""
        if not self.outage_active:
            return {"status": "ALREADY_AVAILABLE"}

        self.state = GNSSState.RESTORED
        self.outage_active = False
        self.restored_start_time = float(current_time_s)
        self.blend_elapsed_s = 0.0
        self.is_blending = True
        
        self.pre_restore_dr_east = float(last_dr_east_m)
        self.pre_restore_dr_north = float(last_dr_north_m)
        
        return {
            "status": "GNSS_RESTORED",
            "blending": True,
            "blend_duration_s": self.blend_duration_s,
        }

    def update(self, current_time_s, last_dr_east_m=0.0, last_dr_north_m=0.0):
        """Update outage timer and automatic restoration check."""
        if self.outage_active and self.outage_start_time is not None:
            self.current_outage_elapsed_s = max(0.0, current_time_s - self.outage_start_time)
            
            # Check automatic duration expiry
            if self.outage_target_duration_s is not None and self.current_outage_elapsed_s >= self.outage_target_duration_s:
                self.restore_gnss(current_time_s, last_dr_east_m, last_dr_north_m)

        elif self.is_blending and self.restored_start_time is not None:
            self.blend_elapsed_s = max(0.0, current_time_s - self.restored_start_time)
            if self.blend_elapsed_s >= self.blend_duration_s:
                self.is_blending = False
                self.state = GNSSState.AVAILABLE

    def compute_blended_position(self, gnss_east_m, gnss_north_m, dr_east_m, dr_north_m):
        """
        Compute continuous smooth blended position during GNSS re-acquisition.
        Uses Sigmoid smooth-step weighting w(t) in [0, 1] across blend_duration_s.
        """
        if self.outage_active:
            # During outage, strictly use dead reckoning
            return dr_east_m, dr_north_m, 0.0

        if not self.is_blending:
            # Normal GNSS available
            return gnss_east_m, gnss_north_m, 1.0

        # Smooth-step S-curve blending: 3x^2 - 2x^3 where x = t / T
        t_norm = np.clip(self.blend_elapsed_s / max(0.01, self.blend_duration_s), 0.0, 1.0)
        alpha = t_norm * t_norm * (3.0 - 2.0 * t_norm)  # 0.0 at start, 1.0 at finish

        blended_east = (1.0 - alpha) * dr_east_m + alpha * gnss_east_m
        blended_north = (1.0 - alpha) * dr_north_m + alpha * gnss_north_m

        return blended_east, blended_north, alpha

    def get_telemetry_status(self):
        """Get formatted status block for UI."""
        return {
            "state": self.state,
            "outage_active": self.outage_active,
            "outage_elapsed_s": round(self.current_outage_elapsed_s, 1),
            "outage_target_s": self.outage_target_duration_s,
            "is_blending": self.is_blending,
            "blend_progress": round(min(1.0, self.blend_elapsed_s / max(0.01, self.blend_duration_s)), 2) if self.is_blending else 1.0,
        }
