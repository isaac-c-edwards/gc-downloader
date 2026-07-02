"""Write ID3v2 tags onto in-memory MP3 bytes using mutagen (see docs/06)."""

from __future__ import annotations

import io
import logging

from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
    ID3NoHeaderError,
)

from app.models import TalkTags

logger = logging.getLogger(__name__)


def _mime_from_bytes(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return "image/jpeg"


def tag_mp3(data: bytes, tags: TalkTags, cover: bytes | None = None) -> bytes:
    """Apply ID3v2 tags to `data` (MP3 bytes) and return the tagged bytes.

    Mutagen writes the ID3 header in place when given a file-like object.
    We create a fresh BytesIO with the original MP3, let mutagen patch the
    header, then return the modified bytes.
    """
    buf = io.BytesIO(data)

    try:
        id3 = ID3(buf)
    except ID3NoHeaderError:
        id3 = ID3()

    id3.delall("TIT2"); id3.add(TIT2(encoding=3, text=tags.title))
    id3.delall("TPE1"); id3.add(TPE1(encoding=3, text=tags.artist))
    id3.delall("TALB"); id3.add(TALB(encoding=3, text=tags.album))
    id3.delall("TPE2"); id3.add(TPE2(encoding=3, text=tags.album_artist))
    id3.delall("TRCK"); id3.add(TRCK(encoding=3, text=tags.track))
    id3.delall("TPOS"); id3.add(TPOS(encoding=3, text=tags.disc))
    id3.delall("TDRC"); id3.add(TDRC(encoding=3, text=str(tags.year)))
    id3.delall("TCON"); id3.add(TCON(encoding=3, text=tags.genre))

    if cover:
        id3.delall("APIC")
        id3.add(
            APIC(
                encoding=3,
                mime=_mime_from_bytes(cover),
                type=3,  # front cover
                desc="Cover",
                data=cover,
            )
        )

    # Write the ID3 tag to a fresh buffer, then append the raw MP3 audio.
    # This avoids in-place patching edge cases with files that lack a header.
    tag_buf = io.BytesIO()
    id3.save(tag_buf, v2_version=3)
    tag_bytes = tag_buf.getvalue()

    # Strip any existing ID3v2 header from the original data before appending
    audio_start = _find_audio_start(data)
    return tag_bytes + data[audio_start:]


def _find_audio_start(data: bytes) -> int:
    """Return the byte offset where the MPEG audio frames begin (skip ID3 header)."""
    if data[:3] == b"ID3":
        # ID3v2 size is encoded as 4 syncsafe bytes at offset 6
        size = (
            ((data[6] & 0x7F) << 21)
            | ((data[7] & 0x7F) << 14)
            | ((data[8] & 0x7F) << 7)
            | (data[9] & 0x7F)
        )
        has_footer = bool(data[5] & 0x10)
        header_size = 10 + size + (10 if has_footer else 0)
        return header_size
    return 0
