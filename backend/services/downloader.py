import logging
from pathlib import Path
from typing import Any, Dict, Tuple
from fastapi import HTTPException
import yt_dlp

try:
    from backend.services.validate import validate_video
except ImportError:
    from services.validate import validate_video

logger = logging.getLogger("uvicorn")


def download_video_from_url(url: str, output_dir: Path) -> Tuple[Path, Dict[str, Any]]:
    """
    Download video directly from URL (Instagram Reel, YouTube, etc.) using yt-dlp.
    Saves to output_dir, validates content with ffprobe, and returns (path, metadata).
    """
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="A valid video URL must be provided.")

    clean_url = url.strip()
    out_template = str(output_dir / "downloaded_video.%(ext)s")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': out_template,
        'max_filesize': 50 * 1024 * 1024,  # 50 MB limit
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 20,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(clean_url, download=True)

        downloaded_files = list(output_dir.glob("downloaded_video.*"))
        if not downloaded_files:
            raise HTTPException(
                status_code=422,
                detail="Unable to extract video stream from the provided URL."
            )

        video_path = downloaded_files[0]
        meta = validate_video(video_path)
        return video_path, meta

    except HTTPException:
        raise
    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        logger.warning(f"yt-dlp download failed for '{clean_url}': {err_msg}")
        if "Private" in err_msg or "login" in err_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="This Instagram Reel is private or requires login. Only public reels can be downloaded directly."
            )
        raise HTTPException(
            status_code=422,
            detail=f"Failed to download video: {err_msg.splitlines()[-1] if err_msg else 'Unknown error'}"
        )
    except Exception as e:
        logger.error(f"Error downloading video from '{clean_url}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while downloading the video: {str(e)}"
        )
