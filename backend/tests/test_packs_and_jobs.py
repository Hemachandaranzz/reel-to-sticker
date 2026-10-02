import io
import json
import zipfile
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.packs import create_tray_icon, validate_pack_sticker, build_sticker_pack_archive
from backend.services.jobs import job_store

client = TestClient(app)


def _create_dummy_webp(size=(512, 512), color="red") -> bytes:
    img = Image.new("RGBA", size, color)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=80)
    return buf.getvalue()


def test_create_tray_icon():
    dummy = _create_dummy_webp()
    tray_png = create_tray_icon(dummy)
    assert len(tray_png) <= 50 * 1024

    with Image.open(io.BytesIO(tray_png)) as im:
        assert im.format == "PNG"
        assert im.size == (96, 96)


def test_pack_validation_rules():
    valid_bytes = _create_dummy_webp()
    # 1. Valid sticker
    meta = validate_pack_sticker(valid_bytes, index=1)
    assert meta["is_animated"] is False

    # 2. Invalid dimensions
    wrong_dim = _create_dummy_webp(size=(300, 300))
    with pytest.raises(Exception):
        validate_pack_sticker(wrong_dim, index=2)

    # 3. Invalid format (PNG instead of WebP)
    png_img = Image.new("RGBA", (512, 512), "blue")
    buf = io.BytesIO()
    png_img.save(buf, format="PNG")
    with pytest.raises(Exception):
        validate_pack_sticker(buf.getvalue(), index=3)


def test_build_sticker_pack_archive():
    s1 = _create_dummy_webp(color="red")
    s2 = _create_dummy_webp(color="green")
    s3 = _create_dummy_webp(color="blue")

    # Less than 3 stickers should fail
    with pytest.raises(Exception):
        build_sticker_pack_archive("Pack", "Author", [(s1, ["🔥"]), (s2, ["😂"])])

    # 3 stickers should succeed
    zip_bytes = build_sticker_pack_archive(
        "Awesome Pack",
        "Test Author",
        [(s1, ["🔥"]), (s2, ["😂", "❤️"]), (s3, ["🚀"])]
    )
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "tray.png" in namelist
        assert "pack.json" in namelist
        assert "01.webp" in namelist
        assert "02.webp" in namelist
        assert "03.webp" in namelist

        pack_json = json.loads(zf.read("pack.json").decode("utf-8"))
        assert pack_json["name"] == "Awesome Pack"
        assert pack_json["publisher"] == "Test Author"
        assert len(pack_json["stickers"]) == 3
        assert pack_json["stickers"][0]["emojis"] == ["🔥"]


def test_pack_export_endpoint():
    s1 = _create_dummy_webp(color="red")
    s2 = _create_dummy_webp(color="green")
    s3 = _create_dummy_webp(color="blue")

    meta_json = json.dumps([
        {"emojis": ["🔥"]},
        {"emojis": ["🎉"]},
        {"emojis": ["😎"]}
    ])

    files = [
        ("stickers", ("s1.webp", s1, "image/webp")),
        ("stickers", ("s2.webp", s2, "image/webp")),
        ("stickers", ("s3.webp", s3, "image/webp")),
    ]

    data = {
        "name": "My Cool Pack",
        "publisher": "Creator",
        "stickers_meta": meta_json,
    }

    resp = client.post("/api/packs/export", data=data, files=files)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert resp.headers["X-Pack-Count"] == "3"


def test_jobs_lifecycle():
    # 404 for non-existent job
    resp = client.get("/api/jobs/non-existent-uuid")
    assert resp.status_code == 404

    # Create job in store
    job = job_store.create_job()
    assert job.status == "queued"

    # Query status
    resp = client.get(f"/api/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"

    # Cancel job
    cancel_resp = client.post(f"/api/jobs/{job.id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "canceled"

    # Query updated status
    resp = client.get(f"/api/jobs/{job.id}")
    assert resp.json()["status"] == "canceled"
