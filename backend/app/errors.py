"""Typed application errors and their HTTP mappings (see docs/07)."""

from __future__ import annotations


class AppError(Exception):
    code: str = "Internal"
    status_code: int = 500

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.__name__
        super().__init__(self.message)


class BadSelection(AppError):
    code = "BadSelection"
    status_code = 400


class NotFound(AppError):
    code = "NotFound"
    status_code = 404


class NotReady(AppError):
    code = "NotReady"
    status_code = 409


class SourceUnreachable(AppError):
    code = "SourceUnreachable"
    status_code = 502


class ContentUnavailable(AppError):
    """The requested content could not be fetched/parsed from the source."""

    code = "SourceUnreachable"
    status_code = 502


class MediaUnavailable(AppError):
    """A talk has no resolvable audio (e.g. not available in the language)."""

    code = "NotFound"
    status_code = 404


class RobotsDisallowed(ContentUnavailable):
    """The source site's robots.txt disallows fetching this path (docs/11).

    Subclasses `ContentUnavailable` so existing `except ContentUnavailable`
    call sites (e.g. the content-API → scraper fallback in `catalog.py`) keep
    working without change — a robots-blocked path is just another form of
    "can't get this content right now".
    """
