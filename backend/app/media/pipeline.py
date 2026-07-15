"""Disk-backed download + tag pipeline (see docs/06 NFR-2).

Keeps full MP3 bytes off the heap during ZIP jobs: stream to a temp file,
tag in place, then let ZipFile.read from disk in chunks.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from app.media.downloader import fetch_mp3_to_file
from app.media.tagger import tag_mp3_file
from app.models import TalkTags


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


async def prepare_tagged_talk_mp3(
    mp3_url: str,
    tags: TalkTags,
    *,
    cover: bytes | None = None,
) -> str:
    """Download an MP3 to a temp file, apply ID3 tags, and return the path.

    The caller is responsible for deleting the file when finished.
    """
    fd, path = tempfile.mkstemp(suffix=".mp3", prefix="gc_talk_")
    os.close(fd)
    try:
        await fetch_mp3_to_file(mp3_url, path)
        # mutagen tagging is synchronous/CPU-bound; run it in a worker thread
        # so concurrent jobs and progress polling aren't blocked.
        await asyncio.to_thread(tag_mp3_file, path, tags, cover)
        return path
    except Exception:
        _safe_unlink(path)
        raise
