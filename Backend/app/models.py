from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
from datetime import date

Sex = Literal["Male", "Female", "Other"]

class SubjectDetails(BaseModel):
    subject_name: str = Field(..., min_length=1)
    age_years: int = Field(..., ge=1, le=120)
    sex: Sex
    height_cm: float = Field(..., ge=50, le=250)
    weight_kg: float = Field(..., ge=10, le=300)
    camera_distance_m: float = Field(..., ge=0.5, le=10)
    recording_date: date = Field(default_factory=date.today)

class AnalysisRequest(BaseModel):
    video_id: str
    subject: SubjectDetails
    # Optional calibration knobs (kept optional to match your spec)
    # If you can provide a known seat reference length in cm, metric accel improves.
    seat_reference_length_cm: Optional[float] = None
    seat_reference_pixel_length: Optional[float] = None  # if you measure once offline

class JobStatus(BaseModel):
    job_id: str
    state: Literal["queued", "running", "done", "error", "cancelled"]
    progress: float = 0.0
    message: str = ""
    detail: Optional[Dict[str, Any]] = None

class ResultsResponse(BaseModel):
    job_id: str
    files: Dict[str, str]
    summary: Dict[str, Any]
