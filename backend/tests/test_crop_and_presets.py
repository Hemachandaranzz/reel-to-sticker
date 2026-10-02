import io
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app


def test_static_sticker_custom_crop_success(sample_mp4: Path):
    """Verify custom square crop produces valid 512x512 sticker."""
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            response = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={
                    "second": 0.0,
                    "crop_x": 0.1,
                    "crop_y": 0.1,
                    "crop_size": 0.7,
                }
            )
        assert response.status_code == 200
        img = Image.open(io.BytesIO(response.content))
        assert img.size == (512, 512)
        assert len(response.content) <= 100_000


def test_static_sticker_invalid_crop_bounds(sample_mp4: Path):
    """Verify crop extending beyond bounds returns 400."""
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            response = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={
                    "second": 0.0,
                    "crop_x": 0.8,
                    "crop_y": 0.8,
                    "crop_size": 0.6,  # 0.8 + 0.6 = 1.4 > 1.0
                }
            )
        assert response.status_code == 400
        assert "Crop rectangle extends beyond" in response.json()["detail"] or "must be between" in response.json()["detail"]


def test_static_sticker_presets_predictable_sizes(sample_mp4: Path):
    """Verify that Smallest preset yields smaller or equal file size compared to Best preset."""
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            resp_small = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={"second": 0.0, "preset": "smallest"}
            )
        with open(sample_mp4, "rb") as f:
            resp_best = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={"second": 0.0, "preset": "best"}
            )

        assert resp_small.status_code == 200
        assert resp_best.status_code == 200

        size_small = len(resp_small.content)
        size_best = len(resp_best.content)
        assert size_small <= size_best, f"Smallest preset ({size_small}B) should be <= Best preset ({size_best}B)"


def test_animated_sticker_custom_crop(generate_clip):
    """Verify custom crop on animated stickers."""
    video_path = generate_clip(3)
    with TestClient(app) as client:
        with open(video_path, "rb") as f:
            response = client.post(
                "/api/sticker/animated",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={
                    "start": 0.0,
                    "duration": 2.0,
                    "crop_x": 0.05,
                    "crop_y": 0.05,
                    "crop_size": 0.8,
                    "preset": "balanced",
                }
            )
        assert response.status_code == 200
        img = Image.open(io.BytesIO(response.content))
        assert img.size == (512, 512)
        assert len(response.content) <= 500_000
