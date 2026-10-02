# 🚀 Cloud Deployment Guide for Reel to Sticker

Your application is now configured as a **single, unified service** containing both the React frontend and FastAPI backend in a production-grade multi-stage `Dockerfile`.

---

## 📦 Step 1: Push Your Code to GitHub

Open a terminal in `z:\video to sticker` and run:

```bash
git add .
git commit -m "Production release with unified Dockerfile"
```

Then create a new repository on [GitHub](https://github.com/new) (e.g. named `reel-to-sticker`), and link it:

```bash
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/reel-to-sticker.git
git push -u origin main
```

---

## 🌐 Option A: Deploy on Render.com (Recommended — 100% Free)

1. Sign up or log in at **[render.com](https://render.com)** using your GitHub account.
2. Click the **"New +"** button in the dashboard and select **"Web Service"**.
3. Connect your **`reel-to-sticker`** GitHub repository.
4. Render will read the included `render.yaml` and `Dockerfile` automatically:
   - **Environment:** Docker
   - **Region:** Oregon (US) or Frankfurt (EU)
   - **Instance Type:** Free
5. Click **"Deploy Web Service"**.
6. Render builds the React frontend, sets up Python 3.11 with FFmpeg, and provides your live HTTPS URL:
   `https://reel-to-sticker-xxxx.onrender.com`

---

## 🚆 Option B: Deploy on Railway.app

1. Go to **[railway.app](https://railway.app)** and log in with GitHub.
2. Click **"New Project"** → **"Deploy from GitHub repo"**.
3. Choose your `reel-to-sticker` repository.
4. Railway detects the `Dockerfile` and deploys automatically.
5. In the service settings, click **"Generate Domain"** to get your public live URL.

---

## 🤗 Option C: Deploy on Hugging Face Spaces (Free 16GB RAM CPU)

Hugging Face Spaces provides 16GB RAM and generous CPU for Docker apps completely free:

1. Go to **[huggingface.co/new-space](https://huggingface.co/new-space)**.
2. Enter Space name (e.g. `reel-to-sticker`).
3. Select License: `MIT`.
4. Select Space SDK: **Docker** → **Blank**.
5. Push this repository to your Hugging Face Space git URL.
6. It automatically builds the container and launches your app live!

---

## ⚙️ Architecture Overview

* **Frontend:** React 19 + Vite, compiled into static production assets.
* **Backend:** FastAPI + Uvicorn + FFmpeg (with `libwebp`), serving both the API (`/api/*`) and the frontend single-page app (`/`).
* **Port Handling:** Automatically reads dynamic `$PORT` environment variable required by cloud hosting platforms.
* **Health Check:** `/api/health` endpoint configured for zero-downtime health probes.
