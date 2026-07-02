# 06 — Backend Spec

FastAPI app under `backend/`. This document defines the internal modules. The
HTTP contract is in `docs/07`; data shapes are in `docs/09`.

## Configuration (`app/config.py`)

Load from environment via `pydantic-settings`. Provide `.env.example`.

| Setting | Env var | Default | Notes |
| --- | --- | --- | --- |
| Source base URL | `SOURCE_BASE_URL` | `https://www.churchofjesuschrist.org` | |
| User-Agent | `HTTP_USER_AGENT` | a descriptive UA incl. contact (see `docs/11`) | |
| Max concurrent fetches | `MAX_CONCURRENCY` | `4` | Politeness cap. |
| Per-request delay (ms) | `REQUEST_DELAY_MS` | `250` | Jittered. |
| Catalog cache TTL (s) | `CATALOG_TTL` | `43200` (12h) | |
| Request timeout (s) | `HTTP_TIMEOUT` | `30` | |
| CORS allowed origins | `CORS_ORIGINS` | frontend URL(s) | |
| Delivery mode | `DELIVERY_MODE` | `auto` | `direct`, `job`, or `auto`. |

## Data-source layer (`app/source/`)

### `content_api.py`
- `async get_content(uri: str, lang: str) -> dict` — calls the internal study
  content API (`docs/05`), returns parsed JSON. Retries transient errors
  (tenacity). Raises a typed `ContentUnavailable` on hard failure.

### `scraper.py`
- `async get_talk_html(uri: str, lang: str) -> ParsedTalk` — HTML fallback;
  prefers embedded JSON in `<script>` over DOM walking.

### `extractor.py`
- Pure functions that defensively pull `title`, `speaker`, `mp3_url`,
  `image_url` out of either the API JSON or the HTML. **Search-based, not
  hardcoded deep paths** (see `docs/05`). Unit-test against captured fixtures.

### `catalog.py`
- `async list_conferences(lang) -> list[Conference]` — live enumeration (FR-1).
- `async get_conference(year, month, lang) -> Conference` — sessions + talks,
  with talk order, titles, speakers (audio resolved lazily).
- `async resolve_talk_media(talk_uri, lang) -> TalkMedia` — returns mp3_url +
  image_url; tries content API then scraper; raises `MediaUnavailable` (caught by
  the pipeline as a skip).

### `cache.py`
- TTL cache (cachetools) keyed by `(uri, lang)` for catalog/content. Audio is not
  cached in v1.

## Media pipeline (`app/media/`)

### `downloader.py`
- `async fetch_mp3(url) -> bytes | AsyncIterator[bytes]` — streams audio bytes
  with timeout + retry. Enforce global concurrency via an `asyncio.Semaphore`
  shared with the source layer.

### `tagger.py`
- `tag_mp3(data: bytes, tags: TalkTags, cover: bytes | None) -> bytes` — uses
  **mutagen** to write ID3v2.3/2.4 frames. Required frames:

| Field | ID3 frame |
| --- | --- |
| Title | `TIT2` |
| Artist (speaker) | `TPE1` |
| Album (conference) | `TALB` |
| Album Artist | `TPE2` = "General Conference" |
| Track # | `TRCK` (e.g. `3/8`) |
| Disc # (session) | `TPOS` (e.g. `1/5`) |
| Year | `TDRC` |
| Genre | `TCON` |
| Cover art | `APIC` (type 3, front cover; set mime per image) |

- If cover bytes are missing, skip `APIC` without error.
- Tagging must operate on in-memory bytes (no temp files required) so it composes
  with streaming.

### `packager.py`
- `stream_zip(items: AsyncIterator[ZipItem]) -> AsyncIterator[bytes]` using
  `zipstream-ng`. Each `ZipItem` has an in-zip path (per the FR-5 folder
  structure) and the tagged MP3 bytes.
- Append a final `manifest.txt` (or `summary.json`) entry listing successes and
  skips with reasons.

### `naming.py`
- `safe_filename(s)` — strips/normalizes characters illegal on Windows, macOS,
  and Android; collapses whitespace; trims length.
- `zip_path(conference, session, talk, index)` — builds the exact folder/file
  path from `docs/02` FR-5, zero-padded.

## Jobs (`app/jobs/`)

Supports the host-friendly async mode (Mode B in `docs/04`).

- `create_job(selection) -> job_id`
- `get_job(job_id) -> JobStatus` with fields: `state`
  (`queued|running|done|error`), `total`, `completed`, `skipped[]`,
  `download_ready: bool`.
- `run_job(job_id)` — background task that runs the pipeline and writes the ZIP to
  a temp location (or holds a streaming generator), updating progress.
- Jobs are in-memory for v1 (single instance). Document that horizontal scaling
  would need shared storage (Redis/disk) — out of scope for v1.
- TTL-evict finished jobs and clean up temp files.

## Concurrency & politeness

- One shared `asyncio.Semaphore(MAX_CONCURRENCY)` gates **all** outbound requests
  (catalog, media resolution, audio download).
- Apply `REQUEST_DELAY_MS` jittered delay between source requests.
- Use a single shared `httpx.AsyncClient` (connection pooling, HTTP/2).
- Retries: tenacity, exponential backoff, max ~3 attempts, only on
  network/5xx/429. Honor `Retry-After` on 429.

## Error model

Typed exceptions mapped to API responses (see `docs/07`):
- `ContentUnavailable` / `MediaUnavailable` → recorded as per-talk skip.
- `SourceUnreachable` → 502 from catalog endpoints.
- `BadSelection` → 400.

## Testing

- Unit-test `extractor.py` and `naming.py` against saved fixtures (real API JSON
  + real talk HTML). Do not hit the network in unit tests.
- One opt-in integration test (env-gated) that fetches a single known talk to
  validate the live path; skipped by default to respect the source.
