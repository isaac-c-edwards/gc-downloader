# 10 — Build Plan

Build in milestones. Each milestone ends with something runnable and verifiable.
Log non-obvious decisions in `DECISIONS.md`.

## Milestone 0 — Scaffolding
- Create the repo layout from `AGENTS.md`.
- Backend: FastAPI app, `config.py`, health check `GET /api/health`,
  `requirements.txt`, `.env.example`, shared `httpx.AsyncClient`.
- Frontend: Next.js + Tailwind app, base layout/header, `.env.example`,
  API client in `lib/`.
- **Verify:** both apps start; frontend can hit `/api/health`.

## Milestone 1 — Data-source: catalog (read-only)
- Implement `content_api.py`, `scraper.py` (fallback), `extractor.py`,
  `cache.py`.
- Implement `catalog.list_conferences()` and `catalog.get_conference()`.
- Expose `GET /api/catalog` and `GET /api/conferences/{id}` and
  `GET /api/languages`.
- Save real fixtures (one conference's API JSON + one talk's HTML) and unit-test
  the extractor against them.
- **Verify:** hitting `/api/catalog` returns a live, newest-first list including
  the most recent conference; `/api/conferences/2026-04` returns sessions+talks.

## Milestone 2 — Frontend: browse & select
- Build `ConferenceList`, `ConferenceRow`, `SessionRow`, `TalkRow`,
  `SelectionBar`, `LanguageSelect` (`docs/08`).
- Implement selection state with tri-state + "Select all" + running totals.
- Wire React Query to the catalog endpoints.
- **Verify:** on phone and desktop widths, a user can expand conferences, select
  individual sessions/talks, use "Select all", and see accurate counts.

## Milestone 3 — Media pipeline (download one talk)
- Implement `downloader.fetch_mp3`, `tagger.tag_mp3` (mutagen), `naming.py`.
- Implement `catalog.resolve_talk_media`.
- Add a temporary debug route to download + tag a single talk.
- **Verify:** open the resulting MP3 in a media player; confirm
  Title/Artist/Album/Track/Disc/Year/cover art are correct.

## Milestone 4 — Packaging & download endpoint (Mode A)
- Implement `packager.stream_zip` (zipstream-ng) with the FR-5 folder structure
  and an in-zip `summary.json`.
- Implement `POST /api/download` (direct streaming).
- Enforce concurrency limit + delay + retries (politeness).
- **Verify:** select a full session, download the ZIP, confirm folder structure,
  filenames (zero-padded, sanitized), and tags; confirm a skipped talk doesn't
  abort the batch.

## Milestone 5 — Async jobs (Mode B) for hosting
- Implement `jobs/` (create/get/run, progress, skip tracking, temp cleanup).
- Implement `POST /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/download`.
- Frontend `ProgressModal` polling + auto-download + `SummaryToast`.
- **Verify:** a large multi-session job shows live progress and completes; works
  within hosted request-timeout limits.

## Milestone 6 — Multi-language & "Select all" hardening
- Populate `LanguageSelect`; re-fetch on language change.
- Verify a non-English download produces talks in that language and skips
  unavailable ones with a clear summary.
- Verify whole-conference "Select all" end to end.

## Milestone 7 — Polish & deploy
- Loading skeletons, error/retry states, empty states, accessibility pass,
  dark-mode (optional).
- Catalog cache + scheduled refresh aligned to April/October cadence (FR-8).
- Deploy frontend (Vercel) + backend (Render/Railway/Fly); set CORS + env;
  set frontend `DELIVERY_MODE=job`.
- Write the root `README.md` run instructions (local + deployed).
- **Verify:** the deployed site works on a real phone over the network: pick
  April 2026, Select all, download, load onto phone, play offline with correct
  tags.

## Definition of done
See `AGENTS.md` → "Definition of done" and run every check under "What to verify
before declaring success."
