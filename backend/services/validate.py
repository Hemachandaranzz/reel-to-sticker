import logging
from pathlib import Path
from typing import Any, Dict
from fastapi import HTTPException, UploadFile

try:
    from backend import config
    from backend.services.ffmpeg import probe_video_file
except ImportError:
    import config
    from services.ffmpeg import probe_video_file

logger = logging.getLogger("uvicorn")



def parse_fps(rate_str: str) -> float:
    """Parse frame rate string like '30/1' or '29.97'."""
    if not rate_str or rate_str == "0/0":
        return 30.0
    if "/" in rate_str:
        num, den = rate_str.split("/", 1)
        try:
            den_val = float(den)
            if den_val == 0:
                return 30.0
            return float(num) / den_val
        except (ValueError, ZeroDivisionError):
            return 30.0
    try:
        return float(rate_str)
    except ValueError:
        return 30.0


async def save_upload_to_temp(upload_file: UploadFile, destination_path: Path) -> Path:
    """Stream upload to disk in chunks, enforcing extension and size limit."""
    filename = upload_file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}"
        )

    max_bytes = config.MAX_UPLOAD_MB * 1024 * 1024
    total_bytes = 0
    oversized = False

    try:
        with open(destination_path, "wb") as f:
            while chunk := await upload_file.read(1024 * 64):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    oversized = True
                    break
                f.write(chunk)
    except Exception as e:
        destination_path.unlink(missing_ok=True)
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded file to temporary storage."
        )

    if oversized:
        destination_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {config.MAX_UPLOAD_MB} MB."
        )

    if total_bytes == 0:
        destination_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    return destination_path



def validate_video(file_path: Path | str) -> Dict[str, Any]:
    """Validate that the file contains a readable, valid video stream."""
    data = probe_video_file(file_path)
    streams = data.get("streams", [])
    if not streams:
        raise HTTPException(
            status_code=422,
            detail="No valid video stream found in the uploaded file."
        )

    stream = streams[0]
    try:
        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))
    except (ValueError, TypeError):
        width, height = 0, 0

    if width <= 0 or height <= 0:
        raise HTTPException(
            status_code=422,
            detail="Uploaded video has invalid or missing dimensions."
        )

    if width > 7680 or height > 4320:
        raise HTTPException(
            status_code=422,
            detail=f"Video resolution ({width}x{height}) exceeds maximum supported resolution (8K)."
        )

    # Determine duration
    duration = None
    stream_dur = stream.get("duration")
    if stream_dur is not None:
        try:
            val = float(stream_dur)
            if val > 0:
                duration = val
        except (ValueError, TypeError):
            pass

    if duration is None:
        format_dur = data.get("format", {}).get("duration")
        if format_dur is not None:
            try:
                val = float(format_dur)
                if val > 0:
                    duration = val
            except (ValueError, TypeError):
                pass

    if duration is None or duration <= 0:
        raise HTTPException(
            status_code=422,
            detail="Could not determine video duration or duration is zero."
        )

    # Max duration is 10 minutes (600 seconds) for uploads
    if duration > 600.0:
        raise HTTPException(
            status_code=422,
            detail="Video duration exceeds maximum allowed length of 10 minutes."
        )

    fps = parse_fps(stream.get("avg_frame_rate", "") or stream.get("r_frame_rate", ""))

    return {
        "duration": round(duration, 3),
        "width": width,
        "height": height,
        "fps": round(fps, 2)
    }
