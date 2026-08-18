from __future__ import annotations
import numpy as np
from scipy.signal import lfilter

# Parameters for ISO 2631-1 Wk from Table 3 in Rimell & Mansfield (2007):
# Wk: f1=0.4,Q1=1/sqrt(2), f2=100,Q2=1/sqrt(2), f3=12.5,f4=12.5,Q4=0.63, f5=2.37,Q5=0.91, f6=3.3,Q6=0.91 :contentReference[oaicite:3]{index=3}
WK_PARAMS = {
    "f1": 0.4,  "Q1": 1/np.sqrt(2),
    "f2": 100., "Q2": 1/np.sqrt(2),
    "f3": 12.5, "f4": 12.5, "Q4": 0.63,
    "f5": 2.37, "Q5": 0.91,
    "f6": 3.3,  "Q6": 0.91,
}

def _warp_omega(f_hz: float, fs: float) -> float:
    # Rimell uses pre-warping for bilinear transform.
    # omega' = 2*fs * tan(pi*f/fs)
    return 2.0 * fs * np.tan(np.pi * f_hz / fs)

def _section_Hh(fs: float, f1: float, Q1: float):
    w1 = _warp_omega(f1, fs)
    # Transfer function coefficients from Table 8 (Hh). :contentReference[oaicite:4]{index=4}
    a0 = 4*Q1 + 2*w1 + (w1**2)
    a1 = 2*(w1**2) - 8*Q1
    a2 = 4*Q1 - 2*w1 + (w1**2)
    b0 = 4*Q1
    b1 = -8*Q1
    b2 = 4*Q1
    b = np.array([b0, b1, b2], dtype=float) / a0
    a = np.array([1.0, a1/a0, a2/a0], dtype=float)
    return b, a

def _section_Hl(fs: float, f2: float, Q2: float):
    w2 = _warp_omega(f2, fs)
    a0 = 4*Q2 + 2*w2 + (w2**2)
    a1 = 2*(w2**2) - 8*Q2
    a2 = 4*Q2 - 2*w2 + (w2**2)
    b0 = (w2**2)*Q2
    b1 = 2*(w2**2)*Q2
    b2 = (w2**2)*Q2
    b = np.array([b0, b1, b2], dtype=float) / a0
    a = np.array([1.0, a1/a0, a2/a0], dtype=float)
    return b, a

def _section_Ht(fs: float, f3: float, f4: float, Q4: float):
    w3 = _warp_omega(f3, fs)
    w4 = _warp_omega(f4, fs)
    a0 = 4*Q4 + 2*w4 + (w4**2)
    a1 = 2*(w4**2) - 8*Q4
    a2 = 4*Q4 - 2*w4 + (w4**2)
    b0 = (w4**2)*Q4
    b1 = 2*(w4**2)*Q4
    b2 = (w4**2)*Q4
    # multiply by w3' per Table 8 Ht form (b terms carry w3'). :contentReference[oaicite:5]{index=5}
    b = np.array([b0, b1, b2], dtype=float) * (w3 / a0)
    a = np.array([1.0, a1/a0, a2/a0], dtype=float)
    return b, a

def _section_Hs(fs: float, f5: float, Q5: float, f6: float, Q6: float):
    w5 = _warp_omega(f5, fs)
    w6 = _warp_omega(f6, fs)
    # Using Table 8 (Hs) layout :contentReference[oaicite:6]{index=6}
    a0 = 4*Q6 + 2*w6 + (w6**2)
    a1 = 2*(w6**2) - 8*Q6
    a2 = 4*Q6 - 2*w6 + (w6**2)

    b0 = 4*Q5 + 2*w5 + (w5**2)
    b1 = 2*(w5**2) - 8*Q5
    b2 = 4*Q5 - 2*w5 + (w5**2)

    b = np.array([b0, b1, b2], dtype=float) / a0
    a = np.array([1.0, a1/a0, a2/a0], dtype=float)
    return b, a

def apply_wk(acc: np.ndarray, fs: float) -> np.ndarray:
    """
    Apply ISO 2631-1 Wk frequency weighting to a 1D acceleration signal.
    This is suitable if you have real acceleration in m/s^2 (e.g., from accelerometer).
    For video-derived "pseudo-metric" acceleration, treat it as an approximate comfort proxy.
    """
    p = WK_PARAMS
    b_hh, a_hh = _section_Hh(fs, p["f1"], p["Q1"])
    b_hl, a_hl = _section_Hl(fs, p["f2"], p["Q2"])
    b_ht, a_ht = _section_Ht(fs, p["f3"], p["f4"], p["Q4"])
    b_hs, a_hs = _section_Hs(fs, p["f5"], p["Q5"], p["f6"], p["Q6"])

    y = lfilter(b_hh, a_hh, acc)
    y = lfilter(b_hl, a_hl, y)
    y = lfilter(b_ht, a_ht, y)
    y = lfilter(b_hs, a_hs, y)
    return y
