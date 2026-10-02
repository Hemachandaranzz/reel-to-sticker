# Reel → WhatsApp Sticker Generator

A privacy-first web application that converts short videos and Instagram Reels into WhatsApp-ready static (≤ 100 KB) and animated (≤ 500 KB, ≤ 10s) WebP stickers, featuring visual trimming, 1:1 framing, caption and emoji overlays, motion effects, sticker pack bundling, and WhatsApp export.

---

## Technical Specifications (WhatsApp Standard Compliant)

| Specification | Static Sticker | Animated Sticker |
| :--- | :--- | :--- |
| **Canvas Dimensions** | Exactly 512 × 512 px WebP | Exactly 512 × 512 px WebP |
| **Maximum File Size** | **≤ 100 KB** (strict enforcement) | **≤ 500 KB** (strict enforcement) |
| **Duration Limit** | 1 frame | **≤ 10 seconds** |
| **Audio** | No audio | Stripped (`-an`) |
| **Animation Loop** | N/A | Infinite loop (`loop=0`) |
| **Padding / Alpha** | Preserved transparent canvas | Preserved transparent canvas (`yuva420p`) |
| **Tray Icon** | 96 × 96 PNG (≤ 50 KB) | 96 × 96 PNG (≤ 50 KB) |
| **Sticker Pack Rules** | 3 to 30 stickers; uniform type | 3 to 30 stickers; uniform type |

---

## Key Features

- **Visual Video Trimmer:** Client-side thumbnail generation with dual-handle range scrubbing, keyboard nudging (`0.1s`), and live loop preview.
- **Custom 1:1 Framing:** Draggable square crop overlay with Fit (transparent padding), Fill (center crop), and custom positioning.
- **Auto-Optimizer Ladder:** Automatically retries FPS, WebP quality, compression level, and content downscaling to guarantee stickers land under WhatsApp's strict size limits.
- **Text & Emoji Overlays:** Caption overlays with meme fonts (Impact, Sans-serif, Comic), customizable stroke, colors, and emoji tags.
- **Motion Effects:** Horizontal flip, reverse playback, and boomerang loops.
- **Background Cutout & Outline:** Transparent cutouts with classic die-cut white sticker outline and edge feathering.
- **Sticker Pack Builder (Task 14–16):** Persistent browser storage (IndexedDB), emoji mapping (1–3 emojis per sticker), 96×96 tray icon generator, and ZIP export with `pack.json`.
- **SSRF-Safe Reel Link Guidance:** Strictly validates Instagram URLs client-side and server-side without fetching remote URLs; provides step-by-step download and permission guidance.
- **Background Jobs:** In-memory TTL job store with progress tracking and cancellation support.

---

## Local Development (Windows)

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **FFmpeg with `libwebp` encoder**:
  ```powershell
  winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
  ```

### 2. Backend Setup (FastAPI)
```powershell
cd "z:\video to sticker\backend"
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
.\venv\Scripts\uvicorn.exe main:app --reload --host 127.0.0.1 --port 8000
```
- API Health: `http://127.0.0.1:8000/api/health`
- Swagger Documentation: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup (React + Vite)
```powershell
cd "z:\video to sticker\frontend"
npm.cmd install
npm.cmd run dev
```
Open `http://localhost:5173/` in your browser.

---

## Running Automated Tests

### Backend Test Suite (Pytest - 38 tests)
```powershell
cd "z:\video to sticker"
.\backend\venv\Scripts\pytest.exe backend/tests -v
```

### Frontend Test Suite (Vitest)
```powershell
cd "z:\video to sticker\frontend"
npm.cmd test
```

### Frontend Production Build
```powershell
cd "z:\video to sticker\frontend"
npm.cmd run build
```

---

## Docker & Production Deployment

Run the entire full-stack application using Docker Compose:

```bash
docker compose up --build -d
```

- **Frontend:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`

---

## Extending Media Providers (Authorized Meta Graph API)

Direct scraping of Instagram URLs is prohibited by Meta terms of service and poses SSRF security vulnerabilities. To add an authorized Meta Graph API or licensed content partner integration:

1. Subclass `MediaProvider` in [`backend/services/providers/base.py`](file:///z:/video%20to%20sticker/backend/services/providers/base.py):
   ```python
   from backend.services.providers.base import MediaProvider
   from pathlib import Path

   class MetaGraphApiProvider(MediaProvider):
       def __init__(self, app_id: str, app_secret: str):
           self.app_id = app_id
           self.app_secret = app_secret

       async def fetch(self, reel_shortcode: str, destination: Path) -> Path:
           # Authenticate with Meta Graph API
           # Verify media access permissions
           # Download to destination path
           return destination
   ```
2. Register the provider in `get_media_provider(...)` in [`backend/services/providers/base.py`](file:///z:/video%20to%20sticker/backend/services/providers/base.py).
3. **Security Checklist for New Providers:**
   - [ ] Strict host allowlist (`graph.facebook.com` only)
   - [ ] Reject all non-HTTPS redirects
   - [ ] Network egress timeout (≤ 15s)
   - [ ] File-size streaming cap (abort if > 50 MB)
   - [ ] Clean up temporary files on failures

---

## Privacy & License

- **Ephemeral Processing:** Uploaded files and stickers are stored only in temporary directories and auto-purged upon completion or after 15 minutes.
- **Zero Content Logging:** No user media or filenames are stored in logs.
- **Disclaimer:** WhatsApp and Instagram are registered trademarks of Meta Platforms, Inc. This application is an independent open-source tool.
