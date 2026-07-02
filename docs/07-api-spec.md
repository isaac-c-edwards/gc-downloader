# 07 — API Spec

Base path: `/api`. All responses are JSON unless noted. All endpoints accept a
`lang` parameter (default `eng`). CORS allows the frontend origin(s).

Data shapes referenced here are defined in `docs/09`.

---

## GET `/api/languages`

Returns the list of selectable audio languages.

**200**
```json
{
  "languages": [
    { "code": "eng", "name": "English" },
    { "code": "spa", "name": "Español" },
    { "code": "por", "name": "Português" }
  ],
  "default": "eng"
}
```

---

## GET `/api/catalog`

Live list of conferences (FR-1). Cached server-side (NFR-3).

**Query:** `lang` (optional)

**200**
```json
{
  "conferences": [
    {
      "id": "2026-04",
      "year": 2026,
      "month": 4,
      "name": "April 2026 General Conference",
      "image_url": "https://www.churchofjesuschrist.org/imgs/<hash>/.../default"
    }
  ]
}
```
Newest first. Does **not** include sessions/talks (kept light).

---

## GET `/api/conferences/{id}`

Sessions + talks for one conference (FR-2). `id` is `YYYY-MM`.

**Query:** `lang` (optional)

**200**
```json
{
  "id": "2026-04",
  "name": "April 2026 General Conference",
  "year": 2026,
  "month": 4,
  "image_url": "...",
  "sessions": [
    {
      "id": "2026-04-s1",
      "order": 1,
      "name": "Saturday Morning Session",
      "talks": [
        {
          "id": "2026-04-11nelson",
          "uri": "/general-conference/2026/04/11nelson",
          "order": 1,
          "title": "Talk Title",
          "speaker": "President Russell M. Nelson",
          "image_url": "..."
        }
      ]
    }
  ]
}
```

Audio URLs are **not** included here; they're resolved at download time.

**404** if the conference id doesn't exist. **502** if the source is unreachable.

---

## Download — two supported modes

The frontend picks a mode from its env/config. Backend supports both.

### Mode A (direct streaming) — POST `/api/download`

Streams a ZIP back immediately. Best for local/self-hosted.

**Request body**
```json
{
  "lang": "eng",
  "selection": [
    {
      "conference_id": "2026-04",
      "session_ids": ["2026-04-s1"],            
      "talk_ids": ["2026-04-11nelson"]          
    }
  ]
}
```
- Provide `session_ids` to include whole sessions, and/or `talk_ids` for
  individual talks. "Select all" = include every `session_id` of the conference.
- At least one talk must resolve, or return **400** `BadSelection`.

**200** `Content-Type: application/zip`,
`Content-Disposition: attachment; filename="GC Downloader - April 2026 (English).zip"`
— streamed body. A `summary.json` is included inside the ZIP listing
skips/failures (FR-7).

### Mode B (async job) — for hosts with request timeouts

#### POST `/api/jobs`
Body identical to Mode A. **202**
```json
{ "job_id": "b1f2...", "total": 47 }
```

#### GET `/api/jobs/{job_id}`
**200**
```json
{
  "job_id": "b1f2...",
  "state": "running",            
  "total": 47,
  "completed": 12,
  "skipped": [
    { "talk_id": "2026-04-...", "reason": "no audio for language" }
  ],
  "download_ready": false
}
```
`state` ∈ `queued | running | done | error`.

#### GET `/api/jobs/{job_id}/download`
Available when `download_ready` is true. Streams the ZIP (same headers as Mode A).
**409** if not ready, **404** if job unknown/expired.

---

## Error format

Non-2xx responses use:
```json
{ "error": { "code": "BadSelection", "message": "No talks selected." } }
```
Codes: `BadSelection` (400), `NotFound` (404), `NotReady` (409),
`SourceUnreachable` (502), `Internal` (500).

---

## Progress UX guidance

- Mode A: show an indeterminate "Preparing your download…" state since the body
  streams as one response; the in-zip `summary.json` reports skips afterward.
- Mode B: poll `GET /api/jobs/{id}` every ~1–2s and render
  `completed / total` plus live skip notices.
