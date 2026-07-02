"""Tests for ID3 tagging on disk."""

from __future__ import annotations

import os
import tempfile

from mutagen.id3 import ID3

from app.media.tagger import tag_mp3_file
from app.models import TalkTags

# Minimal valid MPEG frame sync + dummy frame (mutagen only needs a file path).
_FAKE_MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" + b"\x00" * 128


def test_tag_mp3_file_writes_tags_in_place():
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.write(fd, _FAKE_MP3)
    os.close(fd)
    try:
        tags = TalkTags(
            title="Test Talk",
            artist="Test Speaker",
            album="April 2026 General Conference",
            track="1/5",
            disc="1/4",
            year=2026,
        )
        tag_mp3_file(path, tags, cover=None)

        id3 = ID3(path)
        assert str(id3["TIT2"]) == "Test Talk"
        assert str(id3["TPE1"]) == "Test Speaker"
        assert str(id3["TALB"]) == "April 2026 General Conference"
    finally:
        os.unlink(path)
