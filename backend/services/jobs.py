import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("uvicorn")

JOB_TTL_SECONDS = 900  # 15 minutes TTL for finished jobs


@dataclass
class Job:
    id: str
    status: str = "queued"  # "queued", "running", "completed", "failed", "canceled"
    progress: int = 0
    step: str = "Initialized"
    result_path: Optional[Path] = None
    result_media_type: Optional[str] = None
    result_filename: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + JOB_TTL_SECONDS)
    _cancel_requested: bool = False


class JobStore:
    """In-memory thread-safe background job registry with TTL expiration."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create_job(self) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id)
        with self._lock:
            self._cleanup_expired()
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            self._cleanup_expired()
            return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        step: Optional[str] = None,
        result_path: Optional[Path] = None,
        result_media_type: Optional[str] = None,
        result_filename: Optional[str] = None,
        error: Optional[str] = None
    ):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = max(0, min(100, progress))
            if step is not None:
                job.step = step
            if result_path is not None:
                job.result_path = result_path
            if result_media_type is not None:
                job.result_media_type = result_media_type
            if result_filename is not None:
                job.result_filename = result_filename
            if error is not None:
                job.error = error

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.status in ("queued", "running"):
                job._cancel_requested = True
                job.status = "canceled"
                job.step = "Canceled by user"
                return True
            return False

    def is_canceled(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job._cancel_requested)

    def _cleanup_expired(self):
        now = time.time()
        expired_ids = [jid for jid, j in self._jobs.items() if j.expires_at < now]
        for jid in expired_ids:
            job = self._jobs.pop(jid, None)
            if job and job.result_path and job.result_path.exists():
                try:
                    job.result_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Error removing expired job file {job.result_path}: {e}")


# Singleton job store
job_store = JobStore()
