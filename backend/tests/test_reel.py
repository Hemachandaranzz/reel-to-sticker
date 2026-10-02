import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.providers.base import get_media_provider, NotConfiguredProvider, UploadProvider
from fastapi import HTTPException

client = TestClient(app)


def test_valid_reel_urls():
    valid_cases = [
        ("https://www.instagram.com/reel/C_8xYzaB123/", "C_8xYzaB123"),
        ("https://instagram.com/reel/D_9012/?utm_source=ig_web_copy_link", "D_9012"),
        ("https://www.instagram.com/reels/E_3456", "E_3456"),
        ("https://instagram.com/p/F_7890/", "F_7890"),
    ]

    for url, expected_code in valid_cases:
        resp = client.post("/api/reel/check", json={"url": url})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["shortcode"] == expected_code
        assert data["clean_url"] == f"https://www.instagram.com/reel/{expected_code}/"
        assert len(data["guidance"]) >= 3


def test_invalid_and_ssrf_reel_urls():
    invalid_cases = [
        "http://www.instagram.com/reel/test/",           # HTTP not HTTPS
        "https://evil.com/reel/test/",                   # Bad host
        "https://instagram.com.evil.com/reel/test/",     # Lookalike domain
        "https://127.0.0.1/reel/test/",                  # Localhost IP
        "https://instagram.com:8080/reel/test/",         # Port specification
        "https://user:pass@instagram.com/reel/test/",    # Auth in URL
        "https://www.instagram.com/explore/",            # Invalid non-reel path
        "not a url",                                     # Malformed
        "",                                              # Empty
    ]

    for bad_url in invalid_cases:
        resp = client.post("/api/reel/check", json={"url": bad_url})
        assert resp.status_code == 400


@pytest.mark.anyio
async def test_media_providers(tmp_path):
    upload_prov = get_media_provider("upload")
    assert isinstance(upload_prov, UploadProvider)

    not_conf_prov = get_media_provider("meta")
    assert isinstance(not_conf_prov, NotConfiguredProvider)

    with pytest.raises(HTTPException) as exc_info:
        await not_conf_prov.fetch("https://www.instagram.com/reel/123/", tmp_path / "dummy.mp4")
    assert exc_info.value.status_code == 501
    assert "Direct reel fetching" in exc_info.value.detail


def test_download_reel_endpoint_invalid_url():
    resp = client.post("/api/reel/download", json={"url": "not-a-valid-url"})
    assert resp.status_code in (400, 422)


def test_download_reel_endpoint_mock(monkeypatch, sample_mp4):
    from backend.routers import reel

    def mock_download(url, output_dir):
        return sample_mp4, {"duration": 2.0, "width": 512, "height": 512, "fps": 25.0}

    monkeypatch.setattr(reel, "download_video_from_url", mock_download)

    resp = client.post("/api/reel/download", json={"url": "https://www.instagram.com/reel/valid123/"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "video/mp4"
    assert resp.headers["X-Video-Duration"] == "2.0"
    assert len(resp.content) > 0
