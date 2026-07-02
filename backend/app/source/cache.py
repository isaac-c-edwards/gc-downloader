"""Short-TTL cache for catalog/content responses (see docs/06 NFR-3).

Keyed by (uri, lang). Audio bytes are intentionally NOT cached in v1.
"""

from __future__ import annotations

import asyncio
from typing import Any

from cachetools import TTLCache

from app.config import settings

_cache: TTLCache[tuple[str, str], Any] = TTLCache(
    maxsize=settings.catalog_cache_maxsize, ttl=settings.catalog_ttl
)
_lock = asyncio.Lock()


async def get(uri: str, lang: str) -> Any | None:
    async with _lock:
        return _cache.get((uri, lang))


async def set(uri: str, lang: str, value: Any) -> None:
    async with _lock:
        _cache[(uri, lang)] = value


async def clear() -> None:
    async with _lock:
        _cache.clear()
