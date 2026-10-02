import io
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.parametrize("duration_sec", [3, 5, 10])
def test_animated_sticker_durations(generate_clip, duration_sec):
    """Verify that 3s, 5s, and 10s test clips all produce <= 500 KB animated stickers with infinite loop."""
    video_path = generate_clip(duration_sec)

    with TestClient(app) as client:
        with open(video_path, "rb") as f:
            response = client.post(
                "/api/sticker/animated",
                files={"file": (f"test_{duration_sec}s.mp4", f, "video/mp4")},
                data={
                    "start": 0.0,
                    "duration": float(duration_sec),
                    "fit": "contain",
                    "speed": 1.0,
                }
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert "X-Sticker-Size" in response.headers
        assert "X-Sticker-Fps" in response.headers
        assert "X-Sticker-Duration" in response.headers

        content = response.content
        assert len(content) <= 500_000, f"Clip of {duration_sec}s exceeded 500 KB: {len(content)} bytes"

        # Validate with Pillow
        img = Image.open(io.BytesIO(content))
        assert img.format == "WEBP"
        assert img.size == (512, 512)
        assert getattr(img, "is_animated", False) is True
        assert getattr(img, "n_frames", 1) > 1
        assert img.info.get("loop", 0) == 0, "Sticker must loop infinitely"


def test_animated_sticker_cover_fit(generate_clip):
    """Verify cover fit mode produces valid 512x512 sticker."""
    video_path = generate_clip(3)
    with TestClient(app) as client:
        with open(video_path, "rb") as f:
            response = client.post(
                "/api/sticker/animated",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={"start": 0.0, "duration": 2.0, "fit": "cover", "speed": 1.0}
            )
        assert response.status_code == 200
        assert len(response.content) <= 500_000
        img = Image.open(io.BytesIO(response.content))
        assert img.size == (512, 512)


def test_animated_sticker_out_of_range_start(generate_clip):
    """Verify start timestamp past video duration returns 400."""
    video_path = generate_clip(3)
    with TestClient(app) as client:
        with open(video_path, "rb") as f:
            response = client.post(
                "/api/sticker/animated",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={"start": 99.0, "duration": 2.0}
            )
        assert response.status_code == 400
        assert "outside video duration" in response.json()["detail"]


def test_animated_sticker_duration_over_10s(generate_clip):
    """Verify duration > 10 returns 400."""
    video_path = generate_clip(3)
    with TestClient(app) as client:
        with open(video_path, "rb") as f:
            response = client.post(
                "/api/sticker/animated",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={"start": 0.0, "duration": 15.0}
            )
        assert response.status_code == 400
        assert "exceed 10 seconds" in response.json()["detail"]


def test_animated_sticker_invalid_speed(generate_clip):
    """Verify speed outside [0.5, 2.0] returns 400."""
    video_path = generate_clip(3)
    with TestClient(app) as client:
        with open(video_path, "rb") as f:
            response = client.post(
                "/api/sticker/animated",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={"start": 0.0, "duration": 2.0, "speed": 5.0}
            )
        assert response.status_code == 400
        assert "Speed must be between 0.5x and 2.0x" in response.json()["detail"]
