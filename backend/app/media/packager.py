"""Streaming ZIP packager (see docs/06, NFR-2).

Builds a ZIP on the fly using zipstream-ng so no full archive is held
in memory. Each talk is fetched, tagged, and written as it comes in.
A summary.json is appended as the final entry.
"""

from __future__ import annotations

import asyncio
import logging

import zipstream

from app.config import settings
from app.languages import normalize as normalize_lang
from app.media.downloader import fetch_mp3
from app.media.naming import zip_filename, zip_path
from app.media.tagger import tag_mp3
from app.models import ConferenceDetail, DownloadRequest, Session, Skip, Talk, TalkTags
from app.source.catalog import get_conference, resolve_talk_media

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
    if not url:
        return None
    try:
        from app.http_client import get_http_client
        client = get_http_client()
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
    mp3_bytes = await fetch_mp3(media.mp3_url)
    cover = await _fetch_cover(media.image_url)

    tags = TalkTags(
        title=talk.title,
        artist=talk.speaker,
        album=detail.name,
        track=f"{talk.order}/{len(session.talks)}",
        disc=f"{session.order}/{len(detail.sessions)}",
        year=detail.year,
    )
    tagged = tag_mp3(mp3_bytes, tags, cover)

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
    ) -> tuple[str, bytes] | Skip:
        """Fetch + tag one talk. Returns (zip_path, bytes) or a Skip on failure.
        Concurrency is governed by the semaphores inside resolve_talk_media / fetch_mp3.
        """
        try:
            media = await resolve_talk_media(talk.uri, talk.id, lang)
        except Exception as exc:
            logger.warning("No media for %s: %s", talk.id, exc)
            return Skip(talk_id=talk.id, reason=str(exc))

        try:
            mp3_bytes = await fetch_mp3(media.mp3_url)
        except Exception as exc:
            logger.warning("MP3 fetch failed for %s: %s", talk.id, exc)
            return Skip(talk_id=talk.id, reason=f"Download failed: {exc}")

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
            tagged = tag_mp3(mp3_bytes, tags, cover)
        except Exception as exc:
            logger.warning("Tagging failed for %s, using untagged: %s", talk.id, exc)
            tagged = mp3_bytes

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
        return path, tagged

    # Fetch all talks concurrently — semaphores inside fetch_mp3 / resolve_talk_media
    # cap actual simultaneous network I/O at settings.max_concurrency.
    # return_exceptions=True ensures one failure never cancels other tasks.
    results = await asyncio.gather(
        *[fetch_talk(detail, session, talk) for detail, session, talk in items],
        return_exceptions=True,
    )
    # Add to ZIP in original order so filenames sort correctly
    for result in results:
        if isinstance(result, BaseException):
            logger.error("Unexpected gather exception: %s", result)
            skips.append(Skip(talk_id="unknown", reason=str(result)))
        elif isinstance(result, Skip):
            skips.append(result)
        else:
            path, tagged = result
            zs.add(tagged, arcname=path)
            successes += 1

    # Yield ZIP chunks
    for chunk in zs:
        yield chunk

    logger.info(
        "ZIP done: %d succeeded, %d skipped of %d total",
        successes, len(skips), len(items),
    )


def make_zip_filename(request: DownloadRequest) -> str:
    lang = normalize_lang(request.lang)
    conf_names = [sel.conference_id for sel in request.selection]
    return zip_filename(conf_names, _lang_display(lang))
