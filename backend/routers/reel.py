import logging
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

try:
    from backend.config import RATE_LIMIT_PER_MINUTE
    from backend.services.downloader import download_video_from_url
    from backend.services.limiter import limiter
    from backend.services.reel import validate_instagram_url
except ImportError:
    from config import RATE_LIMIT_PER_MINUTE
    from services.downloader import download_video_from_url
    from services.limiter import limiter
    from services.reel import validate_instagram_url

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/reel", tags=["reel"])


class ReelCheckRequest(BaseModel):
    url: str = Field(..., description="Instagram Reel or video URL to process")


@router.post("/check")
@limiter.limit(RATE_LIMIT_PER_MINUTE)
async def check_reel_url(request: Request, body: ReelCheckRequest):
    """
    Validate an Instagram Reel URL safely without scraping or issuing HTTP requests.
    Strips tracking params and returns shortcode and guided upload steps.
    """
    return validate_instagram_url(body.url)


@router.post("/download")
@limiter.limit(RATE_LIMIT_PER_MINUTE)
async def download_reel_video(request: Request, body: ReelCheckRequest):
    """
    Directly download an Instagram Reel / video URL and return the video stream.
    Enables automatic zero-manual-download loading directly into the editor studio.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        video_path, meta = download_video_from_url(body.url, Path(tmp_dir))
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        return Response(
            content=video_bytes,
            media_type="video/mp4",
            headers={
                "Content-Disposition": 'attachment; filename="reel.mp4"',
                "X-Video-Duration": str(meta["duration"]),
                "X-Video-Width": str(meta["width"]),
                "X-Video-Height": str(meta["height"]),
                "X-Video-Fps": str(meta["fps"]),
            }
        )
