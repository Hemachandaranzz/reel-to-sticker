import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

try:
    from backend.services.jobs import job_store
except ImportError:
    from services.jobs import job_store

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve current background job status, progress percentage, and current step."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found or expired.")

    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "step": job.step,
        "error": job.error,
        "has_result": bool(job.result_path and job.result_path.exists()),
        "result_url": f"/api/jobs/{job.id}/result" if job.result_path and job.result_path.exists() else None,
    }


@router.get("/{job_id}/result")
async def get_job_result(job_id: str):
    """Download the completed result artifact for a background job."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found or expired.")

    if job.status != "completed" or not job.result_path or not job.result_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Job '{job_id}' result is not available (status: {job.status})."
        )

    filename = job.result_filename or "sticker_result"
    media_type = job.result_media_type or "application/octet-stream"

    return FileResponse(
        path=job.result_path,
        media_type=media_type,
        filename=filename,
    )


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Request early cancellation of a running background job."""
    success = job_store.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Job '{job_id}' could not be canceled (already finished or not found)."
        )
    return {"status": "canceled", "job_id": job_id}
