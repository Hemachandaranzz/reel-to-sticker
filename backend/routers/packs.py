import json
import logging
from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile

try:
    from backend.config import RATE_LIMIT_PER_MINUTE
    from backend.services.limiter import limiter
    from backend.services.packs import build_sticker_pack_archive
except ImportError:
    from config import RATE_LIMIT_PER_MINUTE
    from services.limiter import limiter
    from services.packs import build_sticker_pack_archive

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/packs", tags=["packs"])


@router.post("/export")
@limiter.limit(RATE_LIMIT_PER_MINUTE)
async def export_sticker_pack(
    request: Request,
    name: str = Form("My Sticker Pack"),
    publisher: str = Form("WhatsApp Sticker Maker"),
    stickers_meta: str = Form("[]"),
    tray_file: Optional[UploadFile] = File(None),
    stickers: List[UploadFile] = File(...)
):
    """
    Validate and bundle 3-30 stickers into a WhatsApp-ready sticker pack ZIP containing:
    - pack.json
    - tray.png (96x96 PNG <= 50 KB)
    - 01.webp .. NN.webp (uniform: all static or all animated)
    """
    if len(stickers) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"At least 3 stickers are required for a WhatsApp pack (received: {len(stickers)})."
        )
    if len(stickers) > 30:
        raise HTTPException(
            status_code=400,
            detail=f"At most 30 stickers are allowed in a single pack (received: {len(stickers)})."
        )

    # Parse metadata json
    try:
        meta_list = json.loads(stickers_meta) if stickers_meta else []
    except Exception:
        meta_list = []

    sticker_tuples = []
    for idx, sticker_upload in enumerate(stickers):
        content = await sticker_upload.read()
        # Find emoji metadata if available
        emojis = []
        if idx < len(meta_list) and isinstance(meta_list[idx], dict):
            emojis = meta_list[idx].get("emojis", [])
        elif idx < len(meta_list) and isinstance(meta_list[idx], list):
            emojis = meta_list[idx]
        sticker_tuples.append((content, emojis))

    tray_bytes = None
    if tray_file is not None:
        tray_bytes = await tray_file.read()

    zip_bytes = build_sticker_pack_archive(
        name=name,
        publisher=publisher,
        stickers=sticker_tuples,
        tray_bytes=tray_bytes
    )

    clean_filename = f"{name.strip().replace(' ', '_').lower() or 'sticker_pack'}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}"',
            "X-Pack-Count": str(len(stickers)),
        }
    )
