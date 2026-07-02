# 09 — Data Model

Canonical shapes shared across backend (Pydantic) and frontend (TypeScript).
Keep these in sync; they define the API payloads in `docs/07`.

## Identifiers

- **Conference id:** `"YYYY-MM"` where MM ∈ {`04`, `10`} → e.g. `"2026-04"`.
- **Session id:** `"{conference_id}-s{order}"` → e.g. `"2026-04-s1"`.
- **Talk id:** the source talk slug, namespaced by conference →
  e.g. `"2026-04-11nelson"`. Must be stable and URL-safe.
- **Talk uri:** the source path used to fetch content →
  `"/general-conference/2026/04/11nelson"`.

## Entities

### Conference (catalog item — light)
```ts
type Conference = {
  id: string;          // "2026-04"
  year: number;        // 2026
  month: number;       // 4 or 10
  name: string;        // "April 2026 General Conference"
  image_url?: string;  // conference cover art
};
```

### ConferenceDetail (with sessions/talks)
```ts
type ConferenceDetail = Conference & {
  sessions: Session[];
};

type Session = {
  id: string;          // "2026-04-s1"
  order: number;       // 1-based, used for disc number (TPOS)
  name: string;        // "Saturday Morning Session"
  talks: Talk[];
};

type Talk = {
  id: string;          // "2026-04-11nelson"
  uri: string;         // "/general-conference/2026/04/11nelson"
  order: number;       // 1-based within session, used for track number (TRCK)
  title: string;       // talk title
  speaker: string;     // display name, e.g. "President Russell M. Nelson"
  image_url?: string;  // talk image (falls back to conference image)
};
```

### TalkMedia (resolved at download time)
```ts
type TalkMedia = {
  talk_id: string;
  mp3_url: string;
  image_url?: string;
  duration_ms?: number;
};
```

### Selection (download request)
```ts
type Selection = {
  conference_id: string;
  session_ids?: string[];  // include whole sessions
  talk_ids?: string[];     // include individual talks
};

type DownloadRequest = {
  lang: string;            // "eng"
  selection: Selection[];
};
```

### Tags (for mutagen)
```ts
type TalkTags = {
  title: string;       // TIT2
  artist: string;      // TPE1  (speaker)
  album: string;       // TALB  (conference name)
  album_artist: string;// TPE2  = "General Conference"
  track: string;       // TRCK  "3/8"
  disc: string;        // TPOS  "1/5"
  year: number;        // TDRC
  genre: string;       // TCON
};
```

### Job (Mode B)
```ts
type JobState = "queued" | "running" | "done" | "error";

type Skip = { talk_id: string; reason: string };

type JobStatus = {
  job_id: string;
  state: JobState;
  total: number;
  completed: number;
  skipped: Skip[];
  download_ready: boolean;
  error?: string;
};
```

### Language
```ts
type Language = { code: string; name: string }; // { "eng", "English" }
```

## Derived values

- **Track number (TRCK):** `talk.order` / number-of-talks-in-session.
- **Disc number (TPOS):** `session.order` / number-of-sessions-in-conference.
- **Album:** `conference.name`.
- **Zip file name:** `GC Downloader - {Month YYYY} ({Language}).zip` (single
  conference) or `GC Downloader - {N} conferences ({Language}).zip` (multiple).
- **In-zip path:** see `docs/02` FR-5.

## Validation rules

- A `Selection` MUST reference a real `conference_id` and at least one
  session/talk overall across the request.
- Unknown ids → `400 BadSelection` (`docs/07`).
- `lang` MUST be one of `/api/languages`; unknown → fall back to `eng` or 400
  (choose one and note it in `DECISIONS.md`).
