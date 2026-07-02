"""Defensive, search-based extraction of conference structure (see docs/05).

We parse the `content.body` HTML returned by the content API into Sessions and
Talks. The parsing keys off stable *content* markers (``data-content-type`` and
semantic class names) rather than fragile deep paths, and every field is
extracted defensively so one malformed talk never breaks the whole conference.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup, Tag

from app.models import Session, Talk

logger = logging.getLogger(__name__)

_MP3_RE = re.compile(r"https?://[^\s\"'<>]+\.mp3", re.IGNORECASE)


def clean_uri(href: str) -> str:
    """Strip query/fragment and the /study prefix from an href."""
    href = href.split("?", 1)[0].split("#", 1)[0]
    if href.startswith("/study/"):
        href = href[len("/study") :]
    return href


def slug_from_uri(uri: str) -> str:
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _text(node: Tag | None) -> str:
    return node.get_text(strip=True) if node else ""


def _first_image(anchor: Tag) -> str | None:
    img = anchor.find("img")
    if isinstance(img, Tag):
        src = img.get("src")
        if isinstance(src, str) and src:
            return src
    return None


def _session_name(session_li: Tag, fallback: str) -> str:
    label = session_li.find(["h2", "h3"], class_="label")
    if isinstance(label, Tag):
        name = _text(label.find(class_="title")) or _text(label)
        if name:
            return name
    return fallback


def _is_session_tile(slug: str, title: str, speaker: str, session_name: str | None) -> bool:
    """True if an anchor is a session/navigation tile rather than a talk.

    Talks always list a speaker (``primaryMeta``); session landing tiles do not
    and instead repeat the session name or use a slug ending in
    ``session``/``meeting``.
    """
    if speaker:
        return False
    if session_name and title and title.strip().lower() == session_name.strip().lower():
        return True
    low = slug.lower()
    return low.endswith("session") or low.endswith("meeting")


def _talk_from_anchor(
    anchor: Tag, conf_id: str, order: int, session_name: str | None
) -> Talk | None:
    href = anchor.get("href")
    if not isinstance(href, str) or not href:
        return None

    uri = clean_uri(href)
    slug = slug_from_uri(uri)
    if not slug:
        return None

    title = _text(anchor.find(class_="title"))
    speaker = _text(anchor.find(class_="primaryMeta"))

    if _is_session_tile(slug, title, speaker, session_name):
        return None
    if not title:
        return None

    return Talk(
        id=f"{conf_id}-{slug}",
        uri=uri,
        order=order,
        title=title,
        speaker=speaker,
        image_url=_first_image(anchor),
    )


def _talks_from_anchors(
    anchors: list[Tag], conf_id: str, session_name: str | None
) -> list[Talk]:
    talks: list[Talk] = []
    order = 1
    for anchor in anchors:
        try:
            talk = _talk_from_anchor(anchor, conf_id, order, session_name)
        except Exception:  # noqa: BLE001 - never let one talk break the parse
            logger.exception("Failed to parse a talk in %s", conf_id)
            continue
        if talk is not None:
            talks.append(talk)
            order += 1
    return talks


def parse_conference_body(body_html: str, conf_id: str) -> list[Session]:
    """Parse a conference's `content.body` HTML into ordered Sessions/Talks.

    Format-agnostic: works with both the older markup (``data-content-type``
    attributes) and the current markup (plain ``nav.manifest > ul.doc-map``
    nesting), since both share the same anchor/heading structure.
    """
    soup = BeautifulSoup(body_html, "html.parser")
    nav = soup.find("nav", class_="manifest") or soup

    top_ul = nav.find("ul", class_="doc-map") if isinstance(nav, Tag) else None
    sessions: list[Session] = []

    if isinstance(top_ul, Tag):
        session_lis = [li for li in top_ul.find_all("li", recursive=False)]
        for s_index, session_li in enumerate(session_lis, start=1):
            name = _session_name(session_li, fallback=f"Session {s_index}")
            anchors = [a for a in session_li.select("a.list-tile") if isinstance(a, Tag)]
            if not anchors:
                anchors = [
                    a for a in session_li.find_all("a", href=True) if isinstance(a, Tag)
                ]
            talks = _talks_from_anchors(anchors, conf_id, session_name=name)
            if talks:
                sessions.append(
                    Session(
                        id=f"{conf_id}-s{len(sessions) + 1}",
                        order=len(sessions) + 1,
                        name=name,
                        talks=talks,
                    )
                )

    if not sessions:
        # Flat fallback: no usable session grouping — collect every talk anchor.
        logger.warning("No session grouping for %s; using flat fallback.", conf_id)
        anchors = [a for a in soup.select("a.list-tile") if isinstance(a, Tag)]
        if not anchors:
            anchors = [a for a in soup.find_all("a", href=True) if isinstance(a, Tag)]
        talks = _talks_from_anchors(anchors, conf_id, session_name=None)
        if talks:
            sessions.append(
                Session(id=f"{conf_id}-s1", order=1, name="General Conference", talks=talks)
            )

    return sessions


def find_mp3_url(payload: object) -> str | None:
    """Recursively search any JSON-like structure for an MP3 URL (for M3)."""
    if isinstance(payload, str):
        match = _MP3_RE.search(payload)
        return match.group(0) if match else None
    if isinstance(payload, dict):
        for value in payload.values():
            found = find_mp3_url(value)
            if found:
                return found
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            found = find_mp3_url(item)
            if found:
                return found
    return None
