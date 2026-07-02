"""Internal study content API client (primary data path, see docs/05).

Endpoint:
    GET /study/api/v3/language-pages/type/content?lang={lang}&uri={uri}

Returns parsed JSON. Retries transient network/5xx errors. Raises
ContentNotFound on a genuine 404, or ContentUnavailable for other hard
failures, so callers can fall back, skip, or report "not available".
"""

from __future__ import annotations

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.errors import ContentNotFound, ContentUnavailable, RobotsDisallowed
from app.http_client import get_http_client
from app.source.politeness import get_semaphore, is_allowed, polite_delay, respect_retry_after

logger = logging.getLogger(__name__)

CONTENT_PATH = "/study/api/v3/language-pages/type/content"


class _Retryable(Exception):
    pass


@retry(
    retry=retry_if_exception_type(_Retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def _request(uri: str, lang: str) -> httpx.Response:
    client = get_http_client()
    params = {"lang": lang, "uri": uri}
    full_url = f"{settings.source_base_url}{CONTENT_PATH}?lang={lang}&uri={uri}"
    if not await is_allowed(client, full_url):
        raise RobotsDisallowed(f"robots.txt disallows fetching {uri}")

    async with get_semaphore():
        await polite_delay()
        try:
            response = await client.get(CONTENT_PATH, params=params)
        except httpx.RequestError as exc:
            logger.warning("content_api request error for %s: %s", uri, exc)
            raise _Retryable() from exc

    if response.status_code == 429:
        logger.warning("content_api rate-limited for %s", uri)
        await respect_retry_after(response)
        raise _Retryable()
    if response.status_code >= 500:
        logger.warning("content_api transient status %s for %s", response.status_code, uri)
        raise _Retryable()

    return response


async def get_content(uri: str, lang: str) -> dict:
    """Fetch the content-API JSON for a study `uri` in `lang`.

    Raises ContentNotFound on a genuine 404 (this uri+lang combo doesn't
    exist), or ContentUnavailable for anything else (network/5xx/robots/
    retries exhausted).
    """
    try:
        response = await _request(uri, lang)
    except _Retryable as exc:
        raise ContentUnavailable(f"Source unreachable for {uri}") from exc

    if response.status_code == 404:
        raise ContentNotFound(f"Not found: {uri}")
    if response.status_code != 200:
        raise ContentUnavailable(f"Unexpected status {response.status_code} for {uri}")

    try:
        return response.json()
    except ValueError as exc:
        raise ContentUnavailable(f"Invalid JSON for {uri}") from exc
