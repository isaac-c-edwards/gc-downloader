# 01 — Project Overview

## Title

**GC Downloader**

## Summary

GC Downloader is a full-stack, cross-platform web application that automates the
aggregation, tagging, and packaging of General Conference audio for offline
listening. A user selects one or more conference sessions (for example, "April
2026 — Saturday Morning Session"), optionally chooses a language, and clicks
download. The backend locates the official MP3 files and their metadata,
downloads the audio, injects accurate ID3 tags (speaker as Artist, talk title as
Track, conference as Album, with cover art), and bundles everything into a single
ZIP organized into folders by session.

## Problem statement

General Conference talks are freely available on the official website, but
downloading them for offline use is tedious:

- Each talk must be downloaded one at a time through a multi-click menu.
- The downloaded files often lack clean, consistent metadata, so they display
  poorly in phone music/podcast apps (wrong or missing artist, title, album, art).
- There is no built-in "download this whole session/conference as one bundle"
  option.

This matters most for people who want to listen on a phone **without using
cellular data** — they need the files on-device ahead of time, neatly tagged.

## Goals

1. Let a user browse the full, always-current list of conferences and sessions.
2. Let the user select sessions **individually**, or **Select all**, for download.
3. Support **multiple languages** via a language selector.
4. Produce MP3s with **accurate ID3 metadata and cover art**.
5. Deliver a single **ZIP organized by session** that is easy to load onto a phone.
6. **Automatically detect new conferences** as soon as they're published — no
   manual updates, no hardcoded dates.
7. Work well on **phone, tablet, and desktop** browsers.

## Non-goals (v1)

- No user accounts, login, or saved preferences across devices.
- No streaming/playback inside the app (it's a downloader, not a player).
- No editing of talk text/transcripts.
- No re-hosting or permanent storage of audio on our servers (fetch on demand).

## Target users

- The primary user: someone who wants conference audio on their phone for
  offline listening (commutes, travel, areas with no signal).
- Secondary: anyone who wants a tidy, well-tagged local archive of sessions.

## Success criteria

- A non-technical user can go from "open the site" to "ZIP of tagged MP3s on my
  phone" in under a minute of interaction (excluding download time).
- Produced files show correct Artist/Title/Album/Track/art in a stock phone media
  app.
- The newest conference is selectable within the same day the Church publishes it,
  with zero code changes.

## Origin

The idea came from a friend's request: *"a program that could download all of the
recent general conferences as MP3s with accurate tags and labels and make them
into a file I can put on my phone for when I don't have data."* GC Downloader is
the answer to exactly that.
