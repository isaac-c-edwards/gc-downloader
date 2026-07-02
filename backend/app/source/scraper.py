"""HTML fallback scraper (see docs/05).

Used when the content API path fails or to enumerate conferences from the public
landing page. Fetches a human page and returns its raw HTML.
"""

from __future__ import annotations

import logging
import re

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.errors import ContentUnavailable, RobotsDisallowed
from app.http_client import get_http_client
from app.source.politeness import get_semaphore, is_allowed, polite_delay, respect_retry_after

logger = logging.getLogger(__name__)

# Matches conference links like /study/general-conference/2026/04
_CONFERENCE_LINK_RE = re.compile(r"/general-conference/(\d{4})/(\d{2})\b")


class _Retryable(Exception):
    pass


@retry(
    retry=retry_if_exception_type(_Retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def _get(path: str, params: dict[str, str]) -> httpx.Response:
    client = get_http_client()
    full_url = f"{settings.source_base_url}{path}"
    if not await is_allowed(client, full_url):
        raise RobotsDisallowed(f"robots.txt disallows fetching {path}")

    async with get_semaphore():
        await polite_delay()
        try:
            response = await client.get(path, params=params)
        except httpx.RequestError as exc:
            logger.warning("scraper request error for %s: %s", path, exc)
            raise _Retryable() from exc

    if response.status_code == 429:
        await respect_retry_after(response)
        raise _Retryable()
    if response.status_code >= 500:
        raise _Retryable()
    return response


async def get_html(uri: str, lang: str) -> str:
    """Fetch the rendered study page HTML for a `uri`."""
    path = f"/study{uri}"
    try:
        response = await _get(path, {"lang": lang})
    except _Retryable as exc:
        raise ContentUnavailable(f"Source unreachable for {uri}") from exc
    if response.status_code != 200:
        raise ContentUnavailable(f"Unexpected status {response.status_code} for {uri}")
    return response.text


async def list_conference_links(lang: str) -> list[tuple[int, int]]:
    """Return (year, month) pairs surfaced on the GC landing page, newest first."""
    html = await get_html("/general-conference", lang)
    seen: set[tuple[int, int]] = set()
    for match in _CONFERENCE_LINK_RE.finditer(html):
        seen.add((int(match.group(1)), int(match.group(2))))
    return sorted(seen, reverse=True)
