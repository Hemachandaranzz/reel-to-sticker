import sys
from pathlib import Path

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

for p in (PROJECT_ROOT, BACKEND_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import backend.config
import backend.services
import backend.services.limiter
import backend.services.ffmpeg
import backend.services.optimizer
import backend.services.validate
import backend.routers
import backend.routers.sticker

sys.modules["config"] = backend.config
sys.modules["services"] = backend.services
sys.modules["services.limiter"] = backend.services.limiter
sys.modules["services.ffmpeg"] = backend.services.ffmpeg
sys.modules["services.optimizer"] = backend.services.optimizer
sys.modules["services.validate"] = backend.services.validate
sys.modules["routers"] = backend.routers
sys.modules["routers.sticker"] = backend.routers.sticker


import pytest
from backend.services.ffmpeg import run_ffmpeg


@pytest.fixture(scope="session")
def sample_mp4(tmp_path_factory) -> Path:
    """Generate a tiny 1-second 320x240 valid MP4 file using FFmpeg testsrc."""
    temp_dir = tmp_path_factory.mktemp("media")
    video_path = temp_dir / "test_sample.mp4"
    run_ffmpeg([
        "-f", "lavfi",
        "-i", "testsrc=duration=1:size=320x240:rate=30",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-y",
        str(video_path)
    ])
    return video_path


@pytest.fixture(scope="session")
def generate_clip(tmp_path_factory):
    """Generate sample test videos of arbitrary duration with caching."""
    media_dir = tmp_path_factory.mktemp("clips")
    cache = {}

    def _make(duration_sec: int) -> Path:
        if duration_sec in cache:
            return cache[duration_sec]
        path = media_dir / f"test_{duration_sec}s.mp4"
        run_ffmpeg([
            "-f", "lavfi",
            "-i", f"testsrc=duration={duration_sec}:size=320x240:rate=15",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-y",
            str(path)
        ])
        cache[duration_sec] = path
        return path

    return _make


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter quota between tests so tests don't interfere."""
    from backend.main import app
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()
    try:
        from backend.services.limiter import limiter
        limiter.reset()
    except Exception:
        pass
    yield
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()
    try:
        from backend.services.limiter import limiter
        limiter.reset()
    except Exception:
        pass





