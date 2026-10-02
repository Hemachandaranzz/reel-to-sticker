import io
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app



def test_probe_valid_mp4(sample_mp4: Path):
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            response = client.post(
                "/api/probe",
                files={"file": ("test.mp4", f, "video/mp4")}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["width"] == 320
        assert data["height"] == 240
        assert data["duration"] >= 0.9
        assert data["fps"] == 30.0


def test_probe_fake_mp4_rejected():
    """A text file renamed to .mp4 should be rejected with 422 by ffprobe validation."""
    with TestClient(app) as client:
        fake_content = io.BytesIO(b"This is not a real video file content.")
        response = client.post(
            "/api/probe",
            files={"file": ("fake_video.mp4", fake_content, "video/mp4")}
        )
        assert response.status_code == 422
        assert "detail" in response.json()


def test_probe_disallowed_extension():
    """Files with disallowed extensions (.txt, .exe) should return 400."""
    with TestClient(app) as client:
        content = io.BytesIO(b"hello")
        response = client.post(
            "/api/probe",
            files={"file": ("notes.txt", content, "text/plain")}
        )
        assert response.status_code == 400
        assert "detail" in response.json()
        assert "Unsupported file extension" in response.json()["detail"]


def test_probe_oversized_file(monkeypatch):
    """File exceeding MAX_UPLOAD_MB should return 413."""
    import backend.config as cfg
    monkeypatch.setattr(cfg, "MAX_UPLOAD_MB", 1)


    with TestClient(app) as client:
        oversized = io.BytesIO(b"0" * (1024 * 1024 + 1024))  # > 1 MB
        response = client.post(
            "/api/probe",
            files={"file": ("oversized.mp4", oversized, "video/mp4")}
        )
        assert response.status_code == 413
        assert "detail" in response.json()
        assert "exceeds maximum allowed size" in response.json()["detail"]
