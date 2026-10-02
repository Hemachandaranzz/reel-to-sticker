import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# Add backend and project root directory to sys.path so both 'backend.*' and direct imports work
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
for p in (str(BACKEND_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


try:
    from config import CORS_ORIGINS, RATE_LIMIT_PER_MINUTE
except ImportError:
    from backend.config import CORS_ORIGINS, RATE_LIMIT_PER_MINUTE

logger = logging.getLogger("uvicorn")


def ensure_ffmpeg_in_path():
    """Ensure ffmpeg can be found, checking standard WinGet install locations if not in PATH."""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_packages.exists():
            for p in winget_packages.glob("**/ffmpeg.exe"):
                bin_dir = str(p.parent)
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
                logger.info(f"Added FFmpeg to PATH from: {bin_dir}")
                break


def check_ffmpeg_tooling() -> bool:
    ensure_ffmpeg_in_path()
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")

    if not ffmpeg_path:
        logger.error("FFmpeg executable not found in PATH! Video/sticker conversion will fail.")
        return False
    if not ffprobe_path:
        logger.error("FFprobe executable not found in PATH! Video inspection will fail.")
        return False
    try:
        res = subprocess.run(
            [ffmpeg_path, "-encoders"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "libwebp" not in res.stdout:
            logger.error("FFmpeg was found, but libwebp encoder is NOT available in this build!")
            return False
        logger.info("FFmpeg and FFprobe verified successfully with libwebp support.")
        return True
    except Exception as e:
        logger.error(f"Error checking FFmpeg encoders: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_ffmpeg_tooling()
    yield


try:
    from backend.services.limiter import limiter
except ImportError:
    from services.limiter import limiter


app = FastAPI(title="Reel to WhatsApp Sticker API", lifespan=lifespan)
app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    try:
        response = await call_next(request)
        elapsed = time.time() - start_time
        content_len = response.headers.get("content-length", "-")
        logger.info(
            f"req_id={req_id} method={request.method} path={request.url.path} "
            f"status={response.status_code} duration={elapsed:.3f}s bytes={content_len}"
        )
        response.headers["X-Request-ID"] = req_id
        return response
    except HTTPException:
        raise
    except Exception as exc:
        elapsed = time.time() - start_time
        logger.error(
            f"req_id={req_id} method={request.method} path={request.url.path} "
            f"error={exc} duration={elapsed:.3f}s"
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
            headers={"X-Request-ID": req_id}
        )


try:
    from services.validate import save_upload_to_temp, validate_video
    from routers.sticker import router as sticker_router
    from routers.reel import router as reel_router
    from routers.packs import router as packs_router
    from routers.jobs import router as jobs_router
except ImportError:
    from backend.services.validate import save_upload_to_temp, validate_video
    from backend.routers.sticker import router as sticker_router
    from backend.routers.reel import router as reel_router
    from backend.routers.packs import router as packs_router
    from backend.routers.jobs import router as jobs_router

app.include_router(sticker_router)
app.include_router(reel_router)
app.include_router(packs_router)
app.include_router(jobs_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/probe")
async def probe(file: UploadFile = File(...)):
    """Probe video and return duration, dimensions, and fps for client trim controls."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ext = Path(file.filename or "video.mp4").suffix or ".mp4"
        temp_file = Path(tmp_dir) / f"upload{ext}"
        await save_upload_to_temp(file, temp_file)
        metadata = validate_video(temp_file)
        return metadata


# --- Production Static File Serving for Single-Service Cloud Deployment ---
possible_dist_dirs = [
    Path(__file__).resolve().parent.parent / "frontend" / "dist",
    Path(__file__).resolve().parent / "dist",
    Path(__file__).resolve().parent / "static",
    Path("/app/frontend/dist"),
    Path("/app/dist"),
]

FRONTEND_DIST = next((d for d in possible_dist_dirs if (d / "index.html").is_file()), None)

if FRONTEND_DIST:
    logger.info(f"Serving frontend static build from: {FRONTEND_DIST}")
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")

