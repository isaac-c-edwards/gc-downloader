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


class ServerBusy(AppError):
    """Too many jobs are running/queued to accept another right now (docs/06).

    Returned as 503 so the frontend can show a calm "try again in a moment"
    message and the client (or a CDN/load balancer) may retry later, rather
    than the request failing silently or the instance being pushed to OOM.
    """

    code = "ServerBusy"
    status_code = 503


class SourceUnreachable(AppError):
    code = "SourceUnreachable"
    status_code = 502


class ContentUnavailable(AppError):
    """The requested content could not be fetched/parsed from the source."""

    code = "SourceUnreachable"
    status_code = 502


class ContentNotFound(ContentUnavailable):
    """The source returned a genuine 404 for this uri+lang combination.

    Distinct from the generic `ContentUnavailable` (which also covers
    network errors, 5xx, robots.txt blocks, and exhausted retries) so callers
    that care can tell "this content truly doesn't exist" apart from "we
    couldn't reach it right now". Subclasses `ContentUnavailable` so existing
    `except ContentUnavailable` call sites (e.g. the content-API → scraper
    fallback in resolve_talk_media) are unaffected.
    """


class LanguageUnavailable(AppError):
    """A conference genuinely has no translation in the requested language
    (as opposed to a network hiccup or bad id). Distinct from `NotFound` so
    the frontend can show a calm, non-actionable message instead of an error
    with a "Try again" prompt that would never succeed (docs/02 FR-4).
    """

    code = "LanguageUnavailable"
    status_code = 404


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
