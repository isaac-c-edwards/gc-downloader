# DECISIONS.md

Log of non-obvious implementation choices.

## Milestone 0

- **`http_client.py`:** Shared `httpx.AsyncClient` lives in its own module and is
  initialized via FastAPI lifespan hooks in `main.py`, so later modules can import
  `get_http_client()` without circular imports.
- **CORS default:** `http://localhost:3000` matches the default Next.js dev server.

## Milestone 1

- **Conference enumeration (hybrid):** The public landing page only surfaces the
  ~3 newest conferences in static HTML (the full archive loads via JS). So we
  scrape the landing page only to find the newest *published* conference (the
  "ceiling"), then generate the full April/October cadence from 1971 up to that
  ceiling. This lists the complete archive (111 conferences) without probing the
  server, and never shows an unpublished future conference. A date-based fallback
  computes the ceiling if the landing scrape fails. New conferences appear
  automatically once the landing page surfaces them.
- **Format-agnostic extractor:** Older conferences (e.g. 2024) tag sessions/talks
  with `data-content-type` attributes, but current conferences (2026) and many
  non-English pages omit them entirely. The extractor therefore parses the shared
  `nav.manifest > ul.doc-map` nesting and identifies talks by the presence of a
  speaker (`p.primaryMeta`), skipping session landing tiles (no speaker, slug ends
  in `session`/`meeting`, or title equals the session name). This works across all
  tested years and languages.
- **HTML parser:** Used Python's built-in `html.parser` via BeautifulSoup (no lxml)
  to avoid native build dependencies on Windows/Python 3.13.
- **Unknown `lang`:** Normalized to the default (`eng`) rather than returning 400,
  for a friendlier UX (per docs/09's allowed choice).
- **Conference `image_url` in catalog:** Left `null` in the light catalog list to
  avoid extra requests; session/talk images are populated in the detail response.
- **Catalog cache:** In-process `cachetools.TTLCache` (12h default) keyed by
  `(uri, lang)`, guarded by an async lock.

## Milestone 6

- **"Select all" lazy-load race:** When the user clicks "Select all" before a
  conference row has been expanded/fetched, we now set a `pendingSelectAll` ref
  and open the accordion. A `useEffect` in `ConferenceRow` fires once `detail`
  arrives and fulfills the deferred selection automatically. The flag is also
  reset on language change so stale intents never carry over.
- **Language-change cache invalidation:** `LanguageSelect` calls
  `queryClient.invalidateQueries({ queryKey: ["conference"] })` on change in
  addition to updating the Zustand store. This ensures any already-open
  accordion immediately re-fetches in the new language rather than waiting for
  its stale-time to expire.

## Milestone 7

- **FR-8 scheduled refresh:** A background `asyncio.Task` started in the
  FastAPI lifespan clears the entire catalog cache every 6 hours and pre-warms
  the English catalog. This guarantees a new conference appears within 6 hours
  of being published, without any redeploy. 6 hours was chosen as a comfortable
  middle ground: the cache stays warm for normal usage while staying fresh
  enough to catch a newly published conference within a few hours of its
  weekend appearance.
- **SummaryToast:** A short-lived (6 s) toast component fires after a job
  download succeeds, replacing the need to manually read the ProgressModal
  summary before closing it. The modal still shows the full skipped-talks list
  for detail; the toast gives a one-liner ("Downloaded 47 talks.") that persists
  briefly after the modal is dismissed.
- **Reduced-motion:** A global CSS rule in `globals.css` collapses all
  animation/transition durations to 0.01 ms when `prefers-reduced-motion:
  reduce` is set, covering both Tailwind utilities and any custom transitions.
- **Deployment:** `render.yaml` at the repo root drives a Render Web Service
  for the backend (Python/uvicorn, `rootDir: backend`). `frontend/vercel.json`
  locks the delivery mode to `job` for hosted deployments. README updated with
  step-by-step deploy instructions and a production verification checklist.

## Pre-deployment hardening (post-M7 audit)

A self-review before the first real deployment surfaced several gaps against
`docs/06`/`docs/11`. All were addressed together:

- **Single shared politeness gate:** `content_api.py`, `scraper.py`,
  `media/downloader.py`, and `media/packager.py`'s cover-art fetch each had
  their *own* `asyncio.Semaphore(max_concurrency)`. With the default of 12,
  effective concurrency against the source could reach ~48 instead of 12 —
  the opposite of "never hammer the server" (`AGENTS.md`). Extracted a single
  `app/source/politeness.py` module (one semaphore, one jittered-delay
  function, one `Retry-After` handler) that every outbound fetcher now
  imports, so `MAX_CONCURRENCY` is a true global cap. Cover-art fetches were
  previously not gated at all; they now go through the same module.
- **`robots.txt` compliance:** `docs/11` rule 2 requires honoring
  `robots.txt`. Added `politeness.is_allowed()`, which fetches and caches
  (per-host, in-memory, for the process lifetime) a `RobotFileParser` and is
  checked before every outbound request. A new `RobotsDisallowed` exception
  subclasses `ContentUnavailable` (not `AppError` directly) specifically so
  existing `except ContentUnavailable:` fallback logic in `catalog.py`
  (content-API → scraper) keeps working unchanged if one path is blocked but
  another isn't.
- **`Retry-After` honored:** `docs/11` rule 4. On a 429, `polite.
  respect_retry_after()` parses the header (delay-seconds or HTTP-date) and
  sleeps that long (capped at 30s so one uncooperative response can't stall a
  job indefinitely) before the existing tenacity retry fires.
- **Legal disclaimer:** `docs/11` explicitly requires the disclaimer text in
  *both* the footer and the README — neither had it. Added a `Footer.tsx`
  component (rendered at the end of the scrollable content in `page.tsx`,
  intentionally not fighting for space with the sticky `SelectionBar`) and a
  blockquote near the top of `README.md`.
- **Memory bound on ZIP building (NFR-2):** Both download paths previously
  fetched+tagged the *entire* selection into memory before writing anything
  out — `packager.stream_zip` used `asyncio.gather()` over all items (all
  results held until the whole gather resolved, before any ZIP bytes were
  yielded), and the Mode B job runner buffered every tagged MP3 into a
  `zip_entries` list before opening the `ZipFile` at all. For a full
  "Select all" (45+ talks) that's hundreds of MB resident at once — a real
  OOM risk on a free-tier host (512 MB typical cap).
  - `stream_zip` now processes `items` in batches of `max_concurrency`,
    calling zipstream-ng's `zs.all_files()` to drain/yield each batch's bytes
    before starting the next, and only calls `zs.footer()` once at the very
    end. (Confirmed via reading zipstream-ng's source: iterating `zs`
    directly triggers `finalize()` = `all_files()` + `footer()`, which closes
    the archive — so batched draining requires calling `all_files()`
    directly instead and deferring `footer()`.)
  - The Mode B job runner now writes each tagged talk to the on-disk
    `ZipFile` via `zf.writestr()` inside the `asyncio.as_completed` loop,
    instead of accumulating a list first. Entries land in completion order
    rather than sorted-path order; this is invisible to end users since
    file managers/zip viewers sort alphabetically regardless of physical
    member order in the archive.
  - Added `tests/test_packager.py` (mocked pipeline, no network) asserting
    the batched output is still a structurally valid ZIP with exactly the
    expected entries, across both the multi-batch and single-batch cases,
    and that a failing talk is skipped rather than aborting the archive.
- **Per-IP rate limiting:** Added `slowapi` with a 60/minute default (via
  middleware) plus stricter per-route limits on the two endpoints that fan
  out into many source requests — `POST /api/jobs` and `POST /api/download`
  (6/minute each) — since those are the ones that could indirectly be used
  to hammer the source site. `GET /api/jobs/{id}` (polled every ~1.5s by the
  frontend) got a looser 120/minute override, and `/api/health` is exempt
  entirely so hosting-platform health probes are never throttled. A custom
  429 handler matches the app's existing `{error: {code, message}}` shape
  instead of slowapi's default `{error: "<string>"}` body, so the frontend's
  existing error-parsing logic (`body?.error?.message`) keeps working.
- **`naming.py` test coverage:** `docs/06` asked for `naming.py` to be
  covered alongside `extractor.py`; only the latter had tests. Added
  `tests/test_naming.py` covering illegal-character stripping, unicode
  normalization, length trimming, zero-padding at various digit widths, and
  the exact FR-5 folder-structure format.
- **`pytest-asyncio`:** Needed to test the new async `stream_zip` batching
  behavior. Added `backend/requirements-dev.txt` (pytest + pytest-asyncio,
  layered on top of `requirements.txt`) since these are dev-only and
  shouldn't bloat the production install. `pytest.ini` sets
  `asyncio_mode = auto` so async test functions don't need explicit
  `@pytest.mark.asyncio` markers.
- **`LICENSE`:** Added an MIT license for the codebase, with an explicit note
  that it does not extend to the fetched Church content (which remains
  governed by the existing `docs/11` disclaimer).

## Handling conferences with no translation in the selected language

Fact-checked: the source genuinely doesn't publish Portuguese (and likely
other) translations of General Conference before ~1990, so pre-1990
Portuguese conference IDs 404 at the source — this is not a bug. The catalog
list itself is *generated* (every April/October since 1971, see FR-1), not
fetched, so the backend cannot know in advance which of the ~110 generated
conferences lack a translation in a given language without asking the source
about each one — and doing that for every conference on every language
change would mean ~110 extra requests per switch, which conflicts with the
politeness rules in `docs/11`.

Chosen approach — lazy discovery + graceful degradation, no hardcoded
per-language cutoff years:

- **Backend:** `content_api.get_content` now raises `ContentNotFound` (a
  `ContentUnavailable` subclass) specifically for a genuine 404, as opposed
  to the existing generic `ContentUnavailable` (network/5xx/robots/retries
  exhausted). `catalog.get_conference` catches `ContentNotFound` distinctly,
  caches a sentinel negative result keyed by `(conference_id, lang)` for the
  rest of the cache TTL (docs/06 NFR-3), and raises a new `LanguageUnavailable`
  error (`code: "LanguageUnavailable"`, HTTP 404) instead of the generic
  `NotFound`. Re-expanding the same conference/language combo — even after
  collapsing and reopening, or a page refresh — hits the cache and never
  re-queries the source.
- **Frontend:** `lib/api.ts` now throws an `ApiError` carrying the backend's
  `code` field. `ConferenceRow` checks for `code === "LanguageUnavailable"`:
  the *first* expand of a given conference+language still does one network
  round trip (there's no way to know in advance), but once that resolves as
  unavailable, the row stops behaving like a dropdown — no chevron, no
  "Select all", just the conference name and a quiet "Not available in this
  language" label. React Query's `retry` is also disabled for this specific
  error (retrying a confirmed non-translation is pointless and just adds
  load on the source). Genuine transient errors (network blips, 5xx) keep
  their existing red error state, now with a real "Retry" button (previously
  the message said "Try again" but nothing was clickable).

## Disk-backed media pipeline (Render OOM hardening)

- **Problem:** Even sequential in-RAM tagging held ~3× each MP3 during
  `tag_mp3`, so full-conference jobs on Render's 512 MB free tier still OOM'd
  intermittently (long keynotes spike higher).
- **Approach:** `media/pipeline.py` streams each MP3 to a temp file
  (`fetch_mp3_to_file`), tags in place (`tag_mp3_file`), then job-mode ZIP
  builds use `ZipFile.write(path)` so Python reads from disk in chunks instead
  of `writestr(bytes)`. Mode A (`stream_zip`) still reads one batch of temp
  files into zipstream per batch — tagging no longer multiplies RAM.
- **Concurrency:** Job runner restored batched parallelism up to
  `PER_JOB_CONCURRENCY` per job (4 on Render) because peak RAM is now bounded
  by batch count × read buffers, not batch × full MP3 × 3. A global
  `_job_lock` serialized every user behind one job; replaced with a bounded
  `asyncio.Semaphore` (`MAX_CONCURRENT_JOBS`, default 3) so several jobs build
  in parallel, extras queue with a reported position, and admission control
  (`MAX_QUEUED_JOBS`) rejects overload with 503 instead of OOM. Jobs are
  launched via `asyncio.create_task` rather than FastAPI `BackgroundTasks`
  (which run sequentially within a single request).

## Language switch duplicate downloads

- **Bug:** After changing audio language, `SelectionBar` scanned the entire
  React Query cache for conference details and included **every cached
  language** for the same conference. Talk IDs are language-independent, so
  one selected talk produced two identical `selection` entries and the job
  downloaded the same MP3 twice (UI showed "1 selected" but progress was 2/2).
- **Fix:** `getCachedConferenceDetails()` filters cache entries to the current
  language only; `LanguageSelect` removes stale conference queries for other
  languages on switch.
