import io
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.effects import create_caption_overlay, apply_effects_to_static_image

client = TestClient(app)


try:
    from backend.config import STATIC_MAX_BYTES, ANIMATED_MAX_BYTES
except ImportError:
    from config import STATIC_MAX_BYTES, ANIMATED_MAX_BYTES


def test_capabilities_endpoint():
    resp = client.get("/api/sticker/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "cutout_available" in data
    assert data["outline_available"] is True
    assert data["effects_available"] is True
    assert data["max_static_bytes"] == STATIC_MAX_BYTES
    assert data["max_animated_bytes"] == ANIMATED_MAX_BYTES


def test_create_caption_overlay():
    overlay = create_caption_overlay(
        text="TEST STICKER",
        font_family="impact",
        font_size=40,
        text_color="#ffff00",
        stroke_color="#000000",
        stroke_width=3,
        text_y=0.85,
        emoji="🎉",
        emoji_y=0.15,
        canvas_size=512
    )
    assert overlay is not None
    assert overlay.size == (512, 512)
    assert overlay.mode == "RGBA"
    # Ensure there are non-transparent pixels
    bbox = overlay.getbbox()
    assert bbox is not None


def test_static_sticker_with_effects(sample_mp4):
    with open(sample_mp4, "rb") as f:
        resp = client.post(
            "/api/sticker/static",
            files={"file": ("clip.mp4", f, "video/mp4")},
            data={
                "second": 0.5,
                "fit": "contain",
                "flip_h": "true",
                "text": "WOW",
                "font_family": "arial",
                "font_size": "42",
                "text_color": "#ffffff",
                "stroke_color": "#000000",
                "stroke_width": "3",
                "text_y": "0.80",
                "emoji": "🎉"
            }
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"
    size = int(resp.headers.get("X-Sticker-Size", 0))
    assert 0 < size <= STATIC_MAX_BYTES

    with Image.open(io.BytesIO(resp.content)) as im:
        assert im.format == "WEBP"
        assert im.size == (512, 512)


def test_animated_sticker_with_boomerang_and_effects(sample_mp4):
    with open(sample_mp4, "rb") as f:
        resp = client.post(
            "/api/sticker/animated",
            files={"file": ("clip.mp4", f, "video/mp4")},
            data={
                "start": 0.0,
                "duration": 1.0,
                "fit": "contain",
                "speed": 1.0,
                "boomerang": "true",
                "flip_h": "true",
                "text": "BOOM",
                "font_family": "impact",
                "font_size": "36"
            }
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"
    size = int(resp.headers.get("X-Sticker-Size", 0))
    assert 0 < size <= ANIMATED_MAX_BYTES

    with Image.open(io.BytesIO(resp.content)) as im:
        assert im.format == "WEBP"
        assert im.size == (512, 512)
        assert getattr(im, "is_animated", False)
        assert im.n_frames > 2
