"""Regression tests for the batched streaming ZIP builder (see docs/06 NFR-2).

`stream_zip` writes talks to the archive in bounded batches instead of
gathering the whole selection into memory before yielding anything (see
DECISIONS.md). These tests mock the network-facing calls (catalog, media
resolution, mp3 fetch, tagging) and never hit the network, and verify that:

  1. The concatenated output is a structurally valid ZIP.
  2. All expected talks/paths are present, batching doesn't drop or duplicate
     entries.
  3. A per-talk failure becomes a skip instead of aborting the whole archive.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from app.media import packager
from app.models import ConferenceDetail, DownloadRequest, Selection, Session, Talk


def _make_conference(n_talks: int) -> ConferenceDetail:
    talks = [
        Talk(
            id=f"t{i}",
            uri=f"/general-conference/2026/04/{i:02d}talk",
            order=i,
            title=f"Talk {i}",
            speaker=f"Speaker {i}",
        )
        for i in range(1, n_talks + 1)
    ]
    session = Session(id="2026-04-s1", order=1, name="Saturday Morning Session", talks=talks)
    return ConferenceDetail(
        id="2026-04", year=2026, month=4, name="April 2026 General Conference",
        sessions=[session],
    )


@pytest.fixture
def patch_pipeline(monkeypatch):
    """Patch every external dependency stream_zip touches, with a knob to
    make one specific talk_id fail (simulating e.g. MediaUnavailable)."""

    def _apply(detail: ConferenceDetail, batch_size: int = 2, fail_talk_id: str | None = None):
        async def fake_get_conference(conference_id, lang):
            return detail

        async def fake_resolve_talk_media(talk_uri, talk_id, lang):
            if talk_id == fail_talk_id:
                raise RuntimeError("simulated media failure")
            return type("M", (), {"mp3_url": f"https://example.com/{talk_id}.mp3", "image_url": None})()

        async def fake_fetch_mp3(url):
            return b"FAKE-MP3-BYTES-" + url.encode()

        async def fake_fetch_cover(url):
            return None

        def fake_tag_mp3(data, tags, cover):
            return data  # tagging is irrelevant to the streaming/batching behavior under test

        monkeypatch.setattr(packager, "get_conference", fake_get_conference)
        monkeypatch.setattr(packager, "resolve_talk_media", fake_resolve_talk_media)
        monkeypatch.setattr(packager, "fetch_mp3", fake_fetch_mp3)
        monkeypatch.setattr(packager, "_fetch_cover", fake_fetch_cover)
        monkeypatch.setattr(packager, "tag_mp3", fake_tag_mp3)
        monkeypatch.setattr(packager.settings, "max_concurrency", batch_size)

    return _apply


async def _collect_zip_bytes(request: DownloadRequest) -> bytes:
    chunks = [chunk async for chunk in packager.stream_zip(request)]
    return b"".join(chunks)


@pytest.mark.asyncio
async def test_stream_zip_spans_multiple_batches(patch_pipeline):
    """8 talks with batch_size=3 forces 3 batches (3+3+2) — every talk must
    still end up in the final archive exactly once."""
    detail = _make_conference(8)
    patch_pipeline(detail, batch_size=3)

    request = DownloadRequest(
        lang="eng",
        selection=[Selection(conference_id="2026-04", session_ids=["2026-04-s1"])],
    )
    zip_bytes = await _collect_zip_bytes(request)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert zf.testzip() is None  # structurally valid, no corrupt members
        names = zf.namelist()
        assert len(names) == 8
        for i in range(1, 9):
            assert any(f"{i:02d} - Talk {i} - Speaker {i}.mp3" in n for n in names)


@pytest.mark.asyncio
async def test_stream_zip_single_batch_still_valid(patch_pipeline):
    """When everything fits in one batch (batch_size >= talk count), behavior
    should be identical to the multi-batch case."""
    detail = _make_conference(3)
    patch_pipeline(detail, batch_size=10)

    request = DownloadRequest(
        lang="eng",
        selection=[Selection(conference_id="2026-04", session_ids=["2026-04-s1"])],
    )
    zip_bytes = await _collect_zip_bytes(request)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert zf.testzip() is None
        assert len(zf.namelist()) == 3


@pytest.mark.asyncio
async def test_stream_zip_skips_failed_talk_without_aborting(patch_pipeline):
    """A single failing talk (e.g. MediaUnavailable) must not abort the whole
    archive — the other talks still make it in (FR-7)."""
    detail = _make_conference(4)
    patch_pipeline(detail, batch_size=2, fail_talk_id="t2")

    request = DownloadRequest(
        lang="eng",
        selection=[Selection(conference_id="2026-04", session_ids=["2026-04-s1"])],
    )
    zip_bytes = await _collect_zip_bytes(request)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert len(names) == 3  # 4 talks minus the 1 failure
        assert not any("Talk 2" in n for n in names)
