from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.config import Settings

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client has not been initialized")
    return _client


async def init_http_client(settings: Settings) -> httpx.AsyncClient:
    global _client
    _client = httpx.AsyncClient(
        base_url=settings.source_base_url,
        headers={"User-Agent": settings.http_user_agent},
        timeout=settings.http_timeout,
        follow_redirects=True,
    )
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
