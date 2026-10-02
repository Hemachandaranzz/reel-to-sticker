# Reel → WhatsApp Sticker Website — Task Plan for Antigravity

## How to use this file

Give Antigravity **one task at a time**, in order. After each task, run the "Verify" steps yourself before moving on. Do not paste the whole file at once.

**Prompt template for each task:**

> Read `PLAN.md` for project context (sections 0–2). Implement **Task N** only. Do not start other tasks. When finished, run the Verify steps and report results.

---

## 0. Project summary

A website where a user uploads a video (or pastes an Instagram Reel link) and gets a **WhatsApp-ready static or animated WebP sticker**. Later: trimming, cropping, background removal, text/effects, and sticker-pack export.

**Dev environment:** Windows, VS Code, PowerShell.

## 1. Stack

| Layer | Tech |
|---|---|
| Frontend | React + Vite (JavaScript), plain CSS |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Video | FFmpeg (must include `libwebp`) + FFprobe |
| Images | Pillow |
| Background removal (later) | `rembg` (U2Net) or MediaPipe selfie segmentation |
| Jobs (later) | In-process background tasks → optional Redis + RQ |
| Tests | pytest (backend), Vitest (frontend) |

## 2. Hard requirements (WhatsApp stickers)

Verify against the official WhatsApp sticker page before launch.

- Canvas: **512 × 512 px**, WebP.
- Static: **≤ 100 KB**.
- Animated: animated WebP, **≤ 500 KB**, **≤ 10 s**, looping.
- Sticker pack: **3–30 stickers**, all static **or** all animated (not mixed), tray icon **96 × 96 PNG ≤ 50 KB**, each sticker linked to 1–3 emojis.
- A web page **cannot** directly trigger "Add to WhatsApp". Export a downloadable file/ZIP and give import instructions for a compatible sticker-maker app.

## 3. Rules for the whole project

1. No scraping, login cookies, or bypassing Instagram restrictions. Reel links are optional; upload is the always-working path.
2. Never fetch arbitrary user URLs on the backend (SSRF).
3. Process files in temp directories; delete after use. Never log video content.
4. Every endpoint returns JSON errors in the form `{"detail": "human readable message"}`.
5. Keep config in one place (`backend/config.py`, `frontend/.env`).
6. Each task must leave the app in a runnable state.

## 4. Target folder structure

```
reel-sticker/
  PLAN.md
  README.md
  docker-compose.yml          (Task 18)
  backend/
    main.py
    config.py
    routers/        (sticker.py, reel.py, packs.py)
    services/       (ffmpeg.py, optimizer.py, validate.py, cutout.py, packs.py)
    tests/
    requirements.txt
  frontend/
    src/
      App.jsx
      components/   (Dropzone, Trimmer, CropBox, ModeTabs, Preview, Presets, PackBuilder)
      lib/          (api.js, format.js)
      App.css
```

---

# PHASE 1 — Working local converter (MVP)

## Task 1 — Project scaffold and tooling check

**Goal:** Empty but runnable frontend + backend.

**Do:**
- Create the folder structure above.
- Backend: venv, `requirements.txt` (`fastapi`, `uvicorn[standard]`, `python-multipart`, `pillow`, `pytest`, `httpx`).
- Frontend: `npm create vite@latest frontend -- --template react`.
- `backend/config.py` with constants: `MAX_UPLOAD_MB=50`, `ALLOWED_EXTENSIONS`, `STATIC_MAX_BYTES=100_000`, `ANIMATED_MAX_BYTES=500_000`, `MAX_DURATION=10`, `FFMPEG_TIMEOUT=60`, `CORS_ORIGINS`.
- `backend/main.py`: `FastAPI()` app, **CORSMiddleware** allowing `http://localhost:5173` and `http://127.0.0.1:5173`, and `GET /api/health`.
- On startup, check that `ffmpeg` and `ffprobe` exist and that the `libwebp` encoder is available (`ffmpeg -encoders`). Log a clear error if not.
- Frontend: Vite proxy for `/api` → `http://127.0.0.1:8000` so the frontend uses relative URLs.
- Write a README with Windows run instructions.

**Verify:**
- `uvicorn main:app --reload` → `/api/health` returns `{"status":"ok"}`.
- `npm run dev` opens the default page.
- Startup log confirms FFmpeg + libwebp.

---

## Task 2 — FFmpeg service and upload validation

**Goal:** Safe building blocks reused by every endpoint.

**Do:**
- `services/ffmpeg.py`: `run_ffmpeg(args)` and `run_ffprobe(path)` using `subprocess.run` with timeout, `-nostdin`, captured output. Map failures to `HTTPException(422, ...)`.
- `services/validate.py`:
  - Extension allowlist (`.mp4 .mov .webm .m4v .gif`).
  - Stream the upload to a temp file in chunks and abort over `MAX_UPLOAD_MB`.
  - Validate real content with `ffprobe` (has a video stream, duration > 0, duration ≤ 10 minutes, resolution sane). Reject otherwise.
  - Return metadata: `duration`, `width`, `height`, `fps`.
- New endpoint `POST /api/probe` → returns metadata (the frontend uses it to size trim sliders).

**Verify:**
- pytest: valid MP4 passes; a renamed `.txt` file as `.mp4` is rejected; an oversized file returns 413.
- Swagger `/docs` shows `/api/probe` working.

---

## Task 3 — Static sticker endpoint

**Goal:** `POST /api/sticker/static`.

**Inputs:** `file`, `second` (float), optional `fit` (`contain` | `cover`).

**Do:**
- Clamp/validate `second` against the probed duration.
- Extract the frame with FFmpeg, scale into 512×512 (`contain` pads transparent, `cover` center-crops).
- Encode with Pillow WebP via the **size optimizer** (`services/optimizer.py`): try quality 90→30 in steps, then if still too large, reduce palette/resize slightly; stop when ≤ 100 KB.
- Return the WebP with `Content-Disposition`.
- Response headers: `X-Sticker-Size`, `X-Sticker-Quality`.

**Verify:**
- Output is 512×512, ≤ 100 KB, transparent padding preserved (open in an image viewer that shows alpha).
- Out-of-range `second` returns 400 with a clear message.

---

## Task 4 — Animated sticker endpoint with auto-optimizer

**Goal:** `POST /api/sticker/animated` that reliably lands under 500 KB.

**Inputs:** `file`, `start`, `duration` (≤10), optional `fit`, optional `speed` (0.5–2.0).

**Do:**
- Validate `start`/`duration` against probed length.
- Encode with `libwebp` (`-loop 0`, `-an`, `format=yuva420p`).
- **Retry ladder** in `optimizer.py` until size ≤ 500 KB, stopping at the first success:
  1. fps 15 / quality 70
  2. fps 12 / quality 60
  3. fps 10 / quality 50
  4. fps 8 / quality 45
  5. fps 8 / quality 35 / `compression_level 6`
  6. shrink to 480 then 448 content size (still on 512 canvas)
  7. trim duration by 20% steps (never below 1 s)
- If nothing works, return 422 with a suggestion ("Try a shorter clip").
- Return a JSON-friendly report in headers: final fps, quality, duration, bytes.
- After encoding, **validate output** with `ffprobe`/Pillow: dimensions 512×512, frame count > 1, duration ≤ 10 s, loop = infinite.

**Verify:**
- 3 s, 5 s and 10 s test clips all produce ≤ 500 KB files.
- File loops in a browser `<img>` tag.
- Test file with pytest assertions on size and dimensions.

---

## Task 5 — Cleanup, limits and error handling

**Goal:** Make it safe to run publicly.

**Do:**
- Ensure all temp directories are removed even on errors (use `try/finally` or `TemporaryDirectory`).
- Add rate limiting (`slowapi`): e.g. 10 conversions/min per IP.
- Limit concurrent FFmpeg processes (semaphore, default 2). Extra requests wait or get 429.
- Global exception handler returning JSON.
- Add `ffmpeg` flags to limit threads (`-threads 2`).
- Structured logging (request id, duration, output size) with **no file content or filenames** logged.

**Verify:**
- Hammer the endpoint with a script; confirm 429s and no leftover temp folders.

---

## Task 6 — Basic React frontend (upload → download)

**Goal:** Usable UI for both sticker types.

**Do:**
- Split into components: `Dropzone` (drag-and-drop + click), `ModeTabs` (Static / Animated), `Preview`.
- Call `/api/probe` after file selection; show duration/resolution.
- Controls: static → frame timestamp; animated → start + duration (number inputs for now).
- Show progress state, error messages, result preview on a checkerboard background (so transparency is visible), file size badge, and a **Download** button (don't auto-download).
- Mobile-first, responsive layout.
- Use `AbortController` so the user can cancel a conversion.

**Verify:**
- Full flow works in Chrome on desktop and at 375 px width.
- Errors from the backend appear in the UI.

---

# PHASE 2 — Real editing experience

## Task 7 — Video preview and visual trimmer

**Goal:** No more typing timestamps.

**Do:**
- Show the uploaded video in a `<video>` element using `URL.createObjectURL`.
- `Trimmer` component: dual-handle range slider over a **thumbnail timeline** (generate thumbnails client-side with a hidden canvas, ~10 frames).
- Enforce the 10 s max; show live "estimated duration" badge.
- Static mode: scrubber that picks the exact frame, with a "use this frame" button.
- Loop-preview the selected range.
- Keyboard accessible (arrow keys nudge by 0.1 s).

**Verify:** The trimmed range on screen matches the sticker output.

---

## Task 8 — Crop and framing controls

**Goal:** Let users choose what's inside the square.

**Do:**
- `CropBox`: draggable/resizable square overlay on the video (aspect ratio locked 1:1), plus quick buttons: **Fit (pad)**, **Fill (center crop)**, **Custom**.
- Send crop as normalized `crop_x`, `crop_y`, `crop_size` (0–1) to backend; apply with the FFmpeg `crop` filter before scaling.
- Backend validates the crop bounds.

**Verify:** Custom crop from the UI produces a matching sticker; invalid values return 400.

---

## Task 9 — Live size estimate and quality presets

**Goal:** Users understand the limits before converting.

**Do:**
- Presets: **Smallest**, **Balanced**, **Best quality** (map to optimizer starting points).
- After conversion, show size vs the limit as a progress bar, plus what the optimizer changed ("reduced to 10 fps").
- "Try again smaller" button.
- Warn when the selected duration is likely to force heavy compression.

**Verify:** The preset changes the output size predictably.

---

## Task 10 — Background removal (transparent cutout)

**Goal:** True sticker-style cutouts.

**Do:**
- Backend `services/cutout.py` using `rembg` (or MediaPipe) — make it an **optional dependency** and feature-flag it (`ENABLE_CUTOUT`).
- **Static:** remove the background from the chosen frame.
- **Animated:** extract frames at the target fps → segment each frame → temporal smoothing of the mask (blend with the previous mask) to avoid flicker → reassemble to animated WebP with alpha.
- Hard cap on frames (e.g. 120) for CPU safety; run as a background job (see Task 15) with progress.
- Optional **edge feather** and **white sticker outline** (dilate the alpha mask by N px, fill white) — the classic sticker look.
- Frontend: toggles for "Remove background" and "Sticker outline" with an outline thickness slider.

**Verify:**
- Static cutout looks clean.
- Animated cutout has no heavy flicker and still meets the 500 KB limit.

---

## Task 11 — Text, emoji and effects

**Goal:** Make it more fun than a plain converter.

**Do:**
- Caption overlay: text, font choice (3–5 bundled open-license fonts), color, stroke, position (top/bottom), drag to move.
- Emoji/sticker overlay (bundled small PNGs).
- Effects: speed (0.5×–2×), reverse, boomerang (forward + backward loop), fade in/out, flip horizontally.
- Render text/emoji in the backend (Pillow overlay → FFmpeg `overlay` filter) so the output matches the preview.
- Live preview in the browser using CSS/canvas approximations.

**Verify:** Output matches what's seen in the preview; size limits still enforced.

---

# PHASE 3 — Instagram links (done honestly)

## Task 12 — Reel URL validation and graceful fallback

**Goal:** Accept a reel link without scraping.

**Do:**
- `POST /api/reel/check` with a URL. Use `validate_instagram_url` (https only; hosts `instagram.com` / `www.instagram.com`; paths `/reel/`, `/reels/`, optionally `/p/`). Reject everything else. **Never fetch the URL.**
- Normalize and strip tracking query parameters.
- Frontend: a URL field at the top. If valid, show a friendly guided panel:
  1. Open the reel in Instagram.
  2. Save/download the video using an option you have permission to use (the creator's own reel, or with their permission).
  3. Drop the file here.
- Show an optional embed preview via Instagram's official embed (`<blockquote class="instagram-media">`) only if it works; never block the flow if it doesn't.
- Include a short "only convert videos you have permission to use" notice with a required checkbox.

**Verify:**
- Valid reel URLs accepted; look-alike domains (`instagram.com.evil.com`, `http://`) rejected.
- Flow never dead-ends: always offers upload.

---

## Task 13 — Optional authorized-provider integration (stub only)

**Goal:** Prepare the architecture without committing to a risky approach.

**Do:**
- Define an interface `MediaProvider.fetch(url) -> temp_file_path` in `services/providers/base.py`.
- Implement only `UploadProvider` (existing path) and a `NotConfiguredProvider` that returns a clear message.
- Document in README: how to add an official Meta API or licensed provider later, with a checklist (terms, permissions, retention, cost, host allowlist, redirect validation, timeouts, network egress limits).

**Verify:** The app behaves identically; adding a provider requires no changes outside `providers/`.

---

# PHASE 4 — Sticker packs and WhatsApp export

## Task 14 — Pack builder UI

**Goal:** Create multiple stickers, then export together.

**Do:**
- "Add to pack" button after each conversion; the pack is kept in browser state (IndexedDB so it survives refresh).
- Pack screen: reorder (drag), delete, rename, per-sticker emoji picker (1–3 emojis, required by WhatsApp), pack name + author.
- Enforce rules in the UI: 3–30 stickers, **all static or all animated**, show counter and a checklist of what's missing.
- Tray icon: pick any sticker or upload an image; backend (or Pillow in-browser) makes a **96×96 PNG ≤ 50 KB**.

**Verify:** The UI blocks export until the pack is valid.

---

## Task 15 — Background jobs and progress (needed for cutouts and packs)

**Goal:** Long conversions don't block requests.

**Do:**
- Switch heavy endpoints to job-style: `POST /api/jobs` → `{job_id}`; `GET /api/jobs/{id}` → status, progress %, result URL; `GET /api/jobs/{id}/result`.
- Start with FastAPI `BackgroundTasks` + an in-memory job store with TTL (e.g. 15 min), designed so Redis + RQ can replace it later.
- Frontend polling (or Server-Sent Events) with a progress bar and cancel.
- Results auto-delete after the TTL.

**Verify:** Cutout jobs show progress and the UI stays responsive.

---

## Task 16 — Pack export

**Goal:** Give users a real path into WhatsApp.

**Do:**
- Backend `POST /api/packs/export` builds a ZIP containing: all stickers as `.webp`, `tray.png` (96×96), and a `pack.json` (name, author, emojis).
- Also produce the format that popular third-party sticker apps import (research current formats such as `.wastickers`; implement only what you can verify against the app's documentation).
- Validate every file again before packaging (size, dimensions, type consistency).
- Frontend: Download ZIP + an **instructions screen** for Android and iPhone using a compatible sticker-maker app, with screenshots/steps. Clearly say the website cannot add directly to WhatsApp.
- (Optional, advanced) Provide a small companion Android project template that uses WhatsApp's official sticker-pack `ContentProvider` approach, documented in `/docs/android-companion.md`.

**Verify:** Import the exported pack into a sticker-maker app on a real phone and add it to WhatsApp.

---

# PHASE 5 — Quality, polish and launch

## Task 17 — Tests and CI

**Do:**
- Backend pytest suite: validation, probe, static/animated size & dimension assertions, optimizer ladder (with a mocked oversized result), URL validator, SSRF rejection cases.
- Generate tiny test videos in fixtures with FFmpeg (`testsrc`) instead of committing large files.
- Frontend Vitest: format helpers, pack validation logic.
- GitHub Actions workflow: install FFmpeg, run backend and frontend tests, lint (ruff + eslint).

---

## Task 18 — Docker and deployment

**Do:**
- `backend/Dockerfile` (python-slim + ffmpeg with libwebp), non-root user, read-only filesystem where possible, resource limits.
- `docker-compose.yml` for local full-stack run.
- Environment-based config (CORS origins, limits, feature flags).
- Deployment notes: frontend on Vercel/Netlify, backend on a Docker-capable host. Enforce body-size limits at the proxy too. Keep the cutout worker separate when traffic grows.

---

## Task 19 — Privacy, legal and UX polish

**Do:**
- Privacy page: files processed temporarily, deleted after processing/TTL, no accounts, no content logging.
- Terms: only convert content you have permission to use; Instagram is a trademark of Meta, not affiliated; WhatsApp likewise.
- Accessibility pass: labels, focus states, contrast, reduced-motion support, keyboard use of trimmer.
- PWA: installable, offline shell, and Web Share Target (so users can "share" a video from their phone gallery straight into the site).
- Dark mode and responsive checks on small phones.
- Error copy review: every error says what to do next.

---

## Task 20 — Final QA checklist

Run through every item and fix failures:

- [ ] `/api/health` returns ok; startup warns if FFmpeg/libwebp missing
- [ ] Static sticker: 512×512, ≤ 100 KB, transparent padding
- [ ] Animated sticker: 512×512, ≤ 500 KB, ≤ 10 s, loops, plays in Chrome and on a phone
- [ ] Optimizer ladder succeeds on clips of 3 s, 6 s and 10 s
- [ ] Fake video file rejected (content check, not just extension)
- [ ] Oversized upload rejected at app and proxy level
- [ ] Reel URL validator rejects look-alike domains and `http://`
- [ ] No backend fetch of user-supplied URLs anywhere
- [ ] Temp files removed after success, failure and cancel
- [ ] Rate limit and concurrency cap work under load
- [ ] Trim/crop/text/cutout previews match final output
- [ ] Pack export validates 3–30, uniform type, tray icon, emojis
- [ ] Exported pack imports into a sticker app and appears in WhatsApp
- [ ] Mobile layout works at 360–430 px width
- [ ] Privacy/terms pages present

---

# Extra feature backlog (after launch)

- **GIF and Tenor/Giphy-style input**: accept `.gif` and convert (already in the allowlist).
- **Batch mode**: upload several clips, generate a whole pack in one go.
- **Auto-highlight**: suggest the best 3 s segment (motion/scene-change detection with FFmpeg `select='gt(scene,0.3)'`).
- **Face-aware crop**: keep the face centered when cropping to a square (MediaPipe).
- **Loop smoothing**: crossfade the last frames into the first for seamless loops.
- **Style filters**: cartoon/comic, pixelate, sepia, glitch.
- **Static from animated**: export a poster frame alongside the animated sticker.
- **Shareable preview link**: temporary, auto-expiring page for a finished sticker.
- **Usage analytics** that are privacy-friendly (counts only, no media, no IPs stored).
- **Localization**: i18n with English + Tamil/Hindi first.
- **Telegram sticker export** (WebM/PNG specs differ — separate pipeline).
- **Undo/redo and project autosave** in the editor.
