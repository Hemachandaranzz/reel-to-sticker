import asyncio
import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.ffmpeg import ffmpeg_slot


def test_request_id_and_logging_header():
    """Verify that every response has an X-Request-ID header."""
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers


def test_concurrency_semaphore_limit():
    """Verify that when all ffmpeg slots are held, extra requests return 429."""
    async def run_slot_test():
        # Hold all slots
        async with ffmpeg_slot(timeout=1.0):
            async with ffmpeg_slot(timeout=1.0):
                # Third acquisition should fail with 429
                with pytest.raises(Exception) as exc_info:
                    async with ffmpeg_slot(timeout=0.1):
                        pass
                assert "429" in str(exc_info.value) or "Server is busy" in str(exc_info.value)

    asyncio.run(run_slot_test())


def test_rate_limiting(sample_mp4: Path, monkeypatch):
    """Verify that rapid conversions trigger rate limit (429)."""
    # Create client with fresh limiter
    with TestClient(app) as client:
        responses = []
        for _ in range(15):
            with open(sample_mp4, "rb") as f:
                r = client.post(
                    "/api/sticker/static",
                    files={"file": ("sample.mp4", f, "video/mp4")},
                    data={"second": 0.0, "fit": "contain"}
                )
                responses.append(r.status_code)
                if r.status_code == 429:
                    break

        assert 429 in responses, f"Expected 429 in responses, got {responses}"
