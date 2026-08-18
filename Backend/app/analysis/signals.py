from __future__ import annotations
import numpy as np
from scipy.signal import butter, filtfilt

def butter_lowpass_filtfilt(x: np.ndarray, fs: float, cutoff_hz: float, order: int = 4) -> np.ndarray:
    if cutoff_hz <= 0:
        return x
    nyq = 0.5 * fs
    wn = min(cutoff_hz / nyq, 0.999)
    b, a = butter(order, wn, btype="low", analog=False)
    # filtfilt expects finite values; handle NaNs before calling outside.
    return filtfilt(b, a, x, axis=0)

def central_diff(x: np.ndarray, dt: float) -> np.ndarray:
    """Central difference derivative with forward/backward edges."""
    v = np.zeros_like(x, dtype=float)
    if len(x) < 3:
        return v
    v[1:-1] = (x[2:] - x[:-2]) / (2.0 * dt)
    v[0] = (x[1] - x[0]) / dt
    v[-1] = (x[-1] - x[-2]) / dt
    return v

def magnitude(vec: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum(vec**2, axis=-1))
