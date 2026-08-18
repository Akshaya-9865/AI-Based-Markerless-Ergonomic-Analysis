from __future__ import annotations
import numpy as np

def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x))))

def comfort_index(mean_jerk: float) -> float:
    # user-specified: 1/(1+mean_jerk)
    return float(1.0 / (1.0 + max(mean_jerk, 0.0)))

def summarize_joint(acc_res: np.ndarray, jerk_res: np.ndarray) -> dict:
    return {
        "mean_acc": float(np.mean(acc_res)),
        "peak_acc": float(np.max(acc_res)),
        "rms_acc": float(np.sqrt(np.mean(acc_res**2))),
        "max_jerk": float(np.max(jerk_res)),
        "mean_jerk": float(np.mean(jerk_res)),
        "comfort_index": comfort_index(float(np.mean(jerk_res))),
    }
