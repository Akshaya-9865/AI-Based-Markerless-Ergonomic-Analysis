from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


RED = "#FF0000"

def plot_timeseries(t: np.ndarray, y: np.ndarray, title: str, ylabel: str, out_png: str, threshold: float | None = None):
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    plt.figure(figsize=(10, 4.2), dpi=200)
    plt.plot(t, y, color=RED, linewidth=2.0)
    if threshold is not None:
        plt.axhline(threshold, linestyle="--", linewidth=1.5, color="black")
    plt.title(title, fontweight="bold")
    plt.xlabel("Time (s)")
    plt.ylabel(ylabel)
    plt.grid(True, color="0.85", linewidth=0.8)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
