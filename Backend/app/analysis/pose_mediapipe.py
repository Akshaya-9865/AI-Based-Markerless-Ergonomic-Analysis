from __future__ import annotations
import numpy as np
import cv2
import mediapipe as mp
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

# Landmark IDs (MediaPipe Pose)
L_SHOULDER = 11
L_ELBOW    = 13
L_WRIST    = 15
L_INDEX    = 19   # LEFT_INDEX (for wrist flexion proxy)
L_HIP      = 23
R_HIP      = 24  # used only to compute pelvis midpoint
L_KNEE     = 25
L_ANKLE    = 27
L_HEEL     = 29
L_FOOTIDX  = 31
HEAD_0     = 0

@dataclass
class PoseFrame:
    pts: Dict[str, np.ndarray]      # name -> (x,y,z) in pixels (z scaled)
    vis: Dict[str, float]           # name -> visibility
    ok: bool

def _lm_to_xyz_px(lm, w: int, h: int) -> np.ndarray:
    # x,y are normalized. z is roughly normalized to image width in MP docs.
    return np.array([lm.x * w, lm.y * h, lm.z * w], dtype=float)

def extract_landmarks(video_frame_bgr, pose, min_vis: float) -> PoseFrame:
    h, w = video_frame_bgr.shape[:2]
    rgb = cv2.cvtColor(video_frame_bgr, cv2.COLOR_BGR2RGB)
    res = pose.process(rgb)
    if not res.pose_landmarks:
        return PoseFrame(pts={}, vis={}, ok=False)

    lms = res.pose_landmarks.landmark

    mapping = {
        "shoulder": L_SHOULDER,
        "elbow": L_ELBOW,
        "wrist": L_WRIST,
        "index": L_INDEX,
        "hip": L_HIP,
        "knee": L_KNEE,
        "ankle": L_ANKLE,
        "heel": L_HEEL,
        "foot_index": L_FOOTIDX,
        "head": HEAD_0,
        "r_hip": R_HIP,
    }

    pts, vis = {}, {}
    ok = True
    for name, idx in mapping.items():
        lm = lms[idx]
        pts[name] = _lm_to_xyz_px(lm, w, h)
        vis[name] = float(lm.visibility)
        if name in ("shoulder","elbow","wrist","hip","knee","ankle","head") and vis[name] < min_vis:
            ok = False

    return PoseFrame(pts=pts, vis=vis, ok=ok)

def build_pose_model():
    mp_pose = mp.solutions.pose
    return mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )
