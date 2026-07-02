"""Fetch MP3 bytes from a remote URL (see docs/06 media/downloader)."""

from __future__ import annotations

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.errors import RobotsDisallowed
from app.http_client import get_http_client
from app.source.politeness import get_semaphore, is_allowed, polite_delay, respect_retry_after

logger = logging.getLogger(__name__)


class _Retryable(Exception):
    pass


@retry(
    retry=retry_if_exception_type(_Retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _get_bytes(url: str) -> bytes:
    client = get_http_client()
    if not await is_allowed(client, url):
        raise RobotsDisallowed(f"robots.txt disallows fetching {url}")

    async with get_semaphore():
        await polite_delay()
        try:
            response = await client.get(url, follow_redirects=True)
        except httpx.RequestError as exc:
            logger.warning("MP3 fetch error for %s: %s", url, exc)
            raise _Retryable() from exc

    if response.status_code == 429:
        await respect_retry_after(response)
        raise _Retryable()
    if response.status_code >= 500:
        raise _Retryable()
    if response.status_code != 200:
        raise RuntimeError(f"Unexpected status {response.status_code} for {url}")
    return response.content


async def fetch_mp3(url: str) -> bytes:
    """Download an MP3 from `url` and return its bytes."""
    try:
        return await _get_bytes(url)
    except _Retryable as exc:
        raise RuntimeError(f"Failed to fetch MP3 after retries: {url}") from exc
