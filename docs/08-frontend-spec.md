# 08 — Frontend Spec

Next.js (App Router) + Tailwind CSS. Fully responsive: phone (≈375px), tablet
(≈768px), desktop (≥1280px). Talks to the backend only (see `docs/07`).

## Design principles

- **Mobile-first.** Design for the phone, enhance for larger screens.
- **One clear primary action:** select → download.
- **Always show selection state** so the user knows what they'll get.
- Clean, modern, friendly. Generous touch targets (≥44px) on mobile.

## Screens / layout

Single-page experience with three logical regions:

```
┌───────────────────────────────────────────────┐
│  Header: "GC Downloader"  [Language ▾]         │
├───────────────────────────────────────────────┤
│  Conference list (accordion)                   │
│   ▸ April 2026 General Conference   [Select all]│
│       ☑ Saturday Morning Session               │
│           ☑ Welcome Message — Speaker          │
│           ☐ Talk Title — Speaker               │
│       ☐ Saturday Afternoon Session             │
│   ▸ October 2025 General Conference [Select all]│
│   ...                                           │
├───────────────────────────────────────────────┤
│  Sticky selection bar:                         │
│   "3 sessions · 47 talks"     [ Download ZIP ] │
└───────────────────────────────────────────────┘
```

### Header
- App title/logo.
- **Language selector** (dropdown) populated from `GET /api/languages`,
  defaulting to English. Changing language re-fetches catalog/conference data for
  that language.

### Conference list (accordion)
- Loaded from `GET /api/catalog` (newest first). Each conference is a collapsible
  row showing its name and image thumbnail, plus a **"Select all"** toggle that
  selects every session/talk in that conference.
- Expanding a conference lazy-loads `GET /api/conferences/{id}` and renders its
  **sessions**. Each session:
  - Has a checkbox (selects/deselects the whole session).
  - Expands to show its **talks** (title — speaker), each with its own checkbox.
- Tri-state checkboxes: a session shows "indeterminate" when only some of its
  talks are selected.

### Sticky selection bar
- Always visible at the bottom (mobile) / bottom or side (desktop).
- Shows running counts (sessions + talks). Satisfies FR-3.
- **Download ZIP** button — disabled when nothing is selected.

### Download flow & progress
- On click, send the selection (`docs/07`).
  - **Mode A:** trigger a streamed file download; show a "Preparing your
    download…" overlay; on completion, show a toast and (from the in-zip
    `summary.json` is not readable client-side, so) display the count requested.
  - **Mode B (recommended for hosted):** create a job, then poll and render a
    progress bar (`completed / total`) with a live list of skipped talks; when
    `download_ready`, auto-start the download and show a success summary.
- Always surface a final summary: "Downloaded 45 of 47 talks (2 skipped — not
  available in Español)."

## Components

| Component | Responsibility |
| --- | --- |
| `LanguageSelect` | Dropdown bound to `/api/languages`; updates global language. |
| `ConferenceList` | Renders catalog; manages expand/lazy-load. |
| `ConferenceRow` | One conference; "Select all"; thumbnail; expands sessions. |
| `SessionRow` | Checkbox (tri-state); expands talks. |
| `TalkRow` | Checkbox + title + speaker. |
| `SelectionBar` | Sticky summary + Download button. |
| `ProgressModal` | Job progress (Mode B) / preparing overlay (Mode A). |
| `SummaryToast` | Final success/skip report. |

## State management

- Selection state: a normalized structure keyed by talk id with derived session/
  conference roll-ups (use React state or `zustand` if it grows). Must support:
  - select/deselect a talk,
  - select/deselect a whole session,
  - "Select all" for a conference,
  - tri-state derivation,
  - running totals.
- Server data: `@tanstack/react-query` for `/api/catalog`, `/api/conferences/{id}`,
  `/api/languages` (cached; refetch on language change).

## Empty / loading / error states

- Loading skeletons for catalog and session expansion.
- Friendly error if the source is unreachable (`502`) with a retry button.
- "Nothing selected yet" hint in the selection bar.

## Configuration

- `NEXT_PUBLIC_API_BASE_URL` — backend base URL.
- `NEXT_PUBLIC_DELIVERY_MODE` — `direct` (A) or `job` (B); default `job` for
  hosted, `direct` for local. Provide `.env.example`.

## Accessibility & polish

- All interactive elements keyboard-focusable with labels/ARIA (checkboxes,
  accordion toggles).
- Respect `prefers-reduced-motion`.
- Color contrast AA. Dark-mode friendly (Tailwind `dark:` optional but nice).
