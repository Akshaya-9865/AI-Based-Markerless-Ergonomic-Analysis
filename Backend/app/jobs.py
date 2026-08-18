from __future__ import annotations
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class JobRecord:
    job_id: str
    state: str = "queued"
    progress: float = 0.0
    message: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)
    cancel_flag: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str) -> JobRecord:
        with self._lock:
            rec = JobRecord(job_id=job_id)
            self._jobs[job_id] = rec
            return rec

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs) -> None:
        rec = self.get(job_id)
        if not rec:
            return
        with rec.lock:
            for k, v in kwargs.items():
                setattr(rec, k, v)

    def cancel(self, job_id: str) -> None:
        rec = self.get(job_id)
        if not rec:
            return
        with rec.lock:
            rec.cancel_flag = True
            if rec.state in ("queued", "running"):
                rec.state = "cancelled"
                rec.message = "Cancelled by user."

job_store = JobStore()
