import os
from typing import List, Set

MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_EXTENSIONS: Set[str] = {".mp4", ".mov", ".webm", ".m4v", ".gif"}
STATIC_MAX_BYTES: int = int(os.getenv("STATIC_MAX_BYTES", "100000"))
ANIMATED_MAX_BYTES: int = int(os.getenv("ANIMATED_MAX_BYTES", "500000"))
MAX_DURATION: float = float(os.getenv("MAX_DURATION", "10.0"))
FFMPEG_TIMEOUT: int = int(os.getenv("FFMPEG_TIMEOUT", "60"))
MAX_CONCURRENT_FFMPEG: int = int(os.getenv("MAX_CONCURRENT_FFMPEG", "2"))
RATE_LIMIT_PER_MINUTE: str = os.getenv("RATE_LIMIT_PER_MINUTE", "10/minute")
FFMPEG_THREADS: int = int(os.getenv("FFMPEG_THREADS", "2"))
ENABLE_CUTOUT: bool = os.getenv("ENABLE_CUTOUT", "true").lower() in ("1", "true", "yes")



CORS_ORIGINS: List[str] = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
