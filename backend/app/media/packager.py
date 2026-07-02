"""Streaming ZIP packager (see docs/06, NFR-2).

Builds a ZIP on the fly using zipstream-ng so no full archive is held
in memory. Each talk is fetched, tagged, and written as it comes in.
A summary.json is appended as the final entry.
"""

from __future__ import annotations

import asyncio
import logging
import os

import zipstream

from app.config import settings
from app.http_client import get_http_client
from app.languages import normalize as normalize_lang
from app.media.naming import zip_filename, zip_path
from app.media.pipeline import prepare_tagged_talk_mp3
from app.models import ConferenceDetail, DownloadRequest, Session, Skip, Talk, TalkTags
from app.source.catalog import get_conference, resolve_talk_media
from app.source.politeness import get_semaphore, is_allowed, polite_delay

logger = logging.getLogger(__name__)

# Language code → display name map for ZIP filename
_LANG_NAMES: dict[str, str] = {
    "eng": "English", "spa": "Español", "por": "Português",
    "fra": "Français", "deu": "Deutsch", "ita": "Italiano",
    "jpn": "日本語", "kor": "한국어", "zho": "中文",
    "rus": "Русский", "tgl": "Tagalog", "smo": "Gagana Samoa",
    "ton": "Lea Faka-Tonga",
}


def _lang_display(lang: str) -> str:
    return _LANG_NAMES.get(lang, lang)


async def _fetch_cover(url: str | None) -> bytes | None:
    """Fetch cover art bytes, gated by the same semaphore/robots rules as
    every other outbound request (docs/06, docs/11) — cover images are not a
    special case just because they're small."""
    if not url:
        return None
    try:
        client = get_http_client()
        if not await is_allowed(client, url):
            logger.info("robots.txt disallows fetching cover image %s", url)
            return None
        async with get_semaphore():
            await polite_delay()
            r = await client.get(url, follow_redirects=True)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def _resolve_selected_talks(
    detail: ConferenceDetail, sel_session_ids: set[str], sel_talk_ids: set[str]
) -> list[tuple[Session, Talk]]:
    """Return (session, talk) pairs that match the selection."""
    results: list[tuple[Session, Talk]] = []
    for session in detail.sessions:
        for talk in session.talks:
            if session.id in sel_session_ids or talk.id in sel_talk_ids:
                results.append((session, talk))
    return results


async def resolve_single_talk(request: DownloadRequest):
    """Resolve exactly one talk from the request.

    Returns (tagged_mp3_bytes, mp3_filename) or raises if anything goes wrong.
    Used when the selection contains exactly one talk so we can skip the ZIP.
    """
    lang = normalize_lang(request.lang)
    sel = request.selection[0]
    detail = await get_conference(sel.conference_id, lang)

    sel_sessions = set(sel.session_ids or [])
    sel_talks = set(sel.talk_ids or [])
    pairs = _resolve_selected_talks(detail, sel_sessions, sel_talks)
    if not pairs:
        raise ValueError("No talks resolved from selection")

    session, talk = pairs[0]
    media = await resolve_talk_media(talk.uri, talk.id, lang)
    cover = await _fetch_cover(media.image_url)

    tags = TalkTags(
        title=talk.title,
        artist=talk.speaker,
        album=detail.name,
        track=f"{talk.order}/{len(session.talks)}",
        disc=f"{session.order}/{len(detail.sessions)}",
        year=detail.year,
    )
    mp3_path = await prepare_tagged_talk_mp3(media.mp3_url, tags, cover=cover)
    try:
        with open(mp3_path, "rb") as f:
            tagged = f.read()
    finally:
        try:
            os.unlink(mp3_path)
        except OSError:
            pass

    from app.media.naming import safe_filename
    speaker_part = f" - {talk.speaker}" if talk.speaker else ""
    filename = safe_filename(f"{talk.title}{speaker_part}") + ".mp3"
    return tagged, filename


async def stream_zip(request: DownloadRequest):
    """Async generator that yields ZIP bytes for the given selection."""
    lang = normalize_lang(request.lang)

    # ── 1. Resolve all selected conferences + talks ──────────────────────────
    items: list[tuple[ConferenceDetail, Session, Talk]] = []
    for sel in request.selection:
        try:
            detail = await get_conference(sel.conference_id, lang)
        except Exception as exc:
            logger.error("Cannot load conference %s: %s", sel.conference_id, exc)
            continue

        sel_sessions = set(sel.session_ids or [])
        sel_talks = set(sel.talk_ids or [])
        pairs = _resolve_selected_talks(detail, sel_sessions, sel_talks)
        for session, talk in pairs:
            items.append((detail, session, talk))

    if not items:
        raise ValueError("No talks resolved from selection")

    # ── 2. Build the ZIP ─────────────────────────────────────────────────────
    zs = zipstream.ZipStream(compress_type=zipstream.ZIP_STORED)
    successes = 0
    skips: list[Skip] = []
    conf_names: list[str] = []

    # Group by conference for proper per-conference folder naming
    conf_details: dict[str, ConferenceDetail] = {
        d.id: d for d, _, _ in items
    }
    for d in conf_details.values():
        if d.name not in conf_names:
            conf_names.append(d.name)

    # For zero-padding we need per-session talk totals
    session_talk_totals: dict[str, int] = {}
    session_totals: dict[str, int] = {}
    for detail, session, _ in items:
        session_talk_totals[session.id] = len(session.talks)
        session_totals[detail.id] = len(detail.sessions)

    async def fetch_talk(
        detail: ConferenceDetail, session: Session, talk: Talk
    ) -> tuple[str, str] | Skip:
        """Fetch + tag one talk to a temp file. Returns (zip_path, mp3_path) or Skip.
        Concurrency is governed by the semaphores inside resolve_talk_media / fetch.
        """
        try:
            media = await resolve_talk_media(talk.uri, talk.id, lang)
        except Exception as exc:
            logger.warning("No media for %s: %s", talk.id, exc)
            return Skip(talk_id=talk.id, reason=str(exc))

        cover = await _fetch_cover(media.image_url)

        tags = TalkTags(
            title=talk.title,
            artist=talk.speaker,
            album=detail.name,
            track=f"{talk.order}/{session_talk_totals.get(session.id, talk.order)}",
            disc=f"{session.order}/{session_totals.get(detail.id, session.order)}",
            year=detail.year,
        )
        try:
            mp3_path = await prepare_tagged_talk_mp3(
                media.mp3_url, tags, cover=cover
            )
        except Exception as exc:
            logger.warning("MP3 fetch/tag failed for %s: %s", talk.id, exc)
            return Skip(talk_id=talk.id, reason=f"Download failed: {exc}")

        path = zip_path(
            conf_id=detail.id,
            conf_name=detail.name,
            session_order=session.order,
            session_name=session.name,
            session_total=session_totals.get(detail.id, 1),
            talk_order=talk.order,
            talk_title=talk.title,
            talk_speaker=talk.speaker,
            talk_total=session_talk_totals.get(session.id, 1),
        )
        return path, mp3_path

    # ── 3. Fetch + write in bounded batches (NFR-2) ───────────────────────
    # Talks are tagged on disk; only one batch of temp files is read into the
    # zipstream at a time before yielding bytes downstream.
    batch_size = max(1, settings.max_concurrency)
    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start : batch_start + batch_size]
        results = await asyncio.gather(
            *[fetch_talk(detail, session, talk) for detail, session, talk in batch],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException):
                logger.error("Unexpected gather exception: %s", result)
                skips.append(Skip(talk_id="unknown", reason=str(result)))
            elif isinstance(result, Skip):
                skips.append(result)
            else:
                path, mp3_path = result
                try:
                    with open(mp3_path, "rb") as f:
                        zs.add(f.read(), arcname=path)
                    successes += 1
                finally:
                    try:
                        os.unlink(mp3_path)
                    except OSError:
                        pass

        # Drain everything queued so far (writes+yields actual zip bytes),
        # WITHOUT finalizing the archive — zipstream-ng only writes the
        # closing central directory when footer()/finalize() runs, so
        # all_files() lets us flush a batch and keep adding more afterward.
        for chunk in zs.all_files():
            yield chunk

    # Close out the archive once every batch has been written.
    for chunk in zs.footer():
        yield chunk

    logger.info(
        "ZIP done: %d succeeded, %d skipped of %d total",
        successes, len(skips), len(items),
    )


def make_zip_filename(request: DownloadRequest) -> str:
    lang = normalize_lang(request.lang)
    conf_names = [sel.conference_id for sel in request.selection]
    return zip_filename(conf_names, _lang_display(lang))
