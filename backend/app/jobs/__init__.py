"""Async job store and pipeline runner (Mode B — see docs/06, docs/07).

Jobs are in-memory for v1 (single instance). Each job writes its output
(tagged MP3 or ZIP) to a temp file, then marks download_ready = True.
The temp file is streamed on demand and cleaned up after TTL_SECONDS.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass, field

from app.languages import normalize as normalize_lang
from app.media.downloader import fetch_mp3
from app.media.naming import safe_filename, zip_filename, zip_path
from app.media.packager import _fetch_cover, _lang_display, _resolve_selected_talks
from app.media.tagger import tag_mp3
from app.models import DownloadRequest, TalkTags
from app.source.catalog import get_conference, resolve_talk_media

logger = logging.getLogger(__name__)

TTL_SECONDS = 3600  # evict jobs + temp files after 1 hour


@dataclass
class Job:
    job_id: str
    request: DownloadRequest
    state: str = "queued"       # queued | running | done | error
    total: int = 0
    completed: int = 0
    skipped: list = field(default_factory=list)
    download_ready: bool = False
    temp_path: str | None = None
    filename: str = "gc-downloader.zip"
    content_type: str = "application/zip"
    created_at: float = field(default_factory=time.time)
    error_msg: str | None = None


_jobs: dict[str, Job] = {}


# ── Public store API ──────────────────────────────────────────────────────────

def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def create_job(request: DownloadRequest, total: int) -> Job:
    _evict_old()
    job = Job(job_id=str(uuid.uuid4()), request=request, total=total)
    _jobs[job.job_id] = job
    return job


def _evict_old() -> None:
    cutoff = time.time() - TTL_SECONDS
    expired = [jid for jid, j in list(_jobs.items()) if j.created_at < cutoff]
    for jid in expired:
        j = _jobs.pop(jid, None)
        if j and j.temp_path:
            _safe_unlink(j.temp_path)


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


# ── Resolution helper (shared with POST /api/jobs) ───────────────────────────

async def resolve_total(request: DownloadRequest) -> int:
    """Resolve all selections to get an exact talk count (catalog is cached)."""
    lang = normalize_lang(request.lang)
    total = 0
    for sel in request.selection:
        try:
            detail = await get_conference(sel.conference_id, lang)
        except Exception:
            continue
        pairs = _resolve_selected_talks(
            detail, set(sel.session_ids or []), set(sel.talk_ids or [])
        )
        total += len(pairs)
    return total


# ── Background runner ─────────────────────────────────────────────────────────

async def run_job(job_id: str) -> None:
    """Run the full download pipeline for a job and write output to a temp file."""
    job = _jobs.get(job_id)
    if not job:
        return

    job.state = "running"
    lang = normalize_lang(job.request.lang)

    try:
        # ── 1. Resolve all (detail, session, talk) triples ────────────────────
        items: list = []
        for sel in job.request.selection:
            try:
                detail = await get_conference(sel.conference_id, lang)
            except Exception as exc:
                logger.error("Job %s: cannot load %s: %s", job_id, sel.conference_id, exc)
                continue
            pairs = _resolve_selected_talks(
                detail, set(sel.session_ids or []), set(sel.talk_ids or [])
            )
            for session, talk in pairs:
                items.append((detail, session, talk))

        if not items:
            job.state = "error"
            job.error_msg = "No talks resolved from selection."
            return

        job.total = len(items)

        # ── 2. Build per-session / per-conference totals for ID3 TRCK/TPOS ───
        session_talk_totals = {s.id: len(s.talks) for _, s, _ in items}
        session_totals: dict[str, int] = {}
        for d, _, _ in items:
            session_totals[d.id] = len(d.sessions)

        is_single = len(items) == 1
        suffix = ".mp3" if is_single else ".zip"
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="gc_job_")
        os.close(fd)
        job.temp_path = temp_path

        # ── 3a. Single talk → write tagged MP3 directly ───────────────────────
        if is_single:
            job.content_type = "audio/mpeg"
            detail, session, talk = items[0]
            try:
                media = await resolve_talk_media(talk.uri, talk.id, lang)
                mp3_bytes = await fetch_mp3(media.mp3_url)
                cover = await _fetch_cover(media.image_url)
                tags = TalkTags(
                    title=talk.title,
                    artist=talk.speaker,
                    album=detail.name,
                    track=f"{talk.order}/{session_talk_totals.get(session.id, talk.order)}",
                    disc=f"{session.order}/{session_totals.get(detail.id, session.order)}",
                    year=detail.year,
                )
                tagged = tag_mp3(mp3_bytes, tags, cover)
                with open(temp_path, "wb") as f:
                    f.write(tagged)
                job.completed = 1
                speaker_part = f" - {talk.speaker}" if talk.speaker else ""
                job.filename = safe_filename(f"{talk.title}{speaker_part}") + ".mp3"
            except Exception as exc:
                logger.warning("Job %s: single talk failed: %s", job_id, exc)
                job.skipped.append({"talk_id": talk.id, "reason": str(exc)})
                job.filename = "talk.mp3"

        # ── 3b. Multiple talks → build a ZIP ─────────────────────────────────
        else:
            job.content_type = "application/zip"
            conf_names: list[str] = []
            for d, _, _ in items:
                if d.name not in conf_names:
                    conf_names.append(d.name)

            async def fetch_one(detail, session, talk):
                try:
                    media = await resolve_talk_media(talk.uri, talk.id, lang)
                    mp3_bytes = await fetch_mp3(media.mp3_url)
                    cover = await _fetch_cover(media.image_url)
                    tags = TalkTags(
                        title=talk.title,
                        artist=talk.speaker,
                        album=detail.name,
                        track=f"{talk.order}/{session_talk_totals.get(session.id, talk.order)}",
                        disc=f"{session.order}/{session_totals.get(detail.id, session.order)}",
                        year=detail.year,
                    )
                    tagged = tag_mp3(mp3_bytes, tags, cover)
                    path = zip_path(
                        conf_id=detail.id, conf_name=detail.name,
                        session_order=session.order, session_name=session.name,
                        session_total=session_totals.get(detail.id, 1),
                        talk_order=talk.order, talk_title=talk.title,
                        talk_speaker=talk.speaker,
                        talk_total=session_talk_totals.get(session.id, 1),
                    )
                    return path, tagged, talk.id, None
                except Exception as exc:
                    logger.warning("Job %s: skipping %s: %s", job_id, talk.id, exc)
                    return None, None, talk.id, str(exc)

            # Use as_completed so job.completed increments as each talk finishes,
            # giving the frontend progress bar smooth live updates.
            #
            # Write each talk to the on-disk ZipFile as soon as it's tagged,
            # instead of buffering every talk's bytes in a list until all are
            # done. Previously `zip_entries` held every tagged MP3 in memory
            # simultaneously before any bytes hit disk — for a full-conference
            # "Select all" that's 45+ full MP3s (hundreds of MB) resident at
            # once. Writing incrementally bounds peak memory to roughly
            # max_concurrency in-flight talks (NFR-2).
            tasks = [asyncio.create_task(fetch_one(d, s, t)) for d, s, t in items]

            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_STORED) as zf:
                for coro in asyncio.as_completed(tasks):
                    path, tagged, talk_id, err = await coro
                    if err:
                        job.skipped.append({"talk_id": talk_id, "reason": err})
                    else:
                        zf.writestr(path, tagged)
                        job.completed += 1

            job.filename = zip_filename(conf_names, _lang_display(lang))

        job.download_ready = True
        job.state = "done"

    except Exception as exc:
        logger.exception("Job %s failed unexpectedly: %s", job_id, exc)
        job.state = "error"
        job.error_msg = str(exc)
        if job.temp_path:
            _safe_unlink(job.temp_path)
            job.temp_path = None
