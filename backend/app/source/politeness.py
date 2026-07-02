"""Shared politeness primitives (see docs/06 "Concurrency & politeness", docs/11).

Every outbound request to the source site — content API, HTML scraper, and
audio downloader alike — funnels through this module so that:

  1. `MAX_CONCURRENCY` is a true *global* cap across all three fetchers, not a
     per-module cap that could triple the effective concurrency.
  2. `REQUEST_DELAY_MS` jitter is applied consistently everywhere.
  3. `Retry-After` (on HTTP 429) is honored everywhere a 429 can occur.
  4. `robots.txt` is checked (and cached) before fetching any path.
"""

from __future__ import annotations

import asyncio
import email.utils
import logging
import random
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── One global gate for ALL outbound source requests ─────────────────────────
_semaphore = asyncio.Semaphore(settings.max_concurrency)


def get_semaphore() -> asyncio.Semaphore:
    return _semaphore


async def polite_delay() -> None:
    """Small jittered delay applied before every outbound request."""
    base = settings.request_delay_ms / 1000.0
    await asyncio.sleep(base + random.uniform(0, base))


# Cap how long we'll ever wait on a single Retry-After value so one
# uncooperative response can't stall a whole job indefinitely.
_MAX_RETRY_AFTER_S = 30.0


def _parse_retry_after(value: str) -> float | None:
    """Parse a Retry-After header value (either delay-seconds or an HTTP-date)."""
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    delta = (parsed - email.utils.parsedate_to_datetime(email.utils.formatdate())).total_seconds()
    return max(delta, 0.0)


async def respect_retry_after(response: httpx.Response) -> None:
    """On a 429, sleep for the server's requested Retry-After (docs/11 rule 4)."""
    header = response.headers.get("Retry-After")
    if not header:
        return
    seconds = _parse_retry_after(header)
    if seconds is None:
        return
    wait_s = min(seconds, _MAX_RETRY_AFTER_S)
    logger.info("Honoring Retry-After: sleeping %.1fs before retrying", wait_s)
    await asyncio.sleep(wait_s)


# ── robots.txt (docs/11 rule 2) ───────────────────────────────────────────────
# Cached per-host so we only fetch each site's robots.txt once per process.
_robots_cache: dict[str, RobotFileParser] = {}
_robots_lock = asyncio.Lock()


async def _get_parser(client: httpx.AsyncClient, base: str) -> RobotFileParser:
    if base in _robots_cache:
        return _robots_cache[base]
    async with _robots_lock:
        if base in _robots_cache:
            return _robots_cache[base]
        parser = RobotFileParser()
        parser.set_url(f"{base}/robots.txt")
        try:
            resp = await client.get(f"{base}/robots.txt", timeout=10)
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
            else:
                # No robots.txt (or inaccessible) — convention treats this as
                # "no restrictions" rather than blocking everything.
                parser.parse([])
        except httpx.HTTPError as exc:
            logger.warning("Could not fetch robots.txt for %s: %s", base, exc)
            parser.parse([])
        _robots_cache[base] = parser
        return parser


async def is_allowed(client: httpx.AsyncClient, url: str) -> bool:
    """Check whether our User-Agent may fetch `url` per that host's robots.txt."""
    parsed = urlsplit(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    try:
        parser = await _get_parser(client, base)
        return parser.can_fetch(settings.http_user_agent, url)
    except Exception as exc:  # noqa: BLE001 — never let a robots check crash a fetch
        logger.warning("robots.txt check failed for %s: %s", url, exc)
        return True
