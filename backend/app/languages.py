"""Selectable audio languages (see docs/05, docs/07).

A curated list of widely available General Conference audio languages. A given
talk may not exist in every language; that is handled gracefully at download
time (FR-4).
"""

from __future__ import annotations

from app.models import Language

DEFAULT_LANGUAGE = "eng"

LANGUAGES: list[Language] = [
    Language(code="eng", name="English"),
    Language(code="spa", name="Español"),
    Language(code="por", name="Português"),
    Language(code="fra", name="Français"),
    Language(code="deu", name="Deutsch"),
    Language(code="ita", name="Italiano"),
    Language(code="jpn", name="日本語"),
    Language(code="kor", name="한국어"),
    Language(code="zho", name="中文"),
    Language(code="rus", name="Русский"),
    Language(code="tgl", name="Tagalog"),
    Language(code="smo", name="Gagana Samoa"),
    Language(code="ton", name="Lea Faka-Tonga"),
]

_VALID_CODES = {language.code for language in LANGUAGES}


def is_valid(code: str) -> bool:
    return code in _VALID_CODES


def normalize(code: str | None) -> str:
    """Return a valid language code, falling back to the default."""
    if code and is_valid(code):
        return code
    return DEFAULT_LANGUAGE
