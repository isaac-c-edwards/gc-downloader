"""Internal study content API client (primary data path, see docs/05).

Endpoint:
    GET /study/api/v3/language-pages/type/content?lang={lang}&uri={uri}

Returns parsed JSON. Retries transient network/5xx errors. Raises
ContentUnavailable on hard failure so callers can fall back or skip.
"""

from __future__ import annotations

import asyncio
import logging
import random

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.errors import ContentUnavailable
from app.http_client import get_http_client

logger = logging.getLogger(__name__)

CONTENT_PATH = "/study/api/v3/language-pages/type/content"

# One shared gate for all outbound source requests (politeness, docs/11).
_semaphore = asyncio.Semaphore(settings.max_concurrency)


class _Retryable(Exception):
    pass


async def _polite_delay() -> None:
    base = settings.request_delay_ms / 1000.0
    await asyncio.sleep(base + random.uniform(0, base))


@retry(
    retry=retry_if_exception_type(_Retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def _request(uri: str, lang: str) -> httpx.Response:
    client = get_http_client()
    params = {"lang": lang, "uri": uri}
    async with _semaphore:
        await _polite_delay()
        try:
            response = await client.get(CONTENT_PATH, params=params)
        except httpx.RequestError as exc:
            logger.warning("content_api request error for %s: %s", uri, exc)
            raise _Retryable() from exc

    if response.status_code == 429 or response.status_code >= 500:
        logger.warning("content_api transient status %s for %s", response.status_code, uri)
        raise _Retryable()

    return response


async def get_content(uri: str, lang: str) -> dict:
    """Fetch the content-API JSON for a study `uri` in `lang`.

    Raises ContentUnavailable on 404 or after retries are exhausted.
    """
    try:
        response = await _request(uri, lang)
    except _Retryable as exc:
        raise ContentUnavailable(f"Source unreachable for {uri}") from exc

    if response.status_code == 404:
        raise ContentUnavailable(f"Not found: {uri}")
    if response.status_code != 200:
        raise ContentUnavailable(f"Unexpected status {response.status_code} for {uri}")

    try:
        return response.json()
    except ValueError as exc:
        raise ContentUnavailable(f"Invalid JSON for {uri}") from exc
