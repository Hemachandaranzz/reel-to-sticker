import io
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from PIL import Image

try:
    from backend.config import RATE_LIMIT_PER_MINUTE, STATIC_MAX_BYTES, ANIMATED_MAX_BYTES
    from backend.services.cutout import is_cutout_available, remove_background_static, apply_sticker_outline
    from backend.services.effects import create_caption_overlay, apply_effects_to_static_image
    from backend.services.ffmpeg import run_ffmpeg, ffmpeg_slot
    from backend.services.limiter import limiter
    from backend.services.optimizer import optimize_static_webp, optimize_animated_webp
    from backend.services.validate import save_upload_to_temp, validate_video
except ImportError:
    from config import RATE_LIMIT_PER_MINUTE, STATIC_MAX_BYTES, ANIMATED_MAX_BYTES
    from services.cutout import is_cutout_available, remove_background_static, apply_sticker_outline
    from services.effects import create_caption_overlay, apply_effects_to_static_image
    from services.ffmpeg import run_ffmpeg, ffmpeg_slot
    from services.limiter import limiter
    from services.optimizer import optimize_static_webp, optimize_animated_webp
    from services.validate import save_upload_to_temp, validate_video


logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/sticker", tags=["sticker"])


def extract_frame_as_image(video_path: Path | str, second: float) -> Image.Image:
    """Extract a single frame from video at given timestamp as a Pillow RGBA Image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        tmp_img_path = Path(tmp_img.name)

    try:
        run_ffmpeg([
            "-ss", f"{second:.4f}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-f", "image2",
            "-c:v", "png",
            "-y",
            str(tmp_img_path)
        ])
        with Image.open(tmp_img_path) as img:
            return img.convert("RGBA")
    finally:
        tmp_img_path.unlink(missing_ok=True)


def validate_and_compute_crop(
    width: int,
    height: int,
    crop_x: Optional[float],
    crop_y: Optional[float],
    crop_size: Optional[float]
) -> Optional[Tuple[int, int, int, int]]:
    """Validate normalized crop coordinates (0-1) and return (x, y, crop_w, crop_h) in pixel units."""
    if crop_size is None or crop_x is None or crop_y is None:
        return None

    if crop_size <= 0.0 or crop_size > 1.001:
        raise HTTPException(status_code=400, detail="crop_size must be between 0 and 1.")
    if crop_x < -0.001 or crop_x > 1.001 or crop_y < -0.001 or crop_y > 1.001:
        raise HTTPException(status_code=400, detail="crop_x and crop_y must be between 0 and 1.")

    dim = min(width, height)
    actual_crop_size = max(16, int(round(crop_size * dim)))
    actual_x = int(round(crop_x * width))
    actual_y = int(round(crop_y * height))

    if actual_x + actual_crop_size > width + 2 or actual_y + actual_crop_size > height + 2:
        raise HTTPException(status_code=400, detail="Crop rectangle extends beyond video boundaries.")

    actual_x = max(0, min(width - actual_crop_size, actual_x))
    actual_y = max(0, min(height - actual_crop_size, actual_y))

    return (actual_x, actual_y, actual_crop_size, actual_crop_size)


def fit_image_to_512(img: Image.Image, fit: str = "contain") -> Image.Image:
    """Scale and fit image into a 512x512 canvas.
    'contain' maintains aspect ratio and pads transparently.
    'cover' scales to cover 512x512 and center-crops.
    """
    mode = (fit or "contain").strip().lower()
    w, h = img.size

    if mode == "cover":
        ratio = max(512 / w, 512 / h)
        new_w, new_h = max(512, int(round(w * ratio))), max(512, int(round(h * ratio)))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - 512) // 2
        top = (new_h - 512) // 2
        return resized.crop((left, top, left + 512, top + 512))
    else:  # contain (default)
        ratio = min(512 / w, 512 / h)
        new_w, new_h = max(1, int(round(w * ratio))), max(1, int(round(h * ratio)))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        offset = ((512 - new_w) // 2, (512 - new_h) // 2)
        canvas.paste(resized, offset, resized)
        return canvas


@router.get("/capabilities")
async def get_sticker_capabilities():
    """Return system capabilities including background cutout availability and size limits."""
    return {
        "cutout_available": is_cutout_available(),
        "outline_available": True,
        "effects_available": True,
        "max_static_bytes": STATIC_MAX_BYTES,
        "max_animated_bytes": ANIMATED_MAX_BYTES,
    }


@router.post("/static")
@limiter.limit(RATE_LIMIT_PER_MINUTE)
async def create_static_sticker(
    request: Request,
    file: UploadFile = File(...),
    second: float = Form(0.0),
    fit: str = Form("contain"),
    crop_x: Optional[float] = Form(None),
    crop_y: Optional[float] = Form(None),
    crop_size: Optional[float] = Form(None),
    preset: str = Form("balanced"),
    remove_bg: bool = Form(False),
    outline_px: int = Form(0),
    feather: int = Form(0),
    flip_h: bool = Form(False),
    text: Optional[str] = Form(None),
    font_family: str = Form("impact"),
    font_size: int = Form(38),
    text_color: str = Form("#ffffff"),
    stroke_color: str = Form("#000000"),
    stroke_width: int = Form(3),
    text_y: Optional[float] = Form(None),
    emoji: Optional[str] = Form(None),
    emoji_y: Optional[float] = Form(None)
):
    """
    Generate a WhatsApp-ready static WebP sticker (512x512, <= 100 KB).
    Supports custom 1:1 square crop, transparent cutout, sticker outline, text caption, and emoji.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        ext = Path(file.filename or "video.mp4").suffix or ".mp4"
        temp_video_path = Path(tmp_dir) / f"upload{ext}"

        await save_upload_to_temp(file, temp_video_path)
        meta = validate_video(temp_video_path)

        duration = meta["duration"]
        if second < 0.0 or second > duration:
            raise HTTPException(
                status_code=400,
                detail=f"Timestamp {second:.2f}s is outside valid range [0.0, {duration:.2f}s]."
            )

        crop_rect = validate_and_compute_crop(
            meta["width"], meta["height"], crop_x, crop_y, crop_size
        )

        async with ffmpeg_slot():
            # Extract the selected frame
            raw_frame = extract_frame_as_image(temp_video_path, second)

            if crop_rect is not None:
                cx, cy, cw, ch = crop_rect
                cropped = raw_frame.crop((cx, cy, cx + cw, cy + ch))
                canvas_512 = cropped.resize((512, 512), Image.Resampling.LANCZOS)
            else:
                canvas_512 = fit_image_to_512(raw_frame, fit=fit)

            if remove_bg:
                canvas_512 = remove_background_static(
                    canvas_512, outline_px=outline_px, feather=feather
                )
            elif outline_px > 0 or feather > 0:
                canvas_512 = apply_sticker_outline(
                    canvas_512, outline_px=outline_px, feather=feather
                )

            # Apply caption, emoji, and flip effects
            overlay = create_caption_overlay(
                text=text,
                font_family=font_family,
                font_size=font_size,
                text_color=text_color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                text_y=text_y,
                emoji=emoji,
                emoji_y=emoji_y,
                canvas_size=512
            )
            canvas_512 = apply_effects_to_static_image(
                canvas_512, overlay_img=overlay, flip_h=flip_h
            )

            # Optimize size under 100 KB
            webp_bytes, final_quality = optimize_static_webp(canvas_512, preset=preset)

        return Response(
            content=webp_bytes,
            media_type="image/webp",
            headers={
                "Content-Disposition": 'attachment; filename="sticker.webp"',
                "X-Sticker-Size": str(len(webp_bytes)),
                "X-Sticker-Quality": str(final_quality),
            }
        )


@router.post("/animated")
@limiter.limit(RATE_LIMIT_PER_MINUTE)
async def create_animated_sticker(
    request: Request,
    file: UploadFile = File(...),
    start: float = Form(0.0),
    duration: float = Form(3.0),
    fit: str = Form("contain"),
    speed: float = Form(1.0),
    crop_x: Optional[float] = Form(None),
    crop_y: Optional[float] = Form(None),
    crop_size: Optional[float] = Form(None),
    preset: str = Form("balanced"),
    flip_h: bool = Form(False),
    reverse: bool = Form(False),
    boomerang: bool = Form(False),
    text: Optional[str] = Form(None),
    font_family: str = Form("impact"),
    font_size: int = Form(38),
    text_color: str = Form("#ffffff"),
    stroke_color: str = Form("#000000"),
    stroke_width: int = Form(3),
    text_y: Optional[float] = Form(None),
    emoji: Optional[str] = Form(None),
    emoji_y: Optional[float] = Form(None)
):
    """
    Generate a WhatsApp-ready animated WebP sticker (512x512, <= 500 KB, <= 10s, looping).
    Supports custom 1:1 square crop, effects (speed, flip, reverse, boomerang), text and emoji overlays.
    """
    if speed < 0.5 or speed > 2.0:
        raise HTTPException(status_code=400, detail="Speed must be between 0.5x and 2.0x.")

    if duration <= 0.0:
        raise HTTPException(status_code=400, detail="Duration must be greater than 0.")

    if boomerang and duration > 5.0:
        duration = 5.0
    elif duration > 10.0:
        raise HTTPException(status_code=400, detail="Duration cannot exceed 10 seconds.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        ext = Path(file.filename or "video.mp4").suffix or ".mp4"
        temp_video_path = Path(tmp_dir) / f"upload{ext}"
        out_webp_path = Path(tmp_dir) / "sticker_animated.webp"

        await save_upload_to_temp(file, temp_video_path)
        meta = validate_video(temp_video_path)

        total_dur = meta["duration"]
        if start < 0.0 or start >= total_dur:
            raise HTTPException(
                status_code=400,
                detail=f"Start timestamp {start:.2f}s is outside video duration [0.0, {total_dur:.2f}s]."
            )

        if start + duration > total_dur:
            duration = max(0.5, total_dur - start)

        crop_rect = validate_and_compute_crop(
            meta["width"], meta["height"], crop_x, crop_y, crop_size
        )

        # Generate overlay PNG if text or emoji is present
        overlay_img = create_caption_overlay(
            text=text,
            font_family=font_family,
            font_size=font_size,
            text_color=text_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            text_y=text_y,
            emoji=emoji,
            emoji_y=emoji_y,
            canvas_size=512
        )
        overlay_path = None
        if overlay_img is not None:
            overlay_path = Path(tmp_dir) / "overlay.png"
            overlay_img.save(overlay_path, format="PNG")

        async with ffmpeg_slot():
            stats = optimize_animated_webp(
                input_path=temp_video_path,
                output_path=out_webp_path,
                start=start,
                duration=duration,
                fit=fit,
                speed=speed,
                crop_rect=crop_rect,
                preset=preset,
                flip_h=flip_h,
                reverse=reverse,
                boomerang=boomerang,
                overlay_png_path=overlay_path
            )

        with open(out_webp_path, "rb") as f:
            webp_bytes = f.read()

        return Response(
            content=webp_bytes,
            media_type="image/webp",
            headers={
                "Content-Disposition": 'attachment; filename="animated_sticker.webp"',
                "X-Sticker-Size": str(stats["bytes"]),
                "X-Sticker-Fps": str(stats["fps"]),
                "X-Sticker-Quality": str(stats["quality"]),
                "X-Sticker-Duration": str(stats["duration"]),
                "X-Sticker-Frames": str(stats["frames"]),
            }
        )
