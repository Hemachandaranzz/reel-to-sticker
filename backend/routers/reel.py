import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from backend.config import RATE_LIMIT_PER_MINUTE
    from backend.services.limiter import limiter
    from backend.services.reel import validate_instagram_url
except ImportError:
    from config import RATE_LIMIT_PER_MINUTE
    from services.limiter import limiter
    from services.reel import validate_instagram_url

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/reel", tags=["reel"])


class ReelCheckRequest(BaseModel):
    url: str = Field(..., description="Instagram Reel URL to check (e.g. https://www.instagram.com/reel/...)")


@router.post("/check")
@limiter.limit(RATE_LIMIT_PER_MINUTE)
async def check_reel_url(request: Request, body: ReelCheckRequest):
    """
    Validate an Instagram Reel URL safely without scraping or issuing HTTP requests.
    Strips tracking params and returns shortcode and guided upload steps.
    """
    return validate_instagram_url(body.url)
