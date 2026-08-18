from __future__ import annotations
import numpy as np

def _safe_unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-9:
        return np.zeros_like(v)
    return v / n

def angle_between(u: np.ndarray, v: np.ndarray) -> float:
    """Returns unsigned angle in degrees between vectors u and v."""
    u1 = _safe_unit(u)
    v1 = _safe_unit(v)
    c = float(np.clip(np.dot(u1, v1), -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))

def joint_flexion_deg(proximal: np.ndarray, joint: np.ndarray, distal: np.ndarray) -> float:
    """
    Flexion-like definition: 180 - angle between segments (proximal->joint) and (distal->joint).
    For knee/elbow-like joints: straight ~ 0 flexion, bent increases.
    """
    v1 = proximal - joint
    v2 = distal - joint
    ang = angle_between(v1, v2)
    return float(max(0.0, 180.0 - ang))

def trunk_tilt_deg(pelvis: np.ndarray, shoulder: np.ndarray) -> float:
    """
    Anterior trunk tilt w.r.t vertical axis.
    0 = upright, positive = forward lean (in image plane).
    """
    trunk = shoulder - pelvis
    vertical = np.array([0.0, -1.0, 0.0])  # up in image coords (y decreases upward)
    # project to x-y
    trunk2 = np.array([trunk[0], trunk[1], 0.0])
    ang = angle_between(trunk2, vertical)
    return float(ang)

def head_flexion_deg(shoulder: np.ndarray, head: np.ndarray, pelvis: np.ndarray) -> float:
    """
    Head flexion as angle between head segment (shoulder->head) and trunk (pelvis->shoulder).
    0 = aligned, increases with flexion.
    """
    head_seg = head - shoulder
    trunk_seg = shoulder - pelvis
    head2 = np.array([head_seg[0], head_seg[1], 0.0])
    trunk2 = np.array([trunk_seg[0], trunk_seg[1], 0.0])
    return float(angle_between(head2, trunk2))

def ankle_dorsi_proxy_deg(knee: np.ndarray, ankle: np.ndarray, heel: np.ndarray, foot_index: np.ndarray) -> float:
    """
    Ankle dorsiflexion proxy using shank vs foot.
    Uses knee-ankle and heel-foot_index.
    """
    shank = knee - ankle
    foot = foot_index - heel
    shank2 = np.array([shank[0], shank[1], 0.0])
    foot2 = np.array([foot[0], foot[1], 0.0])
    ang = angle_between(shank2, foot2)
    # Neutral foot roughly ~90; we report dorsiflexion-like as deviation from 90
    return float(ang - 90.0)
