import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
from PIL import Image

try:
    from config import ANIMATED_MAX_BYTES, STATIC_MAX_BYTES
    from services.ffmpeg import probe_video_file, run_ffmpeg
except ImportError:
    from backend.config import ANIMATED_MAX_BYTES, STATIC_MAX_BYTES
    from backend.services.ffmpeg import probe_video_file, run_ffmpeg

logger = logging.getLogger("uvicorn")


def optimize_static_webp(
    image: Image.Image,
    max_bytes: int = STATIC_MAX_BYTES,
    preset: str = "balanced"
) -> Tuple[bytes, int]:
    """
    Encode Pillow RGBA image to WebP under max_bytes (100 KB for static WhatsApp stickers).
    Preset adjusts initial target quality:
      'smallest': 60 -> 20
      'balanced': 80 -> 25
      'best':     90 -> 30
    """
    if image.size != (512, 512):
        raise ValueError(f"Expected 512x512 image, got {image.size}")

    img_to_encode = image.convert("RGBA")

    preset_name = (preset or "balanced").lower()
    if preset_name == "smallest":
        qualities = [60, 50, 40, 35, 30]
    elif preset_name == "best":
        qualities = [90, 85, 80, 75, 70, 60, 50, 40, 30]
    else:  # balanced
        qualities = [80, 75, 70, 60, 50, 40, 30]

    for q in qualities:
        buf = io.BytesIO()
        img_to_encode.save(buf, format="WEBP", quality=q, method=6)
        data = buf.getvalue()
        if len(data) <= max_bytes:
            return data, q


    # Ladder 2: Quality 30 with color reduction / quantization if image is very complex
    logger.info("Static sticker still over 100KB at quality 30; trying palette reduction...")
    quantized = img_to_encode.quantize(colors=256, method=Image.Quantize.MEDIANCUT).convert("RGBA")
    for q in [35, 30, 25, 20]:
        buf = io.BytesIO()
        quantized.save(buf, format="WEBP", quality=q, method=6)
        data = buf.getvalue()
        if len(data) <= max_bytes:
            return data, q

    # Ladder 3: Resize content slightly to 480x480 on 512x512 canvas
    logger.info("Trying slight content scale down on 512 canvas...")
    scaled_content = img_to_encode.resize((480, 480), Image.Resampling.LANCZOS)
    padded_canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    padded_canvas.paste(scaled_content, (16, 16), scaled_content)

    for q in [30, 25, 20, 15]:
        buf = io.BytesIO()
        padded_canvas.save(buf, format="WEBP", quality=q, method=6)
        data = buf.getvalue()
        if len(data) <= max_bytes:
            return data, q

    return data, 15


def build_filter_complex(
    fps: int,
    fit: str = "contain",
    content_size: int = 512,
    speed: float = 1.0,
    crop_rect: Optional[Tuple[int, int, int, int]] = None,
    flip_h: bool = False,
    reverse: bool = False,
    boomerang: bool = False,
    has_overlay: bool = False
) -> str:
    """Build FFmpeg video filter chain for sticker generation with effects and overlay."""
    fit_mode = (fit or "contain").strip().lower()
    filters = []

    # Speed adjustment
    if abs(speed - 1.0) > 0.01:
        pts_factor = round(1.0 / speed, 4)
        filters.append(f"setpts={pts_factor}*PTS")

    # Horizontal flip
    if flip_h:
        filters.append("hflip")

    # Custom 1:1 Crop or standard framing
    if crop_rect is not None:
        cx, cy, cw, ch = crop_rect
        filters.append(f"crop={cw}:{ch}:{cx}:{cy}")
        filters.append(f"scale={content_size}:{content_size}")
        if content_size < 512:
            filters.append("pad=512:512:(512-iw)/2:(512-ih)/2:color=black@0.0")
    elif fit_mode == "cover":
        if content_size == 512:
            filters.append("scale=512:512:force_original_aspect_ratio=increase,crop=512:512:(iw-512)/2:(ih-512)/2")
        else:
            filters.append(
                f"scale={content_size}:{content_size}:force_original_aspect_ratio=increase,"
                f"crop={content_size}:{content_size}:(iw-{content_size})/2:(ih-{content_size})/2,"
                f"pad=512:512:(512-iw)/2:(512-ih)/2:color=black@0.0"
            )
    else:  # contain
        filters.append(
            f"scale={content_size}:{content_size}:force_original_aspect_ratio=decrease,"
            f"pad=512:512:(512-iw)/2:(512-ih)/2:color=black@0.0"
        )

    # Reverse or Boomerang
    if boomerang:
        base_chain = ",".join(filters)
        if base_chain:
            prefix = f"[0:v]{base_chain},"
        else:
            prefix = "[0:v]"
        boom_chain = f"{prefix}split[f][b];[b]reverse[r];[f][r]concat=n=2:v=1:a=0"
        if has_overlay:
            return f"{boom_chain}[vboom];[vboom][1:v]overlay=0:0:format=auto,fps={fps},format=yuva420p[out]"
        else:
            return f"{boom_chain},fps={fps},format=yuva420p[out]"
    elif reverse:
        filters.append("reverse")

    filters.append(f"fps={fps}")
    filters.append("format=yuva420p")
    base_chain = ",".join(filters)

    if has_overlay:
        return f"[0:v]{base_chain}[base];[base][1:v]overlay=0:0:format=auto[out]"

    return base_chain



def validate_animated_webp(webp_path: Path, max_bytes: int = ANIMATED_MAX_BYTES) -> Dict[str, Any]:
    """
    Validate output animated WebP:
    - Dimensions 512x512
    - Frame count > 1
    - Duration <= 10s
    - Loop = 0 (infinite)
    - File size <= max_bytes (500 KB)
    """
    file_size = webp_path.stat().st_size
    if file_size > max_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"Generated animated sticker exceeds WhatsApp limit: {file_size} bytes > {max_bytes} bytes. Try a shorter clip."
        )

    with Image.open(webp_path) as im:
        if im.format != "WEBP":
            raise HTTPException(status_code=422, detail="Generated file is not valid WebP.")
        if im.size != (512, 512):
            raise HTTPException(
                status_code=422,
                detail=f"Sticker canvas is {im.size[0]}x{im.size[1]}, expected 512x512."
            )
        is_anim = getattr(im, "is_animated", False)
        n_frames = getattr(im, "n_frames", 1)
        if not is_anim or n_frames <= 1:
            raise HTTPException(
                status_code=422,
                detail="Generated sticker is not animated or has only 1 frame."
            )
        loop = im.info.get("loop", 0)
        if loop != 0:
            raise HTTPException(
                status_code=422,
                detail=f"Generated sticker loop count ({loop}) is not infinite."
            )

    # Duration probe with ffprobe
    meta = probe_video_file(webp_path)
    dur = None
    if "streams" in meta and meta["streams"]:
        dur = meta["streams"][0].get("duration")
    if not dur and "format" in meta:
        dur = meta["format"].get("duration")

    duration_val = float(dur) if dur else 0.0
    if duration_val > 10.5:
        raise HTTPException(
            status_code=422,
            detail=f"Animated sticker duration ({duration_val:.2f}s) exceeds WhatsApp 10 second limit."
        )

    return {
        "width": 512,
        "height": 512,
        "frames": n_frames,
        "duration": round(duration_val, 2) if duration_val > 0 else None,
        "bytes": file_size,
    }


def optimize_animated_webp(
    input_path: Path,
    output_path: Path,
    start: float,
    duration: float,
    fit: str = "contain",
    speed: float = 1.0,
    crop_rect: Optional[Tuple[int, int, int, int]] = None,
    preset: str = "balanced",
    flip_h: bool = False,
    reverse: bool = False,
    boomerang: bool = False,
    overlay_png_path: Optional[Path] = None,
    max_bytes: int = ANIMATED_MAX_BYTES
) -> Dict[str, Any]:
    """
    Retry ladder until animated WebP <= max_bytes (500 KB):
    Adjusts starting quality and fps based on preset ('smallest', 'balanced', 'best').
    """
    preset_name = (preset or "balanced").lower()
    if preset_name == "smallest":
        ladder_steps = [
            (10, 45, 4, 512, 1.0),
            (8,  40, 4, 512, 1.0),
            (8,  35, 6, 512, 1.0),
            (8,  30, 6, 480, 1.0),
            (8,  25, 6, 448, 1.0),
            (8,  20, 6, 448, 0.8),
            (6,  18, 6, 400, 0.5),
        ]
    elif preset_name == "best":
        ladder_steps = [
            (15, 80, 4, 512, 1.0),
            (15, 70, 4, 512, 1.0),
            (12, 60, 4, 512, 1.0),
            (10, 50, 4, 512, 1.0),
            (8,  45, 4, 512, 1.0),
            (8,  35, 6, 512, 1.0),
            (8,  30, 6, 448, 1.0),
            (8,  25, 6, 448, 0.8),
        ]
    else:  # balanced
        ladder_steps = [
            (12, 65, 4, 512, 1.0),
            (12, 60, 4, 512, 1.0),
            (10, 50, 4, 512, 1.0),
            (8,  45, 4, 512, 1.0),
            (8,  35, 6, 512, 1.0),
            (8,  35, 6, 480, 1.0),
            (8,  30, 6, 448, 1.0),
            (8,  30, 6, 448, 0.8),
            (8,  25, 6, 448, 0.64),
            (8,  20, 6, 448, 0.5),
            (6,  18, 6, 400, 0.4),
        ]

    last_size = 0
    has_overlay = overlay_png_path is not None and Path(overlay_png_path).exists()
    use_complex = boomerang or has_overlay

    for idx, (fps, q, comp, content_size, dur_factor) in enumerate(ladder_steps):
        current_dur = max(1.0, duration * dur_factor)
        filter_str = build_filter_complex(
            fps=fps,
            fit=fit,
            content_size=content_size,
            speed=speed,
            crop_rect=crop_rect,
            flip_h=flip_h,
            reverse=reverse,
            boomerang=boomerang,
            has_overlay=has_overlay
        )

        cmd = [
            "-ss", f"{start:.3f}",
            "-t", f"{current_dur:.3f}",
            "-i", str(input_path),
        ]
        if has_overlay:
            cmd.extend(["-i", str(overlay_png_path)])

        if use_complex:
            cmd.extend(["-filter_complex", filter_str, "-map", "[out]"])
        else:
            cmd.extend(["-vf", filter_str])

        cmd.extend([
            "-vcodec", "libwebp",
            "-loop", "0",
            "-an",
            "-q:v", str(q),
            "-compression_level", str(comp),
            "-y",
            str(output_path)
        ])

        logger.info(
            f"Optimizer step {idx+1}/{len(ladder_steps)}: fps={fps}, q={q}, "
            f"size={content_size}, dur={current_dur:.2f}s"
        )

        try:
            run_ffmpeg(cmd)
        except Exception as e:
            logger.warning(f"FFmpeg attempt {idx+1} failed: {e}")
            continue

        if not output_path.exists():
            continue

        file_size = output_path.stat().st_size
        last_size = file_size

        if file_size <= max_bytes:
            logger.info(f"Optimizer succeeded on step {idx+1}: {file_size} bytes (<= {max_bytes})")
            validation = validate_animated_webp(output_path, max_bytes=max_bytes)
            return {
                "fps": fps,
                "quality": q,
                "duration": round(current_dur, 2),
                "bytes": file_size,
                "content_size": content_size,
                "frames": validation.get("frames", 0)
            }

    # If ladder exhausted without reaching max_bytes
    output_path.unlink(missing_ok=True)
    raise HTTPException(
        status_code=422,
        detail=f"Unable to compress animated sticker below 500 KB limit (last achieved {last_size // 1024} KB). Try a shorter clip or reduce speed."
    )
