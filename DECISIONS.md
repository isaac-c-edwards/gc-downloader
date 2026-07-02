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
