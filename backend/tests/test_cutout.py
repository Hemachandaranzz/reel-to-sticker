import io
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.cutout import apply_sticker_outline, is_cutout_available, remove_background_static


def test_apply_sticker_outline_logic():
    """Verify that apply_sticker_outline generates a dilated white border around non-transparent pixels."""
    # Create a 100x100 transparent image with a 20x20 red square in the center
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for x in range(40, 60):
        for y in range(40, 60):
            img.putpixel((x, y), (255, 0, 0, 255))

    # Apply 4px white outline
    outlined = apply_sticker_outline(img, outline_px=4, feather=0)
    assert outlined.size == (100, 100)

    # Pixel at (38, 50) is 2px away from red square, should now be white with full alpha
    r, g, b, a = outlined.getpixel((38, 50))
    assert (r, g, b) == (255, 255, 255)
    assert a == 255

    # Center pixel at (50, 50) should remain red
    cr, cg, cb, ca = outlined.getpixel((50, 50))
    assert (cr, cg, cb) == (255, 0, 0)
    assert ca == 255

    # Far pixel at (10, 10) should remain completely transparent
    fr, fg, fb, fa = outlined.getpixel((10, 10))
    assert fa == 0


def test_static_sticker_with_outline(sample_mp4: Path):
    """Test generating a static sticker with sticker outline."""
    with TestClient(app) as client:
        with open(sample_mp4, "rb") as f:
            response = client.post(
                "/api/sticker/static",
                files={"file": ("sample.mp4", f, "video/mp4")},
                data={
                    "second": 0.0,
                    "outline_px": 4,
                    "fit": "contain"
                }
            )
        assert response.status_code == 200
        assert len(response.content) <= 100_000
        img = Image.open(io.BytesIO(response.content))
        assert img.size == (512, 512)
