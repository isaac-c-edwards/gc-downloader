"""Fetch MP3 bytes from a remote URL (see docs/06 media/downloader)."""

from __future__ import annotations

import logging
import os

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.errors import RobotsDisallowed
from app.http_client import get_http_client
from app.source.politeness import get_semaphore, is_allowed, polite_delay, respect_retry_after

logger = logging.getLogger(__name__)

_STREAM_CHUNK = 64 * 1024


class _Retryable(Exception):
    pass


def _unlink_quiet(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


@retry(
    retry=retry_if_exception_type(_Retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def fetch_mp3_to_file(url: str, dest: str) -> None:
    """Stream an MP3 from `url` into `dest` on disk."""
    client = get_http_client()
    if not await is_allowed(client, url):
        raise RobotsDisallowed(f"robots.txt disallows fetching {url}")

    async with get_semaphore():
        await polite_delay()
        try:
            async with client.stream("GET", url, follow_redirects=True) as response:
                if response.status_code == 429:
                    await respect_retry_after(response)
                    raise _Retryable()
                if response.status_code >= 500:
                    raise _Retryable()
                if response.status_code != 200:
                    _unlink_quiet(dest)
                    raise RuntimeError(
                        f"Unexpected status {response.status_code} for {url}"
                    )

                with open(dest, "wb") as out:
                    async for chunk in response.aiter_bytes(_STREAM_CHUNK):
                        out.write(chunk)
        except httpx.RequestError as exc:
            _unlink_quiet(dest)
            logger.warning("MP3 fetch error for %s: %s", url, exc)
            raise _Retryable() from exc


async def fetch_mp3(url: str) -> bytes:
    """Download an MP3 from `url` and return its bytes (small selections / tests)."""
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".mp3", prefix="gc_fetch_")
    os.close(fd)
    try:
        await fetch_mp3_to_file(url, path)
        with open(path, "rb") as f:
            return f.read()
    except _Retryable as exc:
        raise RuntimeError(f"Failed to fetch MP3 after retries: {url}") from exc
    finally:
        _unlink_quiet(path)
