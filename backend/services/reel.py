import re
import urllib.parse
from typing import Any, Dict
from fastapi import HTTPException

# Allowed hosts strictly
ALLOWED_HOSTS = {"instagram.com", "www.instagram.com"}

# Allowed path patterns for Reels and Posts
REEL_PATH_REGEX = re.compile(r"^/(?:reel|reels|p)/([A-Za-z0-9_-]+)/?$", re.IGNORECASE)


def validate_instagram_url(raw_url: str) -> Dict[str, Any]:
    """
    Strictly validate Instagram Reel URL without fetching.
    - HTTPS only
    - Strictly instagram.com or www.instagram.com (no lookalikes or subdomains)
    - Valid reel or post path
    - Strips all tracking and query params
    - NEVER issues network requests (SSRF-safe)
    """
    if not raw_url or not isinstance(raw_url, str):
        raise HTTPException(
            status_code=400,
            detail="URL is required and must be a valid string."
        )

    clean_input = raw_url.strip()
    try:
        parsed = urllib.parse.urlparse(clean_input)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format.")

    # 1. Scheme must be HTTPS
    if parsed.scheme.lower() != "https":
        raise HTTPException(
            status_code=400,
            detail="Only secure HTTPS URLs from Instagram are accepted (e.g. https://www.instagram.com/reel/...)."
        )

    # 2. Hostname must be strictly instagram.com or www.instagram.com
    hostname = (parsed.hostname or "").lower()
    if hostname not in ALLOWED_HOSTS:
        raise HTTPException(
            status_code=400,
            detail=f"Host '{hostname}' is not allowed. Only instagram.com or www.instagram.com is permitted."
        )

    # 3. Reject any user credentials or weird ports
    if parsed.username or parsed.password or parsed.port:
        raise HTTPException(
            status_code=400,
            detail="URL contains invalid user info or port."
        )

    # 4. Path must match reel/reels/p with valid shortcode
    match = REEL_PATH_REGEX.match(parsed.path)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid Reel URL format. URL must look like https://www.instagram.com/reel/SHORTCODE/ or /p/SHORTCODE/."
        )

    shortcode = match.group(1)
    clean_url = f"https://www.instagram.com/reel/{shortcode}/"
    embed_url = f"https://www.instagram.com/reel/{shortcode}/embed"

    return {
        "valid": True,
        "shortcode": shortcode,
        "clean_url": clean_url,
        "embed_url": embed_url,
        "guidance": [
            "1. Open the reel in the Instagram app or browser.",
            "2. Tap Share and select 'Download' (available for Reels allowed by the creator).",
            "3. Upload the downloaded video here to trim, crop, style, and export as a WhatsApp sticker."
        ]
    }
