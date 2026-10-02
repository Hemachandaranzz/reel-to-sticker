import io
import json
import logging
import uuid
import zipfile
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
from PIL import Image

try:
    from backend.config import ANIMATED_MAX_BYTES, STATIC_MAX_BYTES
except ImportError:
    from config import ANIMATED_MAX_BYTES, STATIC_MAX_BYTES

logger = logging.getLogger("uvicorn")

TRAY_SIZE = (96, 96)
TRAY_MAX_BYTES = 50 * 1024  # 50 KB


def create_tray_icon(input_image_bytes: bytes) -> bytes:
    """
    Generate a WhatsApp-compliant 96x96 PNG tray icon (<= 50 KB)
    from image bytes (WebP, PNG, or JPEG).
    """
    try:
        with Image.open(io.BytesIO(input_image_bytes)) as img:
            # Handle first frame if animated
            img.seek(0)
            img_rgba = img.convert("RGBA")

            # Fit into 96x96 preserving aspect ratio
            w, h = img_rgba.size
            ratio = min(96 / w, 96 / h)
            new_w, new_h = max(1, int(round(w * ratio))), max(1, int(round(h * ratio)))
            resized = img_rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)

            tray_canvas = Image.new("RGBA", TRAY_SIZE, (0, 0, 0, 0))
            offset = ((96 - new_w) // 2, (96 - new_h) // 2)
            tray_canvas.paste(resized, offset, resized)

            buf = io.BytesIO()
            tray_canvas.save(buf, format="PNG", optimize=True)
            png_bytes = buf.getvalue()

            if len(png_bytes) > TRAY_MAX_BYTES:
                # Fallback to quantized palette PNG if unexpectedly large
                buf = io.BytesIO()
                quantized = tray_canvas.quantize(colors=128)
                quantized.save(buf, format="PNG", optimize=True)
                png_bytes = buf.getvalue()

            return png_bytes
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process tray icon: {e}")


def validate_pack_sticker(file_bytes: bytes, index: int = 1) -> Dict[str, Any]:
    """
    Validate that a single sticker meets WhatsApp requirements:
    - 512x512 WebP
    - Static <= 100 KB, Animated <= 500 KB
    """
    size = len(file_bytes)
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            if img.format != "WEBP":
                raise HTTPException(
                    status_code=400,
                    detail=f"Sticker #{index} is not a valid WebP image (format: {img.format})."
                )
            if img.size != (512, 512):
                raise HTTPException(
                    status_code=400,
                    detail=f"Sticker #{index} must be exactly 512x512 px (got {img.size[0]}x{img.size[1]})."
                )

            is_anim = getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1

            if is_anim:
                if size > ANIMATED_MAX_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Animated sticker #{index} exceeds 500 KB WhatsApp limit ({size // 1024} KB)."
                    )
            else:
                if size > STATIC_MAX_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Static sticker #{index} exceeds 100 KB WhatsApp limit ({size // 1024} KB)."
                    )

            return {
                "is_animated": is_anim,
                "size": size,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Sticker #{index} is corrupted or cannot be read: {e}"
        )


def build_sticker_pack_archive(
    name: str,
    publisher: str,
    stickers: List[Tuple[bytes, List[str]]],
    tray_bytes: Optional[bytes] = None
) -> bytes:
    """
    Build a WhatsApp-compatible sticker pack ZIP archive containing:
    - pack.json
    - tray.png (96x96 PNG <= 50 KB)
    - 01.webp .. NN.webp (all uniform type: either all static or all animated)
    """
    count = len(stickers)
    if count < 3:
        raise HTTPException(
            status_code=400,
            detail=f"A WhatsApp sticker pack requires at least 3 stickers (provided: {count})."
        )
    if count > 30:
        raise HTTPException(
            status_code=400,
            detail=f"A WhatsApp sticker pack allows at most 30 stickers (provided: {count})."
        )

    # Validate all stickers and check type uniformity
    pack_type: Optional[bool] = None  # True = animated, False = static
    validated_stickers = []

    for idx, (s_bytes, emojis) in enumerate(stickers):
        meta = validate_pack_sticker(s_bytes, index=idx + 1)
        is_anim = meta["is_animated"]

        if pack_type is None:
            pack_type = is_anim
        elif pack_type != is_anim:
            type_str = "animated" if pack_type else "static"
            current_str = "animated" if is_anim else "static"
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Sticker pack must be uniform. Initial stickers are {type_str}, "
                    f"but sticker #{idx + 1} is {current_str}. Mixed packs are forbidden by WhatsApp."
                )
            )

        clean_emojis = [e for e in emojis if e.strip()][:3]
        if not clean_emojis:
            clean_emojis = ["✨"]

        validated_stickers.append((s_bytes, clean_emojis))

    # Process tray icon (generate from 1st sticker if not provided)
    if tray_bytes and len(tray_bytes) > 0:
        tray_png = create_tray_icon(tray_bytes)
    else:
        tray_png = create_tray_icon(validated_stickers[0][0])

    # Build pack.json metadata
    pack_id = str(uuid.uuid4()).replace("-", "")[:16]
    pack_meta = {
        "android_play_store_link": "",
        "ios_app_store_link": "",
        "publisher": publisher.strip() or "WhatsApp Sticker Maker",
        "identifier": pack_id,
        "name": name.strip() or "Sticker Pack",
        "tray_image_file": "tray.png",
        "animated_sticker_pack": bool(pack_type),
        "stickers": []
    }

    # Build in-memory ZIP archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tray.png", tray_png)

        for idx, (s_bytes, emojis) in enumerate(validated_stickers):
            filename = f"{idx + 1:02d}.webp"
            zf.writestr(filename, s_bytes)
            pack_meta["stickers"].append({
                "image_file": filename,
                "emojis": emojis
            })

        pack_json_bytes = json.dumps(pack_meta, indent=2, ensure_ascii=False).encode("utf-8")
        zf.writestr("pack.json", pack_json_bytes)

    return zip_buffer.getvalue()
