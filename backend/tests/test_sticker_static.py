import io
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app


def test_static_sticker_contain_success(sample_mp4: Path):
    """Test static sticker creation with contain mode: 512x512, <= 100KB, with alpha padding."""
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            response = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={"second": 0.5, "fit": "contain"}
            )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert "X-Sticker-Size" in response.headers
        assert "X-Sticker-Quality" in response.headers

        content = response.content
        assert len(content) <= 100_000

        # Open and inspect WebP image
        img = Image.open(io.BytesIO(content))
        assert img.format == "WEBP"
        assert img.size == (512, 512)

        # In contain mode with 320x240 video, top-left corner (0, 0) should be transparent padding
        rgba_img = img.convert("RGBA")
        r, g, b, a = rgba_img.getpixel((0, 0))
        assert a == 0, "Expected transparent padding at corner in contain mode"


def test_static_sticker_cover_success(sample_mp4: Path):
    """Test static sticker creation with cover mode: 512x512, <= 100KB, center cropped."""
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            response = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={"second": 0.0, "fit": "cover"}
            )
        assert response.status_code == 200
        content = response.content
        assert len(content) <= 100_000

        img = Image.open(io.BytesIO(content))
        assert img.size == (512, 512)


def test_static_sticker_out_of_range_timestamp(sample_mp4: Path):
    """Test that timestamp beyond duration returns 400."""
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            response = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={"second": 99.5, "fit": "contain"}
            )
        assert response.status_code == 400
        assert "outside valid range" in response.json()["detail"]


def test_static_sticker_negative_timestamp(sample_mp4: Path):
    """Test that negative timestamp returns 400."""
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            response = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={"second": -0.5, "fit": "contain"}
            )
        assert response.status_code == 400
        assert "outside valid range" in response.json()["detail"]
