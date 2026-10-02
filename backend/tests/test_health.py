from fastapi.testclient import TestClient
from backend.main import app, check_ffmpeg_tooling


def test_ffmpeg_tooling_check():
    assert check_ffmpeg_tooling() is True


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
