from __future__ import annotations
import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from .config import settings
from .models import AnalysisRequest, JobStatus, ResultsResponse
from .jobs import job_store
from .analysis.pipeline import run_analysis
from .storage import ensure_dir

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_dir(settings.UPLOAD_DIR)
ensure_dir(settings.OUTPUT_DIR)

# Serve outputs and uploads
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

executor = ThreadPoolExecutor(max_workers=1)

@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.APP_NAME}

@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename.")
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in [".mp4", ".avi", ".mov"]:
        raise HTTPException(400, "Only MP4/AVI/MOV supported.")
    video_id = str(uuid.uuid4())
    out_path = os.path.join(settings.UPLOAD_DIR, f"{video_id}{ext}")
    with open(out_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # size check
    sz = os.path.getsize(out_path) / (1024 * 1024)
    if sz > settings.MAX_UPLOAD_MB:
        os.remove(out_path)
        raise HTTPException(400, f"File too large. Max {settings.MAX_UPLOAD_MB}MB.")

    return {"video_id": video_id, "path": f"/uploads/{os.path.basename(out_path)}"}

@app.post("/api/analyze", response_model=JobStatus)
def analyze(req: AnalysisRequest):
    job_id = str(uuid.uuid4())
    rec = job_store.create(job_id)
    job_store.update(job_id, state="queued", progress=0.0, message="Queued...")

    # Locate video
    # we don't store extension in id; find by prefix
    candidates = [f for f in os.listdir(settings.UPLOAD_DIR) if f.startswith(req.video_id)]
    if not candidates:
        raise HTTPException(404, "Video not found. Upload first.")
    video_file = os.path.join(settings.UPLOAD_DIR, candidates[0])

    out_dir = os.path.join(settings.OUTPUT_DIR, job_id)
    ensure_dir(out_dir)

    subject = req.subject.model_dump()
    subject["seat_reference_length_cm"] = req.seat_reference_length_cm
    subject["seat_reference_pixel_length"] = req.seat_reference_pixel_length

    def progress_cb(p, msg):
        job_store.update(job_id, state="running", progress=float(p), message=str(msg))

    def cancel_cb():
        j = job_store.get(job_id)
        return bool(j and j.cancel_flag)

    def work():
        try:
            job_store.update(job_id, state="running", progress=0.02, message="Starting analysis...")
            outputs = run_analysis(
                video_path=video_file,
                out_dir=out_dir,
                subject=subject,
                min_vis=settings.MIN_VISIBILITY,
                max_missing=settings.MAX_MISSING_CONSECUTIVE,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
                acc_noise_flag_mps2=settings.ACC_NOISE_FLAG_MPS2,
                jerk_discomfort_mps3=settings.JERK_DISCOMFORT_MPS3,
            )
            if cancel_cb():
                job_store.update(job_id, state="cancelled", progress=0.0, message="Cancelled.")
                return
            job_store.update(job_id, state="done", progress=1.0, message="Completed.", detail=outputs["summary"])
        except Exception as e:
            job_store.update(job_id, state="error", progress=0.0, message=str(e))

    executor.submit(work)
    return JobStatus(job_id=job_id, state=rec.state, progress=rec.progress, message=rec.message)

@app.get("/api/status/{job_id}", response_model=JobStatus)
def status(job_id: str):
    rec = job_store.get(job_id)
    if not rec:
        raise HTTPException(404, "Job not found.")
    return JobStatus(job_id=job_id, state=rec.state, progress=rec.progress, message=rec.message, detail=rec.detail or None)

@app.post("/api/cancel/{job_id}")
def cancel(job_id: str):
    job_store.cancel(job_id)
    return {"ok": True}

@app.get("/api/results/{job_id}", response_model=ResultsResponse)
def results(job_id: str):
    rec = job_store.get(job_id)
    if not rec:
        raise HTTPException(404, "Job not found.")
    if rec.state != "done":
        raise HTTPException(400, f"Job not done. Current state: {rec.state}")

    base = f"/outputs/{job_id}"
    files = {
        "pdf_report": f"{base}/report.pdf",
        "annotated_video": f"{base}/annotated_h264.mp4" if os.path.exists(os.path.join("outputs", job_id, "annotated_h264.mp4")) else f"{base}/annotated.mp4",
        "raw_landmarks_csv": f"{base}/raw_landmarks.csv",
        "angles_csv": f"{base}/angles.csv",
        "timeseries_csv": f"{base}/timeseries.csv",
        "acceleration_summary_csv": f"{base}/acceleration_summary.csv",
        "graphs_dir": f"{base}/graphs",
        "summary_json": f"{base}/summary.json",
    }
    return ResultsResponse(job_id=job_id, files=files, summary=rec.detail or {})
