# GC Downloader

GC Downloader is a cross-platform web application that lets a user select one or
more sessions of General Conference (e.g. "April 2026"), then downloads every
talk in those sessions as MP3 files, injects accurate ID3 metadata (speaker as
Artist, talk title as Track, conference as Album, plus cover art), and packages
everything into a single ZIP organized into folders by session.

The app works on phones, tablets, and desktop browsers. The list of available
conferences is generated live from the official site, so brand-new conferences
appear automatically the moment they are published.

> **Disclaimer:** Unofficial tool. General Conference audio and images are ©
> Intellectual Reserve, Inc. This app downloads publicly available files for
> personal use and is not affiliated with or endorsed by The Church of Jesus
> Christ of Latter-day Saints. See
> [`docs/11-legal-and-ethics.md`](./docs/11-legal-and-ethics.md) for the full
> polite-scraping and copyright policy this project follows.

## Who this is for

This repository is a **specification package meant to be implemented by an AI
coding agent**. The author is building this as a zero-manual-code project: the
goal is for an AI model to read these documents and produce a working
application. The documents are written to be precise, unambiguous, and
buildable.

## How to use these docs

Read them in order. Each builds on the previous one.

| File | Purpose |
| --- | --- |
| [`AGENTS.md`](./AGENTS.md) | Top-level instructions and ground rules for the AI agent building this app. **Start here.** |
| [`docs/01-project-overview.md`](./docs/01-project-overview.md) | Vision, problem statement, target users, success criteria. |
| [`docs/02-requirements.md`](./docs/02-requirements.md) | Functional and non-functional requirements. |
| [`docs/03-tech-stack.md`](./docs/03-tech-stack.md) | Chosen technologies and the reasoning behind each. |
| [`docs/04-architecture.md`](./docs/04-architecture.md) | System design, components, request/data flow. |
| [`docs/05-data-source.md`](./docs/05-data-source.md) | Exactly how to fetch conference lists, talks, audio URLs, and artwork. |
| [`docs/06-backend-spec.md`](./docs/06-backend-spec.md) | Backend modules: fetching, tagging, zipping, jobs. |
| [`docs/07-api-spec.md`](./docs/07-api-spec.md) | HTTP API contract between frontend and backend. |
| [`docs/08-frontend-spec.md`](./docs/08-frontend-spec.md) | UI/UX, screens, components, responsive behavior. |
| [`docs/09-data-model.md`](./docs/09-data-model.md) | Canonical data structures shared across the system. |
| [`docs/10-build-plan.md`](./docs/10-build-plan.md) | Ordered milestones the agent should follow to build it. |
| [`docs/11-legal-and-ethics.md`](./docs/11-legal-and-ethics.md) | Copyright, polite-scraping, and rate-limit rules. |

## High-level tech stack

- **Backend:** Python + FastAPI
- **Data fetching:** `httpx` (HTTP), `selectolax`/`BeautifulSoup4` (HTML fallback)
- **Audio tagging:** `mutagen` (ID3v2)
- **Packaging:** streaming ZIP (`zipstream-ng`)
- **Frontend:** Next.js (React) + Tailwind CSS
- **Deployment:** Vercel (frontend) + Render/Railway/Fly.io (backend)

See [`docs/03-tech-stack.md`](./docs/03-tech-stack.md) for the full rationale.

## Running locally (Milestone 0+)

Use **two separate terminals**. Do not run both from the same folder.

### Terminal 1 — Backend

```powershell
cd "C:\Users\Isaac\OneDrive - BYU-Idaho\BYUI Spring 2026\Special Topics CSE\gc-downloader\backend"
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

If you see **"port 8000 is already in use"**, the backend is already running — leave that terminal alone and skip to Terminal 2.

### Terminal 2 — Frontend

Open a **new** terminal (do not stay in the `backend` folder):

```powershell
cd "C:\Users\Isaac\OneDrive - BYU-Idaho\BYUI Spring 2026\Special Topics CSE\gc-downloader\frontend"
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The home page calls the
backend health endpoint and shows whether the API is connected.

If you see **"Another next dev server is already running"**, either:
- open [http://localhost:3000](http://localhost:3000) in your browser (it's already up), or
- stop the old server with `taskkill /PID <pid> /F` (the error message shows the PID).

Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` →
`frontend/.env.local` if you need to change defaults.

---

## Deploying to the web

### Backend → Render (free tier)

1. Fork / push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New → Web Service** → connect your repo.
3. Render auto-detects `render.yaml` at the repo root and pre-fills the settings.
4. Set the required environment variable in the Render dashboard:
   - `CORS_ORIGINS` → your Vercel frontend URL (e.g. `https://gc-downloader.vercel.app`)
5. Click **Deploy**. Copy the service URL (e.g. `https://gc-downloader-api.onrender.com`).

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → import your repo.
2. Set **Root Directory** to `frontend`.
3. Add environment variables:
   - `NEXT_PUBLIC_API_BASE_URL` → the Render backend URL from the step above
   - `NEXT_PUBLIC_DELIVERY_MODE` → `job`
4. Click **Deploy**.

> **Tip:** The `frontend/vercel.json` already sets `NEXT_PUBLIC_DELIVERY_MODE=job` so
> you only need to set `NEXT_PUBLIC_API_BASE_URL` manually.

### What gets enabled in hosted mode

- `DELIVERY_MODE=job` on the backend means all downloads go through the async job
  pipeline (POST /api/jobs → poll → download) instead of streaming directly.  
  This avoids Render/Vercel's 30-second request-timeout limit for large ZIP downloads.
- The catalog cache auto-refreshes every 6 hours, so new conferences that appear on
  the source site show up in the app within half a day — no redeploy needed.

---

## Verifying a production download

Open the deployed site on a real phone, then:

1. Pick **April 2026 General Conference** → **Select all**.
2. Leave the language as **English**.
3. Tap **Download ZIP** and wait for the progress bar to complete.
4. Open a produced MP3 in a music app and confirm:
   - **Title** = talk title, **Artist** = speaker name, **Album** = "April 2026 General Conference"
   - **Cover art** is present
   - **Track / Disc** numbers are set
5. Confirm the ZIP folder structure matches `docs/02-requirements.md` FR-5.

---

## Running the backend test suite

```powershell
cd "C:\Users\Isaac\OneDrive - BYU-Idaho\BYUI Spring 2026\Special Topics CSE\gc-downloader\backend"
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

Tests run entirely against saved fixtures/mocks and never hit the network.

## License

The GC Downloader source code is licensed under the [MIT License](./LICENSE).
This does **not** extend to the General Conference content the app fetches at
runtime — see the disclaimer above and
[`docs/11-legal-and-ethics.md`](./docs/11-legal-and-ethics.md).
