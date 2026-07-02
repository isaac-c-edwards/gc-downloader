"""Safe filename generation and in-ZIP path building (see docs/06, FR-5)."""

from __future__ import annotations

import re
import unicodedata

# Characters illegal on Windows, macOS, or Android filesystems.
_ILLEGAL_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE_RE = re.compile(r"\s+")
_MAX_COMPONENT = 120  # chars per path component


def safe_filename(s: str) -> str:
    """Strip filesystem-illegal characters, collapse whitespace, trim length."""
    # Normalise unicode (composed form)
    s = unicodedata.normalize("NFC", s)
    s = _ILLEGAL_RE.sub("", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    # Trim to avoid path-length issues
    return s[:_MAX_COMPONENT].strip()


def _pad(n: int, total: int) -> str:
    width = len(str(total))
    return str(n).zfill(max(width, 2))


def zip_path(
    conf_id: str,
    conf_name: str,
    session_order: int,
    session_name: str,
    session_total: int,
    talk_order: int,
    talk_title: str,
    talk_speaker: str,
    talk_total: int,
) -> str:
    """Build the in-ZIP path for one talk (see docs/02 FR-5).

    Example:
        2026-04 April General Conference/
            1 - Saturday Morning Session/
                01 - Sustaining of Authorities - Dallin H. Oaks.mp3
    """
    conf_folder = safe_filename(f"{conf_id} {conf_name}")
    sess_folder = safe_filename(
        f"{_pad(session_order, session_total)} - {session_name}"
    )
    talk_speaker_part = f" - {talk_speaker}" if talk_speaker else ""
    filename = safe_filename(
        f"{_pad(talk_order, talk_total)} - {talk_title}{talk_speaker_part}"
    ) + ".mp3"
    return f"{conf_folder}/{sess_folder}/{filename}"


def zip_filename(conf_names: list[str], lang_name: str) -> str:
    """Suggested filename for the downloaded ZIP."""
    if len(conf_names) == 1:
        base = safe_filename(conf_names[0])
    else:
        base = f"{len(conf_names)} conferences"
    return f"GC Downloader - {base} ({lang_name}).zip"
