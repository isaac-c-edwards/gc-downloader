# 04 — Architecture

## Overview

GC Downloader is a two-tier app: a Next.js frontend and a FastAPI backend. The
backend owns all interaction with the source site; the frontend never talks to
`churchofjesuschrist.org` directly (avoids CORS issues and keeps politeness/
caching centralized).

```
┌─────────────────────────┐         HTTPS/JSON          ┌──────────────────────────────┐
│        Frontend         │  ───────────────────────▶   │           Backend            │
│   Next.js + Tailwind    │                              │           FastAPI            │
│  (phone/tablet/desktop) │  ◀───────────────────────   │                              │
└─────────────────────────┘   catalog, job status,      │  ┌────────────────────────┐  │
            │                  streamed ZIP              │  │   Data-source layer    │  │
            │                                            │  │  catalog / content API │  │
            │                                            │  │  + HTML scraper (fb)   │  │
            │                                            │  └───────────┬────────────┘  │
            ▼                                            │              │               │
   Browser saves ZIP                                     │  ┌───────────▼────────────┐  │
                                                         │  │  Media pipeline        │  │
                                                         │  │  download → tag → zip  │  │
                                                         │  └───────────┬────────────┘  │
                                                         └──────────────┼───────────────┘
                                                                        │ HTTPS (polite)
                                                                        ▼
                                                          churchofjesuschrist.org
                                                          + media CDN (ldscdn)
```

## Components

### Frontend (Next.js)
- **Catalog view:** fetches `/api/catalog`, renders conferences → sessions →
  talks as nested, expandable lists with checkboxes.
- **Selection store:** tracks which talks/sessions are selected and the language.
- **Download controller:** posts the selection to the backend, then either
  streams the ZIP directly or polls a job and downloads when ready (see `docs/07`).
- **Progress UI:** shows per-job progress and a final success/skip summary.

### Backend (FastAPI)

1. **Data-source layer** (`source/`)
   - `catalog.py`: enumerates conferences, sessions, talks (live).
   - `content_api.py`: calls the site's internal study content API (primary).
   - `scraper.py`: HTML fallback when the API path fails.
   - `cache.py`: short-TTL cache for catalog/metadata (NFR-3).
2. **Media pipeline** (`media/`)
   - `downloader.py`: fetches MP3 bytes with retries + concurrency limit.
   - `tagger.py`: writes ID3 tags + cover art via mutagen.
   - `packager.py`: streams tagged files into a ZIP with the required folder
     structure.
3. **Jobs** (`jobs/`)
   - Tracks long-running download jobs, exposes progress, supports streaming or
     polling delivery.

## Two delivery modes (pick per deployment)

The backend supports both; the frontend chooses based on environment.

- **Mode A — Direct streaming (simplest):** `POST /api/download` immediately
  streams the ZIP back. Best for local/self-hosted use where there's no strict
  request timeout. Recommended default for local runs.
- **Mode B — Async job + poll (host-friendly):** `POST /api/jobs` returns a
  `job_id`; frontend polls `GET /api/jobs/{id}` for progress; when complete,
  downloads from `GET /api/jobs/{id}/download` (streamed). Use this on hosts
  with short request timeouts (Vercel/Render free tiers).

See `docs/07` for the exact contracts.

## Request flow (download)

1. Frontend sends selected `{conference, session, talk}` IDs + language.
2. Backend resolves each talk to its **audio URL** and **metadata** via the
   data-source layer (using cached catalog where possible).
3. For each talk (bounded concurrency): download MP3 → tag with mutagen → feed
   into the ZIP stream under the correct session folder.
4. Failures are recorded but don't stop the batch.
5. ZIP streams to the client; a trailing manifest/summary reports skips.

## Caching strategy

- **Catalog cache:** conferences/sessions/talks list, short TTL (6–24h). This is
  what makes the UI fast and keeps source requests low.
- **No audio cache (v1):** audio is fetched on demand and streamed straight into
  the ZIP, then discarded. (A future optimization could add a temporary disk
  cache.)

## Error handling philosophy

- Network/transient errors: retry with backoff (tenacity), then skip-and-report.
- Missing audio/language: skip-and-report, never hard-fail the batch.
- Source structure change: the API-first/scrape-fallback design provides
  resilience; log loudly when falling back.
