"""List conferences, sessions, and talks (see docs/05, docs/06).

Enumeration strategy (hybrid, see docs/05 FR-1):
  1. Scrape the public landing page to find the newest *published* conference.
  2. Generate the full, predictable April/October cadence from 1971 up to that
     ceiling. This lists the complete archive without probing the server, and
     never shows an unpublished future conference. New conferences appear
     automatically once the landing page surfaces them (raising the ceiling).
"""

from __future__ import annotations

import datetime as _dt
import logging

from app.errors import ContentUnavailable, MediaUnavailable, NotFound
from app.models import Conference, ConferenceDetail, TalkMedia
from app.source import cache, content_api, scraper
from app.source.extractor import find_mp3_url, parse_conference_body

logger = logging.getLogger(__name__)

EARLIEST_YEAR = 1971
CONFERENCE_MONTHS = (4, 10)

_CATALOG_KEY = "__catalog__"

# Localized month names and conference name templates for the catalog list.
# These are approximations used when we haven't fetched the full conference.
# get_conference() uses the actual title from the source API.
_MONTH_BY_LANG: dict[str, dict[int, str]] = {
    "eng": {4: "April",   10: "October"},
    "spa": {4: "Abril",   10: "Octubre"},
    "por": {4: "Abril",   10: "Outubro"},
    "fra": {4: "Avril",   10: "Octobre"},
    "deu": {4: "April",   10: "Oktober"},
    "ita": {4: "Aprile",  10: "Ottobre"},
    "jpn": {4: "4月",     10: "10月"},
    "kor": {4: "4월",     10: "10월"},
    "zho": {4: "四月",    10: "十月"},
    "rus": {4: "Апрель",  10: "Октябрь"},
    "tgl": {4: "Abril",   10: "Oktubre"},
    "smo": {4: "Aperila", 10: "Oketopa"},
    "ton": {4: "ʻEpeleli", 10: "ʻOkatopa"},
}

_NAME_TEMPLATE: dict[str, str] = {
    "eng": "{month} {year} General Conference",
    "spa": "Conferencia General de {month} de {year}",
    "por": "Conferência Geral de {month} de {year}",
    "fra": "Conférence générale d\u2019{month} {year}",
    "deu": "Generalkonferenz {month} {year}",
    "ita": "Conferenza Generale di {month} {year}",
    "jpn": "{year}年{month}大会",
    "kor": "{year}년 {month} 대회",
    "zho": "{year}年{month}大会",
    "rus": "Генеральная Конференция {month} {year}",
    "tgl": "Pangkalahatang Kumperensya {month} {year}",
    "smo": "Koneferenisi Aoao {month} {year}",
    "ton": "Konifelenisi Lahi {month} {year}",
}


def conf_id(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def parse_conf_id(value: str) -> tuple[int, int]:
    try:
        year_s, month_s = value.split("-")
        year, month = int(year_s), int(month_s)
    except (ValueError, AttributeError) as exc:
        raise NotFound(f"Invalid conference id: {value}") from exc
    if month not in CONFERENCE_MONTHS or year < EARLIEST_YEAR:
        raise NotFound(f"Unknown conference: {value}")
    return year, month


def conference_name(year: int, month: int, lang: str = "eng") -> str:
    months = _MONTH_BY_LANG.get(lang) or _MONTH_BY_LANG["eng"]
    template = _NAME_TEMPLATE.get(lang) or _NAME_TEMPLATE["eng"]
    return template.format(month=months[month], year=year)


def conference_uri(year: int, month: int) -> str:
    return f"/general-conference/{year:04d}/{month:02d}"


def _date_based_ceiling(today: _dt.date | None = None) -> tuple[int, int]:
    today = today or _dt.date.today()
    if today.month >= 10:
        return today.year, 10
    if today.month >= 4:
        return today.year, 4
    return today.year - 1, 10


async def _resolve_ceiling(lang: str) -> tuple[int, int]:
    """Newest published conference, from the landing page with a date fallback."""
    fallback = _date_based_ceiling()
    try:
        links = await scraper.list_conference_links(lang)
    except ContentUnavailable:
        logger.warning("Landing scrape failed; using date-based ceiling %s", fallback)
        return fallback
    if not links:
        return fallback
    newest = links[0]
    # Guard against the landing page lagging behind the calendar.
    return max(newest, fallback)


def _generate_conferences(ceiling: tuple[int, int], lang: str = "eng") -> list[Conference]:
    ceil_year, ceil_month = ceiling
    conferences: list[Conference] = []
    for year in range(ceil_year, EARLIEST_YEAR - 1, -1):
        for month in (10, 4):
            if year == ceil_year and month > ceil_month:
                continue
            conferences.append(
                Conference(
                    id=conf_id(year, month),
                    year=year,
                    month=month,
                    name=conference_name(year, month, lang),
                )
            )
    return conferences


async def list_conferences(lang: str) -> list[Conference]:
    cached = await cache.get(_CATALOG_KEY, lang)
    if cached is not None:
        return cached
    ceiling = await _resolve_ceiling(lang)
    conferences = _generate_conferences(ceiling, lang)
    await cache.set(_CATALOG_KEY, lang, conferences)
    return conferences


async def get_conference(conference_id: str, lang: str) -> ConferenceDetail:
    year, month = parse_conf_id(conference_id)

    cached = await cache.get(conference_id, lang)
    if cached is not None:
        return cached

    uri = conference_uri(year, month)
    try:
        payload = await content_api.get_content(uri, lang)
    except ContentUnavailable as exc:
        raise NotFound(f"Conference not available: {conference_id}") from exc

    body = (payload.get("content") or {}).get("body") or ""
    sessions = parse_conference_body(body, conference_id)
    if not sessions:
        raise NotFound(f"No sessions found for {conference_id}")

    # Use our generated name (already correctly capitalised for all supported
    # languages). The source API title is often lowercase and inconsistent.
    name = conference_name(year, month, lang)

    detail = ConferenceDetail(
        id=conference_id,
        year=year,
        month=month,
        name=name,
        image_url=None,
        sessions=sessions,
    )
    await cache.set(conference_id, lang, detail)
    return detail


async def resolve_talk_media(talk_uri: str, talk_id: str, lang: str) -> TalkMedia:
    """Fetch MP3 URL + image URL for a single talk.

    Tries the content API first; falls back to the scraper HTML path.
    Raises MediaUnavailable if neither path produces an MP3 URL.
    """
    mp3_url: str | None = None
    image_url: str | None = None

    try:
        payload = await content_api.get_content(talk_uri, lang)
        # Primary path: meta.audio.mediaUrl (confirmed present on live talks)
        meta = payload.get("meta") or {}
        # meta.audio is a list of audio variant dicts (e.g. [{mediaUrl: ..., variant: "audio"}])
        audio_list = meta.get("audio") or []
        if isinstance(audio_list, dict):
            audio_list = [audio_list]
        mp3_url = next(
            (a.get("mediaUrl") for a in audio_list if isinstance(a, dict) and a.get("mediaUrl")),
            None,
        ) or find_mp3_url(payload)
        image_url = meta.get("ogTagImageUrl")
    except ContentUnavailable:
        logger.warning("Content API failed for %s; trying HTML scraper", talk_uri)

    if not mp3_url:
        # HTML fallback: look for a .mp3 URL embedded in the page
        try:
            html = await scraper.get_html(talk_uri, lang)
            mp3_url = find_mp3_url(html)
        except ContentUnavailable:
            pass

    if not mp3_url:
        raise MediaUnavailable(f"No audio found for {talk_uri} in lang={lang}")

    return TalkMedia(talk_id=talk_id, mp3_url=mp3_url, image_url=image_url)
