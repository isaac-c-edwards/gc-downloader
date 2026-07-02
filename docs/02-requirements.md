# 02 — Requirements

Requirements use RFC 2119 keywords: **MUST**, **SHOULD**, **MAY**.

## Functional requirements

### FR-1: Browse conferences (live)
- The app **MUST** display a list of available conferences (year + month/season,
  e.g. "April 2026", "October 2025"), newest first.
- This list **MUST** be generated dynamically from the source site so new
  conferences appear automatically. No hardcoded conference dates.
- The list **SHOULD** be cached briefly server-side (see NFR-3) for speed.

### FR-2: Browse sessions within a conference
- Selecting a conference **MUST** reveal its sessions (e.g. "Saturday Morning
  Session", "Saturday Afternoon Session", "Sunday Morning Session", "Sunday
  Afternoon Session", plus any additional sessions).
- Each session **SHOULD** display its talks (title + speaker) for transparency.

### FR-3: Selection
- The user **MUST** be able to select individual sessions across one or more
  conferences.
- The user **MUST** have a **"Select all"** control (select all sessions in a
  conference; and an option to select all talks in a session).
- The UI **MUST** clearly show what is currently selected and a running count
  (e.g. "3 sessions, 47 talks selected").
- The user **MAY** deselect individual talks within a selected session.

### FR-4: Language selection
- The user **MUST** be able to choose the audio language from the set of
  languages the source provides for that content.
- Default language **MUST** be English.
- If a selected talk is unavailable in the chosen language, the app **MUST** skip
  it gracefully and report the skip rather than failing the whole job.

### FR-5: Download & packaging
- On download, the backend **MUST** fetch each selected talk's MP3, tag it, and
  add it to a ZIP.
- The ZIP **MUST** be organized into folders by session, using this structure:

```
GC Downloader - April 2026 (English).zip
└── 2026-04 April General Conference/
    ├── 1 - Saturday Morning Session/
    │   ├── 01 - Talk Title - Speaker Name.mp3
    │   ├── 02 - Talk Title - Speaker Name.mp3
    │   └── ...
    ├── 2 - Saturday Afternoon Session/
    │   └── ...
    └── ...
```

- Filenames **MUST** be sanitized (no characters illegal on Windows/macOS/Android
  filesystems) and **MUST** be zero-padded for correct sort order.
- If multiple conferences are selected at once, each conference **MUST** be a
  top-level folder inside the ZIP.

### FR-6: Metadata tagging
Each MP3 **MUST** have these ID3v2 tags set (see `docs/06` for exact frames):
- **Title (TIT2):** talk title
- **Artist (TPE1):** speaker name
- **Album (TALB):** conference name (e.g. "April 2026 General Conference")
- **Album Artist (TPE2):** "General Conference"
- **Track number (TRCK):** order within session
- **Disc number (TPOS):** session order within conference
- **Year (TDRC):** conference year
- **Genre (TCON):** "Religion & Spirituality" (or "Speech")
- **Cover art (APIC):** the talk's image if available, else the conference image

### FR-7: Progress & resilience
- For multi-talk jobs, the app **MUST** report progress (e.g. "Downloading 12 of
  47…").
- A failure on a single talk **MUST NOT** abort the entire job; failures **MUST**
  be collected and reported at the end.
- The final response **MUST** tell the user how many files succeeded/were skipped.

### FR-8: New-conference detection
- Because FR-1 is live, new conferences appear automatically. The backend
  **SHOULD** refresh its catalog cache on a schedule aligned to the General
  Conference cadence (first weekends of April and October) so the new conference
  shows up promptly, while still working purely on-demand.

## Non-functional requirements

### NFR-1: Cross-platform & responsive
- The UI **MUST** be fully usable on phone (≈375px), tablet (≈768px), and desktop
  (≥1280px) widths. Touch targets **MUST** be finger-friendly on mobile.

### NFR-2: Performance / memory
- The backend **MUST** stream the ZIP to the client rather than building the whole
  archive in memory, so large multi-session downloads don't exhaust RAM.
- Audio **MUST** be fetched on demand and not require permanent server storage.

### NFR-3: Politeness & caching
- Catalog/metadata responses from the source **MUST** be cached server-side with a
  short TTL (suggest 6–24h for catalog, since it rarely changes) to minimize
  requests.
- The fetcher **MUST** apply concurrency limits and a small delay/backoff (see
  `docs/11`).

### NFR-4: Reliability
- The data-source layer **MUST** use the structured content API first and fall
  back to HTML scraping if the structured path fails (see `docs/05`).

### NFR-5: Accessibility
- Controls **SHOULD** be keyboard-navigable with sensible labels/ARIA roles.

### NFR-6: Observability
- The backend **SHOULD** log each external request (URL, status, duration) at
  debug level to aid troubleshooting without leaking sensitive data.

## Constraints

- No official public API exists; data comes from the public site (see `docs/05`).
- Hosting free tiers impose request timeouts; large jobs **MUST** use the async
  job + streaming pattern (see `docs/06`/`docs/07`) to stay within limits.
