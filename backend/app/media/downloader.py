"""Fetch MP3 bytes from a remote URL (see docs/06 media/downloader)."""

from __future__ import annotations

import asyncio
import logging
import random

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.http_client import get_http_client

logger = logging.getLogger(__name__)

# Shared semaphore imported from content_api to keep total outbound concurrency
# within the polite cap. We recreate a local one here at the same limit so the
# downloader honours the same ceiling even if called independently.
_semaphore = asyncio.Semaphore(settings.max_concurrency)


class _Retryable(Exception):
    pass


async def _polite_delay() -> None:
    base = settings.request_delay_ms / 1000.0
    await asyncio.sleep(base + random.uniform(0, base * 0.5))


@retry(
    retry=retry_if_exception_type(_Retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _get_bytes(url: str) -> bytes:
    client = get_http_client()
    async with _semaphore:
        await _polite_delay()
        try:
            response = await client.get(url, follow_redirects=True)
        except httpx.RequestError as exc:
            logger.warning("MP3 fetch error for %s: %s", url, exc)
            raise _Retryable() from exc

    if response.status_code == 429 or response.status_code >= 500:
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
