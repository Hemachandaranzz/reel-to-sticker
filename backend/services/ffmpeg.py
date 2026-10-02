import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

import asyncio
from contextlib import asynccontextmanager

try:
    from config import FFMPEG_TIMEOUT, FFMPEG_THREADS, MAX_CONCURRENT_FFMPEG
except ImportError:
    from backend.config import FFMPEG_TIMEOUT, FFMPEG_THREADS, MAX_CONCURRENT_FFMPEG

logger = logging.getLogger("uvicorn")

_ffmpeg_semaphore: Optional[asyncio.Semaphore] = None


def get_ffmpeg_semaphore() -> asyncio.Semaphore:
    global _ffmpeg_semaphore
    if _ffmpeg_semaphore is None:
        _ffmpeg_semaphore = asyncio.Semaphore(MAX_CONCURRENT_FFMPEG)
    return _ffmpeg_semaphore


@asynccontextmanager
async def ffmpeg_slot(timeout: float = 8.0):
    """Acquire a slot under the FFmpeg concurrency semaphore, returning 429 if full."""
    sem = get_ffmpeg_semaphore()
    try:
        await asyncio.wait_for(sem.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=429,
            detail="Server is busy processing other media conversions. Please retry shortly."
        )
    try:
        yield
    finally:
        sem.release()


def ensure_tool_path(tool_name: str) -> str:
    """Find the tool binary in PATH or standard WinGet locations."""
    path = shutil.which(tool_name)
    if path:
        return path

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_packages.exists():
            for p in winget_packages.glob(f"**/{tool_name}.exe"):
                bin_dir = str(p.parent)
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
                return str(p)

    raise HTTPException(
        status_code=500,
        detail=f"Required media tool '{tool_name}' is not installed or not in PATH."
    )


def run_ffmpeg(args: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Run FFmpeg command safely with timeout, thread limits, and captured output."""
    ffmpeg_bin = ensure_tool_path("ffmpeg")
    cmd = [ffmpeg_bin, "-nostdin"]
    if "-threads" not in args:
        cmd.extend(["-threads", str(FFMPEG_THREADS)])
    cmd.extend(args)
    timeout_val = timeout or FFMPEG_TIMEOUT


    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_val
        )
        if result.returncode != 0:
            err = result.stderr.strip()
            # Extract last line or summary of error
            last_err = err.splitlines()[-1] if err else "Unknown FFmpeg error"
            logger.error(f"FFmpeg failed (code {result.returncode}): {last_err}")
            raise HTTPException(
                status_code=422,
                detail=f"FFmpeg processing failed: {last_err}"
            )
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg command timed out after {timeout_val}s")
        raise HTTPException(
            status_code=422,
            detail=f"FFmpeg processing timed out after {timeout_val} seconds."
        )


def run_ffprobe(args: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Run FFprobe command safely with timeout and captured output."""
    ffprobe_bin = ensure_tool_path("ffprobe")
    cmd = [ffprobe_bin, *args]
    timeout_val = timeout or FFMPEG_TIMEOUT


    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_val
        )
        if result.returncode != 0:
            err = result.stderr.strip()
            last_err = err.splitlines()[-1] if err else "Unknown FFprobe error"
            logger.warning(f"FFprobe failed: {last_err}")
            raise HTTPException(
                status_code=422,
                detail="Invalid media file or unreadable video format."
            )
        return result
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=422,
            detail=f"FFprobe command timed out after {timeout_val} seconds."
        )


def probe_video_file(file_path: Path | str) -> Dict[str, Any]:
    """Inspect video file and return parsed JSON streams/format."""
    args = [
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,avg_frame_rate,duration,nb_frames:format=duration,size",
        "-of", "json",
        str(file_path)
    ]
    result = run_ffprobe(args)
    try:
        data = json.loads(result.stdout)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse media probe output: {str(e)}"
        )
