# AGENTS.md — Build Instructions for the AI Agent

You are building **GC Downloader**, a web app that downloads General Conference
talks as tagged MP3s and packages them into a ZIP. Read every file in `docs/`
before writing code. This file is the contract for *how* you build it.

## Ground rules

1. **Follow the specs.** The `docs/` folder is authoritative. If something is
   ambiguous, choose the simplest option that satisfies the requirements and
   leave a short note in a `DECISIONS.md` file you create.
2. **Be polite to the source site.** This app fetches public content from
   `churchofjesuschrist.org`. Obey the rate-limiting, caching, and user-agent
   rules in [`docs/11-legal-and-ethics.md`](./docs/11-legal-and-ethics.md).
   Never hammer the server. This is non-negotiable.
3. **Hotlink-safe by design.** Audio and images belong to their owner. Only
   fetch what the user explicitly requested. Do not build a bulk mirror/crawler
   that downloads the entire archive unprompted.
4. **Cross-platform UI.** The frontend must be fully responsive and usable on a
   phone, a tablet, and a desktop. Test layouts at 375px, 768px, and 1280px.
5. **No secrets in code.** Use environment variables. Provide `.env.example`.
6. **Ship something runnable at each milestone.** See
   [`docs/10-build-plan.md`](./docs/10-build-plan.md).

## Repository layout to create

```
gc-downloader/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + routes
│   │   ├── config.py          # settings from env
│   │   ├── models.py          # Pydantic models (see docs/09)
│   │   ├── source/            # data-source layer (see docs/05)
│   │   │   ├── catalog.py     # list conferences/sessions/talks
│   │   │   ├── content_api.py # internal study API client
│   │   │   ├── scraper.py     # HTML fallback
│   │   │   └── cache.py       # short-TTL cache
│   │   ├── media/
│   │   │   ├── downloader.py  # fetch mp3 bytes
│   │   │   ├── tagger.py      # mutagen ID3 tagging
│   │   │   └── packager.py    # streaming zip
│   │   └── jobs/              # async job tracking (see docs/06)
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                   # Next.js App Router
│   ├── components/
│   ├── lib/                   # API client
│   ├── package.json
│   └── .env.example
├── docs/                      # (already provided — read these)
├── DECISIONS.md               # you create: log non-obvious choices
└── README.md
```

## Definition of done

- A user can open the site on a phone or desktop, see a live list of
  conferences, pick one or more sessions (or "Select all"), choose a language,
  click download, and receive a ZIP of correctly tagged MP3s organized by
  session.
- New conferences appear automatically without code changes.
- The backend never blocks indefinitely and reports progress for large jobs.
- Errors (a talk with no audio, a network hiccup) are handled gracefully and
  surfaced to the user without failing the whole batch.

## What to verify before declaring success

- Open a produced MP3 in a media player and confirm Artist/Album/Title/Track/
  cover art are populated.
- Confirm the ZIP folder structure matches [`docs/02-requirements.md`](./docs/02-requirements.md).
- Confirm a non-English language selection produces talks in that language.
- Confirm "Select all" across a full conference works end to end.
