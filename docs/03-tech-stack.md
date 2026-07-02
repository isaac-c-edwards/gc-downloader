# 03 — Tech Stack

The stack is chosen for two reasons: (1) it's the right tool for scraping + media
processing + file delivery, and (2) it's extremely well represented in AI training
data, so an AI agent can generate accurate, idiomatic code for it.

## Backend — Python + FastAPI

- **Python** is the industry standard for web data extraction and media
  manipulation. The ecosystem for HTTP, HTML parsing, and audio tagging is mature.
- **FastAPI** gives modern async routing, automatic request/response validation
  via Pydantic, and auto-generated OpenAPI docs — all things that make the API
  contract explicit and easy for an AI to implement correctly.
- **Uvicorn** as the ASGI server.

### Backend libraries

| Concern | Library | Why |
| --- | --- | --- |
| HTTP requests | `httpx` | Async, HTTP/2, connection pooling, timeouts — ideal for polite concurrent fetching. |
| HTML parsing (fallback) | `selectolax` (primary) or `beautifulsoup4` | `selectolax` is very fast; `beautifulsoup4` is the most AI-familiar fallback. Implement behind one interface. |
| MP3 tagging | `mutagen` | The premier ID3v2 library; full control over Title/Artist/Album/Track/cover art. |
| ZIP streaming | `zipstream-ng` | Streams a ZIP to the client without buffering the whole archive in memory (satisfies NFR-2). |
| Settings | `pydantic-settings` | Typed config from environment variables. |
| Retry/backoff | `tenacity` | Clean retry policy for transient network errors. |
| Caching | `cachetools` (in-process TTL) or Redis (optional) | Short-TTL catalog cache (NFR-3). Start in-process; Redis only if scaling. |

## Frontend — Next.js (React) + Tailwind CSS

- **Next.js (App Router)** is the most widely used React framework; AI tools
  (v0, Claude, etc.) generate complete Next.js components reliably.
- **React** component model maps cleanly to the UI (conference list → session
  list → talk list → selection summary).
- **Tailwind CSS** keeps styling text-based and responsive-by-default, which is
  exactly what AI generates well and what makes cross-device layouts easy.

### Frontend libraries

| Concern | Library | Why |
| --- | --- | --- |
| Data fetching/cache | `@tanstack/react-query` | Caches the conference catalog, handles loading/error states cleanly. |
| Icons | `lucide-react` | Lightweight, consistent icon set. |
| UI primitives (optional) | `shadcn/ui` | Accessible, Tailwind-native components (checkboxes, accordions, buttons). |
| State (light) | React state / `zustand` (optional) | Selection state is simple; only add `zustand` if it grows. |

## Hosting / deployment

- **Frontend:** Vercel (first-class Next.js host, free tier, deploys from GitHub).
- **Backend:** Render, Railway, or Fly.io (container/Python support, free/cheap
  tier, deploys from GitHub).
- **Important:** free tiers enforce request timeouts. Large downloads therefore
  use the **async job + streaming** pattern (`docs/06`, `docs/07`) so the initial
  request returns fast and the ZIP is streamed.

## Why not a native mobile app?

A responsive web app is cross-platform by default (phone/tablet/desktop) and
avoids App Store / Play Store review, file-permission, and distribution friction.
The user wanted it to "run on phones or PC or tablets" and "be compatible with
all" — a responsive web app is the most direct path to that.

## Language/runtime versions (targets)

- Python 3.11+
- Node.js 20 LTS+
- Next.js 14+ (App Router)
- Tailwind CSS 3+
