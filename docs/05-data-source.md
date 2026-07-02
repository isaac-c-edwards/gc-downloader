# 05 — Data Source

> **Critical:** There is **no official public API** for General Conference media.
> Content is served by the public website `churchofjesuschrist.org` and audio is
> hosted on the Church's media CDN (`*.ldscdn.org` / image service on
> `churchofjesuschrist.org/imgs/...`). This document describes a **hybrid**
> strategy: use the site's structured/internal JSON first, fall back to HTML
> parsing. Always follow the politeness rules in `docs/11`.

## Key URLs and identifiers

All content is keyed by **language** (`lang` query param, e.g. `eng`, `spa`,
`por`, `fra`, `deu`, ...) and by a **conference id** in `YYYY/MM` form where MM is
`04` (April) or `10` (October).

- **Conference landing page (human):**
  `https://www.churchofjesuschrist.org/study/general-conference?lang=eng`
- **A specific conference (human):**
  `https://www.churchofjesuschrist.org/study/general-conference/2026/04?lang=eng`
- **A specific talk (human):**
  `https://www.churchofjesuschrist.org/study/general-conference/2026/04/<talk-slug>?lang=eng`

### Internal study content API (primary path)

The site's reading experience is backed by an internal content endpoint that
returns JSON for any study URI. Use it like this:

```
GET https://www.churchofjesuschrist.org/study/api/v3/language-pages/type/content
        ?lang={lang}
        &uri=/general-conference/{year}/{month}/{slug}
```

- For a **conference** (no slug, e.g. `uri=/general-conference/2026/04`), the
  response's table-of-contents / `content.body` lists sessions and the talks
  (with their URIs) inside each session.
- For a **talk** (`uri=/general-conference/2026/04/11nelson`), the response
  contains the talk's title, author/speaker, and a media/meta section that
  includes the **audio (MP3) URL** and **image URL(s)**.

> The exact JSON shape can change. **Do not hardcode deep key paths blindly.**
> Implement a small, defensive extractor that searches the response for:
> - the talk **title**,
> - the **speaker/author** string,
> - the **MP3 url** (look for a `.mp3` URL, typically on an `*.ldscdn.org` host
>   or under a `mediaUrl`/`download`/`audio` key),
> - the **image url** (the `churchofjesuschrist.org/imgs/<hash>/...` pattern).
>
> Log the raw JSON at debug level during development so the extractor can be
> tuned against real responses.

### HTML fallback path

If the content API call fails or its shape is unrecognized, fetch the human talk
page HTML and extract:

- **Title:** the main `<h1>` (often `#title1` or a heading inside `<header>`).
- **Speaker:** the author element (commonly `p.author-name` / `.author-name`, or a
  byline element near the title).
- **MP3 URL:** the page exposes a download menu ("This Page (MP3)"). The MP3 link
  is present in the page — search the HTML (and any embedded JSON in
  `<script>` tags, e.g. a `__NEXT_DATA__`-style or `application/ld+json` block)
  for a `.mp3` URL.
- **Image:** an `og:image` meta tag or the talk's hero image (`/imgs/<hash>/...`).

> Many talk pages embed a JSON blob in a `<script>` tag that already contains the
> media URLs. Prefer parsing that JSON over walking the DOM when present — it's
> more stable.

## Enumerating conferences (for FR-1, live list)

To build the always-current catalog:

1. Fetch the conference landing content
   (`uri=/general-conference`) via the content API (or the landing page HTML as
   fallback).
2. Extract the list of conferences — each links to `/general-conference/{year}/{month}`.
   Derive `{year, month}` from those URIs. This is how **new conferences appear
   automatically**: when the Church publishes April 2026, a new
   `/general-conference/2026/04` entry shows up here.
3. Sort newest-first.

> A simple, robust alternative for enumeration: derive candidate conference ids
> from the cadence (every April=`04` and October=`10`, year ≥ 1971) and probe,
> but **prefer scraping the actual landing list** so you never show a conference
> that isn't published yet, and you don't probe the server unnecessarily.

## Enumerating sessions & talks within a conference

1. Fetch `uri=/general-conference/{year}/{month}` content.
2. Parse the table of contents: it groups talks under **sessions** in order.
3. For each talk, capture: `talk slug/uri`, display order, title, speaker. Defer
   resolving the **audio URL** until download time (or resolve lazily) to keep
   the catalog light and reduce requests.

## Resolving audio at download time

For each selected talk:
1. Look up its `uri`.
2. Call the content API for that talk in the chosen `lang`.
3. Extract the MP3 URL + image URL via the defensive extractor.
4. If the chosen language has no audio for that talk, **skip and record** it
   (FR-4 / FR-7).

## Languages

- Pass the user's chosen `lang` code in every request.
- To populate the language selector, you MAY use a known list of conference audio
  languages (English `eng`, Spanish `spa`, Portuguese `por`, French `fra`, German
  `deu`, etc.). A talk/conference may not exist in every language; handle
  missing-language gracefully (FR-4).

## Reference implementations (study these, don't copy blindly)

These community projects confirm the approach is viable and show real URL/JSON
patterns. Use them to calibrate the extractor; respect their licenses if you
borrow anything.

- `nanoDBA/gc_podcast` — has a documented JSON schema (conference → sessions →
  talks → audio/image), proving the hybrid extraction shape. See its `SPEC.md`.
- `jonbonin/LDSGeneralConferenceDownloader` — multi-language MP3 downloader that
  navigates the site programmatically.
- `peytonbair/GeneralConferenceDownloader` — Python downloader by speaker.
- `bryanwhiting/generalconference` — scraper + structured data package.
- `openscriptureapi.org` (General Conference endpoints) — an **unofficial**
  community API exposing conference metadata
  (`/api/conference/v1/lds/en/conferences`, `/conference/:id`, `/talk/:id`).
  **MAY** be used as an additional metadata source, but treat it as unofficial and
  not guaranteed; the official-site hybrid path remains primary for audio.

## Resilience notes

- Wrap all extraction in defensive try/except; never let one missing field crash
  the whole conference parse.
- When the content API path fails, log it and fall back to HTML; when both fail
  for a talk, skip-and-report.
- Cache catalog results (NFR-3) so building the UI doesn't re-hit the source.
