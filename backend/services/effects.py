import logging
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("uvicorn")

# Known font paths by family
FONT_CANDIDATES = {
    "impact": [
        "C:\\Windows\\Fonts\\impact.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "arial": [
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "comic": [
        "C:\\Windows\\Fonts\\comic.ttf",
        "C:\\Windows\\Fonts\\comicbd.ttf",
    ],
}


def get_font(font_family: str = "impact", size: int = 36) -> ImageFont.FreeTypeFont:
    """Load a TrueType font for rendering, with fallbacks to system fonts or Pillow default."""
    family_key = (font_family or "impact").strip().lower()
    candidates = FONT_CANDIDATES.get(family_key, [])

    for path_str in candidates:
        if os.path.exists(path_str):
            try:
                return ImageFont.truetype(path_str, size=size)
            except Exception as e:
                logger.debug(f"Failed to load font from {path_str}: {e}")

    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def create_caption_overlay(
    text: Optional[str] = None,
    font_family: str = "impact",
    font_size: int = 38,
    text_color: str = "#ffffff",
    stroke_color: str = "#000000",
    stroke_width: int = 3,
    text_y: Optional[float] = None,  # normalized 0.0 - 1.0 (e.g. 0.88 for bottom)
    emoji: Optional[str] = None,
    emoji_y: Optional[float] = None,  # normalized 0.0 - 1.0
    canvas_size: int = 512
) -> Optional[Image.Image]:
    """
    Render a 512x512 transparent RGBA image containing the styled caption and optional emoji.
    Returns None if no text or emoji is specified.
    """
    clean_text = (text or "").strip()
    clean_emoji = (emoji or "").strip()

    if not clean_text and not clean_emoji:
        return None

    overlay = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Render Caption Text
    if clean_text:
        font = get_font(font_family, size=max(14, min(72, font_size)))
        y_pos = int(canvas_size * (text_y if text_y is not None else 0.88))
        x_center = canvas_size // 2

        # Basic multi-line word wrapping if text is long
        words = clean_text.split()
        lines = []
        cur_line = []

        for word in words:
            test_line = " ".join(cur_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font, stroke_width=stroke_width)
            w = bbox[2] - bbox[0]
            if w > (canvas_size - 40) and cur_line:
                lines.append(" ".join(cur_line))
                cur_line = [word]
            else:
                cur_line.append(word)
        if cur_line:
            lines.append(" ".join(cur_line))

        # Render lines stacked
        line_height = int(font_size * 1.25)
        total_text_h = len(lines) * line_height
        start_y = max(10, min(canvas_size - total_text_h - 10, y_pos - (total_text_h // 2)))

        for idx, line in enumerate(lines):
            line_y = start_y + (idx * line_height)
            draw.text(
                (x_center, line_y),
                line,
                font=font,
                fill=text_color,
                stroke_fill=stroke_color,
                stroke_width=stroke_width,
                anchor="mm"
            )

    # 2. Render Emoji Overlay
    if clean_emoji:
        emoji_font = get_font("arial", size=54)
        e_y = int(canvas_size * (emoji_y if emoji_y is not None else 0.15))
        draw.text(
            (canvas_size // 2, e_y),
            clean_emoji,
            font=emoji_font,
            anchor="mm"
        )

    return overlay


def apply_effects_to_static_image(
    image: Image.Image,
    overlay_img: Optional[Image.Image] = None,
    flip_h: bool = False
) -> Image.Image:
    """Apply horizontal flip and caption overlay to a static Pillow RGBA image."""
    res = image.convert("RGBA")
    if flip_h:
        res = res.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    if overlay_img is not None:
        res = Image.alpha_composite(res, overlay_img.convert("RGBA"))

    return res
