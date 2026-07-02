"""Shared Pydantic models (see docs/09)."""

from __future__ import annotations

from pydantic import BaseModel


class Language(BaseModel):
    code: str
    name: str


class LanguagesResponse(BaseModel):
    languages: list[Language]
    default: str


class Conference(BaseModel):
    id: str
    year: int
    month: int
    name: str
    image_url: str | None = None


class CatalogResponse(BaseModel):
    conferences: list[Conference]


class Talk(BaseModel):
    id: str
    uri: str
    order: int
    title: str
    speaker: str
    image_url: str | None = None


class Session(BaseModel):
    id: str
    order: int
    name: str
    talks: list[Talk]


class ConferenceDetail(Conference):
    sessions: list[Session]


class TalkMedia(BaseModel):
    talk_id: str
    mp3_url: str
    image_url: str | None = None


class TalkTags(BaseModel):
    title: str
    artist: str
    album: str
    album_artist: str = "General Conference"
    track: str
    disc: str
    year: int
    genre: str = "Religion & Spirituality"


class Selection(BaseModel):
    conference_id: str
    session_ids: list[str] | None = None
    talk_ids: list[str] | None = None


class DownloadRequest(BaseModel):
    lang: str = "eng"
    selection: list[Selection]


class Skip(BaseModel):
    talk_id: str
    reason: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
