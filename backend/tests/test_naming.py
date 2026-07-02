"""Unit tests for filename sanitization and ZIP path building (see docs/06,
FR-5). These never hit the network.
"""

from __future__ import annotations

from app.media.naming import safe_filename, zip_filename, zip_path


class TestSafeFilename:
    def test_strips_windows_illegal_characters(self):
        # < > : " / \ | ? * are illegal on Windows (also unsafe on other OSes)
        assert safe_filename('Talk: "Faith" <Part 1> | *?/\\') == "Talk Faith Part 1"

    def test_strips_control_characters(self):
        # Control chars (including tab/newline) are removed outright, not
        # converted to a separator — "Talk\tTitle" collapses to "TalkTitle".
        assert safe_filename("Talk\x00Title\x1f") == "TalkTitle"

    def test_collapses_repeated_regular_spaces(self):
        assert safe_filename("Talk   Title   with   gaps") == "Talk Title with gaps"

    def test_trims_leading_and_trailing_whitespace(self):
        assert safe_filename("   Talk Title   ") == "Talk Title"

    def test_normalizes_unicode_to_nfc(self):
        # "é" as combining sequence (e + combining acute) should normalize to
        # the single composed character, not get stripped or duplicated.
        combining = "Cafe\u0301"  # "Café" using a combining accent
        assert safe_filename(combining) == "Café"

    def test_trims_overly_long_names(self):
        long_title = "A" * 500
        result = safe_filename(long_title)
        assert len(result) <= 120

    def test_preserves_safe_punctuation(self):
        assert safe_filename("Elder Jeffrey R. Holland - Part 1") == (
            "Elder Jeffrey R. Holland - Part 1"
        )

    def test_empty_string(self):
        assert safe_filename("") == ""


class TestZipPath:
    def test_builds_expected_folder_structure(self):
        # _pad() always zero-pads to at least 2 digits, even for single-digit
        # totals (e.g. "1 -" would sort before "10 -" incorrectly otherwise).
        path = zip_path(
            conf_id="2026-04",
            conf_name="April 2026 General Conference",
            session_order=1,
            session_name="Saturday Morning Session",
            session_total=5,
            talk_order=1,
            talk_title="Sustaining of Authorities",
            talk_speaker="Dallin H. Oaks",
            talk_total=8,
        )
        assert path == (
            "2026-04 April 2026 General Conference/"
            "01 - Saturday Morning Session/"
            "01 - Sustaining of Authorities - Dallin H. Oaks.mp3"
        )

    def test_zero_pads_talk_number_to_total_width(self):
        # 12 talks in a session → talk numbers should be zero-padded to 2 digits
        path = zip_path(
            conf_id="2026-04", conf_name="April 2026 General Conference",
            session_order=1, session_name="Saturday Morning Session", session_total=2,
            talk_order=3, talk_title="Talk Three", talk_speaker="Speaker",
            talk_total=12,
        )
        assert "03 - Talk Three - Speaker.mp3" in path

    def test_zero_pads_session_number_to_total_width(self):
        # 12 sessions in a conference → session numbers zero-padded to 2 digits
        path = zip_path(
            conf_id="2026-04", conf_name="April 2026 General Conference",
            session_order=3, session_name="Sunday Morning Session", session_total=12,
            talk_order=1, talk_title="Talk", talk_speaker="Speaker", talk_total=1,
        )
        assert "03 - Sunday Morning Session/" in path

    def test_omits_speaker_when_missing(self):
        path = zip_path(
            conf_id="2026-04", conf_name="April 2026 General Conference",
            session_order=1, session_name="Saturday Morning Session", session_total=1,
            talk_order=1, talk_title="Untitled Talk", talk_speaker="",
            talk_total=1,
        )
        assert path.endswith("01 - Untitled Talk.mp3")

    def test_sanitizes_illegal_characters_in_all_components(self):
        path = zip_path(
            conf_id="2026-04", conf_name='April "2026" General Conference',
            session_order=1, session_name="Saturday: Morning Session", session_total=1,
            talk_order=1, talk_title="Talk / Title", talk_speaker="Speaker?",
            talk_total=1,
        )
        assert '"' not in path
        assert ":" not in path
        # Only the intentional path separators ("/") between components remain —
        # any "/" that was part of a title/name must have been stripped.
        parts = path.split("/")
        assert len(parts) == 3


class TestZipFilename:
    def test_single_conference(self):
        name = zip_filename(["April 2026 General Conference"], "English")
        assert name == "GC Downloader - April 2026 General Conference (English).zip"

    def test_multiple_conferences(self):
        name = zip_filename(
            ["April 2026 General Conference", "October 2025 General Conference"],
            "English",
        )
        assert name == "GC Downloader - 2 conferences (English).zip"

    def test_non_english_language_label(self):
        name = zip_filename(["April 2026 General Conference"], "Español")
        assert name == "GC Downloader - April 2026 General Conference (Español).zip"
