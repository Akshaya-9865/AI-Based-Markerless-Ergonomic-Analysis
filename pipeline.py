from __future__ import annotations
import os
import json
import cv2
import numpy as np
import pandas as pd
from datetime import date
import subprocess

from .pose_mediapipe import build_pose_model, extract_landmarks
from .kinematics import (
    joint_flexion_deg,
    trunk_tilt_deg,
    head_flexion_deg,
    ankle_dorsi_proxy_deg,
)
from .signals import butter_lowpass_filtfilt, central_diff, magnitude
from .comfort import summarize_joint
from .plotting import plot_timeseries

# ✅ CHANGED: use minimal Qualisys-layout PDF generator WITH wrist support
from .report_pdf_qualisys_minimal_wrist_v2 import build_qualisys_pdf_minimal

from .iso2631 import apply_wk

JOINT_ORDER = ["hip", "knee", "ankle", "shoulder", "elbow", "wrist", "head"]


def _nan_interp_limit(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    return df.interpolate(limit=limit, limit_direction="both")


def _bmi(height_cm: float, weight_kg: float) -> float:
    hm = height_cm / 100.0
    return float(weight_kg / (hm * hm + 1e-9))


def _estimate_scale_m_per_px(subject: dict, pts_df: pd.DataFrame) -> float:
    """
    Best-effort scale (meters per pixel).
    If seat reference is provided, use it.
    Otherwise estimate using seated body segment proxy (less accurate).
    """
    if subject.get("seat_reference_length_cm") and subject.get("seat_reference_pixel_length"):
        return (subject["seat_reference_length_cm"] / 100.0) / float(subject["seat_reference_pixel_length"])

    # fallback proxy: use median shoulder-hip pixel distance and assume ~0.30 m torso segment
    sh = pts_df[["shoulder_x", "shoulder_y"]].to_numpy()
    hp = pts_df[["hip_x", "hip_y"]].to_numpy()
    d = np.linalg.norm(sh - hp, axis=1)
    d_med = float(np.nanmedian(d))
    if d_med <= 1.0:
        return 0.001
    assumed_torso_m = 0.30
    return assumed_torso_m / d_med


def run_analysis(
    video_path: str,
    out_dir: str,
    subject: dict,
    min_vis: float,
    max_missing: int,
    fs_hint: float | None = None,
    progress_cb=None,
    cancel_cb=None,
    acc_noise_flag_mps2: float = 50.0,
    jerk_discomfort_mps3: float = 5.0,
):
    os.makedirs(out_dir, exist_ok=True)
    graphs_dir = os.path.join(out_dir, "graphs")
    os.makedirs(graphs_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open uploaded video.")
    fps = cap.get(cv2.CAP_PROP_FPS) or fs_hint or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    qc = {
        "fps": float(fps),
        "width": int(width),
        "height": int(height),
        "nframes": int(nframes),
        "min_720p_recommended": bool(height >= 720),
        "min_30fps_recommended": bool(fps >= 30.0),
    }

    pose = build_pose_model()

    annotated_path = os.path.join(out_dir, "annotated.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(annotated_path, fourcc, float(fps), (width, height))

    rows = []
    ok_count = 0

    def prog(p, msg):
        if progress_cb:
            progress_cb(p, msg)

    for i in range(nframes):
        if cancel_cb and cancel_cb():
            break

        ok, frame = cap.read()
        if not ok:
            break

        pf = extract_landmarks(frame, pose, min_vis=min_vis)
        if pf.ok:
            ok_count += 1

        # pelvis midpoint (needs left hip + right hip from pose)
        if "hip" in pf.pts and "r_hip" in pf.pts:
            pelvis = 0.5 * (pf.pts["hip"] + pf.pts["r_hip"])
        else:
            pelvis = np.array([np.nan, np.nan, np.nan], dtype=float)

        def g(name):
            return pf.pts.get(name, np.array([np.nan, np.nan, np.nan], dtype=float))

        row = {
            "frame": i,
            "time_s": i / float(fps),
            "ok_frame": int(pf.ok),
            "pelvis_x": pelvis[0],
            "pelvis_y": pelvis[1],
            "pelvis_z": pelvis[2],
        }

        # ✅ CHANGED: added "index" (needed for wrist angle)
        for name in ["hip", "knee", "ankle", "shoulder", "elbow", "wrist", "head", "heel", "foot_index", "index"]:
            v = g(name)
            row[f"{name}_x"], row[f"{name}_y"], row[f"{name}_z"] = v[0], v[1], v[2]
            row[f"{name}_vis"] = pf.vis.get(name, 0.0)

        rows.append(row)

        # Draw live annotation
        def draw_marker(pt, label):
            x, y = int(pt[0]), int(pt[1])
            cv2.circle(frame, (x, y), 6, (0, 0, 255), -1)
            cv2.putText(frame, label, (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        def line(a, b):
            pa, pb = g(a), g(b)
            if np.isfinite(pa[0]) and np.isfinite(pb[0]):
                cv2.line(frame, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])), (0, 0, 255), 2)

        for nm, lab in [
            ("hip", "HIP"),
            ("knee", "KNEE"),
            ("ankle", "ANKLE"),
            ("shoulder", "SHOULDER"),
            ("elbow", "ELBOW"),
            ("wrist", "WRIST"),
            ("head", "HEAD"),
        ]:
            pt = g(nm)
            if np.isfinite(pt[0]):
                draw_marker(pt, lab)

        line("shoulder", "elbow")
        line("elbow", "wrist")
        line("shoulder", "hip")
        line("hip", "knee")
        line("knee", "ankle")

        q_pct = (ok_count / max(1, i + 1)) * 100.0
        quality_txt = f"Quality: {q_pct:5.1f}% (vis>{min_vis:.2f})"

        cv2.putText(frame, f"Frame: {i}/{nframes}  Time: {i/fps:.2f}s", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3)
        cv2.putText(frame, f"Frame: {i}/{nframes}  Time: {i/fps:.2f}s", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

        cv2.putText(frame, f"Subject: {subject['subject_name']}", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3)
        cv2.putText(frame, f"Subject: {subject['subject_name']}", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

        cv2.putText(frame, quality_txt, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        writer.write(frame)

        if i % 10 == 0:
            prog(0.10 + 0.40 * (i / max(1, nframes - 1)), "Detecting pose landmarks...")

    cap.release()
    writer.release()
    pose.close()

    # --- Make annotated video browser-playable (H.264) ---
    # OpenCV's mp4v output may not play in Chrome. Convert to H.264 using FFmpeg.
    h264_path = os.path.join(out_dir, "annotated_h264.mp4")
    try:
        import shutil
        ffmpeg_exe = shutil.which("ffmpeg") or r"C:\ffmpeg\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe"
        subprocess.run(
            [
                ffmpeg_exe, "-y",
                "-i", annotated_path,
                "-vcodec", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                h264_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        if os.path.exists(h264_path) and os.path.getsize(h264_path) > 10000:
            annotated_path = h264_path
            print(f"[FFmpeg] SUCCESS: {h264_path} ({os.path.getsize(h264_path)} bytes)")
        else:
            print("[FFmpeg] FAILED: output file missing or too small")
    except subprocess.CalledProcessError as e:
        print(f"[FFmpeg] CalledProcessError: {e.stderr}")
    except FileNotFoundError:
        print("[FFmpeg] NOT FOUND in PATH")
    except Exception as e:
        print(f"[FFmpeg] Unexpected error: {e}")


    df = pd.DataFrame(rows)
    raw_csv = os.path.join(out_dir, "raw_landmarks.csv")
    df.to_csv(raw_csv, index=False)

    prog(0.55, "Interpolating missing frames...")
    coord_cols = [c for c in df.columns if any(c.endswith(s) for s in ("_x", "_y", "_z"))]
    df[coord_cols] = _nan_interp_limit(df[coord_cols].copy(), limit=max_missing)

    prog(0.60, "Applying Butterworth filters...")
    fs = float(fps)
    dt = 1.0 / fs

    scale_m_per_px = _estimate_scale_m_per_px(subject, df)
    subject["scale_m_per_px"] = float(scale_m_per_px)

    def as_xyz(name):
        return df[[f"{name}_x", f"{name}_y", f"{name}_z"]].to_numpy(dtype=float)

    # positions (pixels) and metric positions (meters)
    pos_px = {j: as_xyz(j) for j in ["hip", "knee", "ankle", "shoulder", "elbow", "wrist", "head"]}
    pos_m = {j: pos_px[j] * scale_m_per_px for j in pos_px}

    for j in pos_m:
        x = pos_m[j]
        x = np.nan_to_num(x, nan=np.nanmedian(x, axis=0))
        pos_m[j] = butter_lowpass_filtfilt(x, fs=fs, cutoff_hz=6.0, order=4)

    vel_mps = {j: central_diff(pos_m[j], dt=dt) for j in pos_m}
    for j in vel_mps:
        vel_mps[j] = butter_lowpass_filtfilt(vel_mps[j], fs=fs, cutoff_hz=10.0, order=4)

    acc_mps2 = {j: central_diff(vel_mps[j], dt=dt) for j in vel_mps}
    for j in acc_mps2:
        acc_mps2[j] = butter_lowpass_filtfilt(acc_mps2[j], fs=fs, cutoff_hz=12.0, order=4)

    jerk_mps3 = {j: central_diff(acc_mps2[j], dt=dt) for j in acc_mps2}

    prog(0.70, "Calculating joint angles...")

    # ✅ FIXED pelvis: use stored pelvis columns (already midpoint of L/R hip)
    pelvis = df[["pelvis_x", "pelvis_y", "pelvis_z"]].to_numpy(dtype=float)

    shoulder = as_xyz("shoulder")
    hip = as_xyz("hip")
    knee = as_xyz("knee")
    ankle = as_xyz("ankle")
    elbow = as_xyz("elbow")
    wrist = as_xyz("wrist")
    head = as_xyz("head")
    heel = as_xyz("heel")
    footi = as_xyz("foot_index")

    # ✅ Wrist needs index landmark
    index = as_xyz("index")

    n = len(df)
    angles = {
        "hip_flex_deg": np.zeros(n),
        "knee_flex_deg": np.zeros(n),
        "ankle_dorsi_deg": np.zeros(n),
        "trunk_tilt_deg": np.zeros(n),
        "shoulder_flex_deg": np.zeros(n),
        "elbow_flex_deg": np.zeros(n),
        "wrist_flex_deg": np.zeros(n),     # ✅ ADDED
        "head_flex_deg": np.zeros(n),
    }

    for i in range(n):
        angles["hip_flex_deg"][i] = joint_flexion_deg(shoulder[i], hip[i], knee[i])
        angles["knee_flex_deg"][i] = joint_flexion_deg(hip[i], knee[i], ankle[i])
        angles["ankle_dorsi_deg"][i] = ankle_dorsi_proxy_deg(knee[i], ankle[i], heel[i], footi[i])
        angles["trunk_tilt_deg"][i] = trunk_tilt_deg(pelvis[i], shoulder[i])
        angles["shoulder_flex_deg"][i] = joint_flexion_deg(pelvis[i], shoulder[i], elbow[i])
        angles["elbow_flex_deg"][i] = joint_flexion_deg(shoulder[i], elbow[i], wrist[i])

        # ✅ Wrist flexion proxy: elbow → wrist → index
        angles["wrist_flex_deg"][i] = joint_flexion_deg(elbow[i], wrist[i], index[i])

        angles["head_flex_deg"][i] = head_flexion_deg(shoulder[i], head[i], pelvis[i])

    ang_df = pd.DataFrame({"time_s": df["time_s"].values})
    for k, v in angles.items():
        ang_df[k] = v
        ang_df[k.replace("_deg", "_degps")] = central_diff(v[:, None], dt=dt).ravel()
        ang_df[k.replace("_deg", "_degps2")] = central_diff(ang_df[k.replace("_deg", "_degps")].values[:, None], dt=dt).ravel()

    prog(0.78, "Computing accelerations & jerk...")
    t = df["time_s"].to_numpy(dtype=float)

    acc_rows = []
    for j in ["hip", "knee", "ankle", "shoulder", "elbow", "wrist", "head"]:
        a = acc_mps2[j]
        jrk = jerk_mps3[j]
        acc_res = magnitude(a)
        jerk_res = magnitude(jrk)

        noise_flag = bool(np.nanmax(acc_res) > acc_noise_flag_mps2)

        wk = apply_wk(acc_res, fs=fs)

        s = summarize_joint(acc_res, jerk_res)
        s["noise_flag_acc_gt_50"] = noise_flag
        s["discomfort_frames_jerk_gt_5"] = int(np.sum(jerk_res > jerk_discomfort_mps3))
        s["rms_acc_wk_weighted"] = float(np.sqrt(np.mean(wk ** 2)))

        acc_rows.append((j, s))

    prog(0.82, "Writing CSV exports...")
    out_angles_csv = os.path.join(out_dir, "angles.csv")
    ang_df.to_csv(out_angles_csv, index=False)

    ts = pd.DataFrame({"frame": df["frame"], "time_s": t})
    for j in ["hip", "knee", "ankle", "shoulder", "elbow", "wrist", "head"]:
        ts[[f"{j}_x_m", f"{j}_y_m", f"{j}_z_m"]] = pos_m[j]
        ts[[f"{j}_vx", f"{j}_vy", f"{j}_vz"]] = vel_mps[j]
        ts[[f"{j}_ax", f"{j}_ay", f"{j}_az"]] = acc_mps2[j]
        ts[f"{j}_a_res"] = magnitude(acc_mps2[j])
        ts[f"{j}_jerk_res"] = magnitude(jerk_mps3[j])

    out_ts_csv = os.path.join(out_dir, "timeseries.csv")
    ts.to_csv(out_ts_csv, index=False)

    acc_summary = []
    for j, s in acc_rows:
        acc_summary.append({
            "joint": j,
            "mean_acc_mps2": s["mean_acc"],
            "peak_acc_mps2": s["peak_acc"],
            "rms_acc_mps2": s["rms_acc"],
            "max_jerk_mps3": s["max_jerk"],
            "comfort_index": s["comfort_index"],
            "rms_acc_wk_weighted": s["rms_acc_wk_weighted"],
            "noise_flag_acc_gt_50": s["noise_flag_acc_gt_50"],
            "discomfort_frames_jerk_gt_5": s["discomfort_frames_jerk_gt_5"],
        })
    acc_summary_df = pd.DataFrame(acc_summary)
    out_acc_csv = os.path.join(out_dir, "acceleration_summary.csv")
    acc_summary_df.to_csv(out_acc_csv, index=False)

    prog(0.88, "Generating graphs...")

    # ✅ include wrist graph in plots
    for col, title, yl in [
        ("hip_flex_deg", "Left Hip Flexion vs Time", "Angle (deg)"),
        ("knee_flex_deg", "Left Knee Flexion vs Time", "Angle (deg)"),
        ("ankle_dorsi_deg", "Left Ankle Dorsi/Plantar Proxy vs Time", "Angle (deg)"),
        ("trunk_tilt_deg", "Trunk Anterior Tilt vs Time", "Angle (deg)"),
        ("shoulder_flex_deg", "Left Shoulder Flexion vs Time", "Angle (deg)"),
        ("elbow_flex_deg", "Left Elbow Flexion vs Time", "Angle (deg)"),
        ("wrist_flex_deg", "Left Wrist Flexion (Proxy) vs Time", "Angle (deg)"),
        ("head_flex_deg", "Head Flexion (Head-Trunk) vs Time", "Angle (deg)"),
    ]:
        outp = os.path.join(graphs_dir, f"{col}.png")
        plot_timeseries(t, ang_df[col].to_numpy(), title, yl, outp)

    jerk_cols = [f"{j}_jerk_res" for j in ["hip", "knee", "ankle", "shoulder", "elbow", "wrist", "head"]]
    jerk_max = ts[jerk_cols].max(axis=1).to_numpy()
    jerk_png = os.path.join(graphs_dir, "jerk_max.png")
    plot_timeseries(t, jerk_max, "Jerk (max across joints) vs Time", "Jerk (m/s³)", jerk_png, threshold=jerk_discomfort_mps3)

    def rom_stats(x: np.ndarray):
        return float(np.max(x)), float(np.std(x)), float(np.min(x)), float(np.std(x)), float(np.ptp(x)), float(np.std(x))

    lower_rows = []
    for label, col in [
        ("Left Hip Flexion", "hip_flex_deg"),
        ("Left Knee Flexion", "knee_flex_deg"),
        ("Left Ankle Dorsiflex (Proxy)", "ankle_dorsi_deg"),
    ]:
        mx, mxs, mn, mns, rg, rgs = rom_stats(ang_df[col].to_numpy())
        lower_rows.append([label, f"{mx:.1f} ± {mxs:.1f}°", f"{mn:.1f} ± {mns:.1f}°", f"{rg:.1f} ± {rgs:.1f}°"])

    upper_rows = []
    for label, col in [
        ("Trunk Anterior Tilt", "trunk_tilt_deg"),
        ("Left Shoulder Flexion", "shoulder_flex_deg"),
        ("Left Elbow Flexion", "elbow_flex_deg"),
        ("Left Wrist Flexion (Proxy)", "wrist_flex_deg"),
        ("Head Flexion", "head_flex_deg"),
    ]:
        mx, mxs, mn, mns, rg, rgs = rom_stats(ang_df[col].to_numpy())
        upper_rows.append([label, f"{mx:.1f} ± {mxs:.1f}°", f"{mn:.1f} ± {mns:.1f}°", f"{rg:.1f} ± {rgs:.1f}°"])

    prog(0.94, "Creating PDF report...")
    pdf_path = os.path.join(out_dir, "report.pdf")
    analysis_date = date.today().isoformat()

    subject_pdf = dict(subject)
    subject_pdf["bmi"] = _bmi(subject["height_cm"], subject["weight_kg"])

    # ✅ split upper vs head ROM for the minimal report generator
    upper_only_rows = []
    head_only_rows = []
    for row in upper_rows:
        if row[0].strip().lower().startswith("head"):
            head_only_rows.append(row)
        else:
            upper_only_rows.append(row)

    rom = {
        "lower": lower_rows,
        "upper": upper_only_rows,   # trunk/shoulder/elbow/wrist
        "head": head_only_rows,     # head only
    }

    build_qualisys_pdf_minimal(
        out_pdf=pdf_path,
        subject=subject_pdf,
        analysis_date=analysis_date,
        graphs_dir=graphs_dir,
        rom=rom,
        recorded_date=subject_pdf.get("recording_date", analysis_date),
        upload_date=analysis_date,
        rec_id=str(subject_pdf.get("id", "1")),
    )

    prog(0.98, "Finalizing outputs...")
    summary = {
        "video_qc": qc,
        "quality_ok_frame_pct": float(100.0 * ok_count / max(1, len(df))),
        "subject": subject_pdf,
        "comfort_summary": {j: s for j, s in acc_rows},
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    prog(1.0, "Done.")
    return {
        "annotated_video": annotated_path,
        "pdf_report": pdf_path,
        "raw_landmarks_csv": raw_csv,
        "angles_csv": out_angles_csv,
        "timeseries_csv": out_ts_csv,
        "acceleration_summary_csv": out_acc_csv,
        "graphs_dir": graphs_dir,
        "summary": summary,
    }