"""Unit tests for the conference body extractor, run against a saved fixture.

The fixture (`fixtures/conference_2024_04.json`) is a real content-API response
captured from the source. These tests never hit the network.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.source.extractor import (
    clean_uri,
    find_mp3_url,
    parse_conference_body,
    slug_from_uri,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_body(name: str) -> str:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8-sig"))
    return payload["content"]["body"]


def test_parses_multiple_sessions():
    sessions = parse_conference_body(_load_body("conference_2024_04.json"), "2024-04")
    # April 2024 had 5 sessions.
    assert len(sessions) == 5
    assert sessions[0].name == "Saturday Morning Session"
    assert sessions[0].order == 1
    assert sessions[0].id == "2024-04-s1"


def test_parses_current_format_2026():
    """The 2026 markup has no data-content-type attributes (different format)."""
    sessions = parse_conference_body(_load_body("conference_2026_04.json"), "2026-04")
    assert len(sessions) == 4  # April 2026 had no separate Saturday evening session
    names = [s.name for s in sessions]
    assert names[0] == "Saturday Morning Session"
    # Session tiles must not be mistaken for talks, and every talk has a speaker.
    for session in sessions:
        assert session.talks
        for talk in session.talks:
            assert "session" not in talk.uri.rsplit("/", 1)[-1]
            assert talk.speaker


def test_talks_have_required_fields():
    sessions = parse_conference_body(_load_body("conference_2024_04.json"), "2024-04")
    talks = [talk for session in sessions for talk in session.talks]
    assert len(talks) > 30
    for talk in talks:
        assert talk.title
        assert talk.uri.startswith("/general-conference/2024/04/")
        assert talk.id.startswith("2024-04-")
        assert talk.order >= 1


def test_talk_ids_are_unique():
    sessions = parse_conference_body(_load_body("conference_2024_04.json"), "2024-04")
    ids = [talk.id for session in sessions for talk in session.talks]
    assert len(ids) == len(set(ids))


def test_clean_uri_and_slug():
    assert clean_uri("/study/general-conference/2024/04/11oaks?lang=eng") == (
        "/general-conference/2024/04/11oaks"
    )
    assert slug_from_uri("/general-conference/2024/04/11oaks") == "11oaks"


def test_find_mp3_url_searches_nested():
    payload = {"a": {"b": [{"download": "https://media.ldscdn.org/x/talk.mp3"}]}}
    assert find_mp3_url(payload) == "https://media.ldscdn.org/x/talk.mp3"
    assert find_mp3_url({"none": "here"}) is None
