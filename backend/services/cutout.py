import logging
from typing import List, Optional
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

from PIL import Image, ImageFilter

try:
    from backend.config import ENABLE_CUTOUT
except ImportError:
    from config import ENABLE_CUTOUT

logger = logging.getLogger("uvicorn")

try:
    import rembg
    REMBG_AVAILABLE = True
except Exception:
    rembg = None
    REMBG_AVAILABLE = False


def is_cutout_available() -> bool:
    """Check if background removal is enabled and rembg and numpy are installed."""
    return bool(ENABLE_CUTOUT and REMBG_AVAILABLE and NUMPY_AVAILABLE)



def apply_sticker_outline(
    image: Image.Image,
    outline_px: int = 4,
    feather: int = 1
) -> Image.Image:
    """
    Apply classic sticker outline and optional edge feathering:
    - Dilates the alpha channel by outline_px
    - Fills with pure white
    - Pastes the original cutout on top
    """
    if outline_px <= 0 and feather <= 0:
        return image

    img_rgba = image.convert("RGBA")
    r, g, b, alpha = img_rgba.split()

    if outline_px > 0:
        filter_size = 2 * outline_px + 1
        dilated_alpha = alpha.filter(ImageFilter.MaxFilter(filter_size))
        if feather > 0:
            dilated_alpha = dilated_alpha.filter(ImageFilter.GaussianBlur(feather))

        white_border = Image.new("RGBA", img_rgba.size, (255, 255, 255, 255))
        border_layer = Image.composite(
            white_border,
            Image.new("RGBA", img_rgba.size, (0, 0, 0, 0)),
            dilated_alpha
        )
        return Image.alpha_composite(border_layer, img_rgba)

    if feather > 0:
        feathered_alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
        img_rgba.putalpha(feathered_alpha)
        return img_rgba

    return img_rgba


def remove_background_static(
    image: Image.Image,
    outline_px: int = 0,
    feather: int = 0
) -> Image.Image:
    """Remove background from a static PIL image and optionally apply sticker outline."""
    if not is_cutout_available():
        logger.info("Background cutout skipped (rembg not available or ENABLE_CUTOUT is disabled).")
        return image

    try:
        cutout_img = rembg.remove(image)
        if outline_px > 0 or feather > 0:
            cutout_img = apply_sticker_outline(cutout_img, outline_px=outline_px, feather=feather)
        return cutout_img
    except Exception as e:
        logger.warning(f"Error during static background removal: {e}")
        return image


def remove_background_animated(
    frames: List[Image.Image],
    outline_px: int = 0,
    feather: int = 0,
    smoothing_factor: float = 0.6
) -> List[Image.Image]:
    """
    Segment frames and apply temporal smoothing to alpha masks to eliminate flicker:
    smoothed_mask[t] = smoothing_factor * current_mask + (1 - smoothing_factor) * smoothed_mask[t-1]
    """
    if not is_cutout_available() or not frames:
        return frames

    # Safety cap: max 120 frames
    max_frames = 120
    frames_to_process = frames[:max_frames]

    processed_frames = []
    prev_mask_np = None

    try:
        session = rembg.new_session("u2netp") if hasattr(rembg, "new_session") else None
    except Exception:
        session = None

    for frame in frames_to_process:
        try:
            if session:
                cutout = rembg.remove(frame, session=session)
            else:
                cutout = rembg.remove(frame)

            alpha = cutout.split()[3]
            alpha_np = np.array(alpha, dtype=np.float32)

            # Temporal smoothing with previous mask
            if prev_mask_np is not None and smoothing_factor < 1.0:
                smoothed_np = (
                    smoothing_factor * alpha_np + (1.0 - smoothing_factor) * prev_mask_np
                )
                prev_mask_np = smoothed_np
                final_alpha = Image.fromarray(np.clip(smoothed_np, 0, 255).astype(np.uint8))
            else:
                prev_mask_np = alpha_np
                final_alpha = alpha

            cutout.putalpha(final_alpha)

            if outline_px > 0 or feather > 0:
                cutout = apply_sticker_outline(cutout, outline_px=outline_px, feather=feather)

            processed_frames.append(cutout)
        except Exception as e:
            logger.warning(f"Error processing cutout frame: {e}")
            processed_frames.append(frame)

    return processed_frames
