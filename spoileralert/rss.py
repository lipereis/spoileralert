"""Username-only diary reading through Letterboxd's public RSS feed.

Letterboxd does not grant API access for visualization projects, and it blocks
page scraping from shared cloud addresses. The per-member RSS feed is the
machine-readable route Letterboxd itself points at, so it is what makes
"type a username" work from any host.

The trade-off is coverage: the feed carries recent activity rather than a whole
diary, so a busy year can be cut off. `DiaryFeed.truncated` records when that
may have happened instead of quietly presenting a partial year as a complete
one.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable
from urllib.parse import quote

from spoileralert.data import (
    BlockedError,
    EmptyDiaryError,
    NetworkError,
    ProfileNotFoundError,
)
from spoileralert.models import DiaryEntry

FEED_URL_TEMPLATE = "https://letterboxd.com/{username}/rss/"

_LETTERBOXD_NS = "https://letterboxd.com"
_USER_AGENT = "SpoilerAlert/1.0 (+https://github.com/lipereis/spoileralert)"
_TIMEOUT_SECONDS = (10, 30)
# Feeds run tens of kilobytes; this only stops a pathological response from
# being handed to the XML parser.
_MAX_FEED_BYTES = 8 * 1024 * 1024
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,50}$")


@dataclass(frozen=True)
class DiaryFeed:
    """Diary viewings read from one member feed, plus how complete they are."""

    entries: tuple[DiaryEntry, ...]
    year: int
    diary_item_count: int
    truncated: bool

    @property
    def coverage_note(self) -> str | None:
        """Describe missing coverage, or return None when the year is whole."""
        if not self.truncated:
            return None
        return (
            f"Letterboxd's public feed only publishes recent activity, and every "
            f"entry it returned is from {self.year}. Earlier {self.year} viewings "
            "are probably missing, so these totals cover the recent part of the "
            "year. Upload your diary export for the complete year."
        )


def build_feed_url(username: str) -> str:
    """Return the member feed URL for a syntactically valid username."""
    candidate = (username or "").strip().lstrip("@")
    if not _USERNAME_PATTERN.match(candidate):
        raise ProfileNotFoundError(
            f"'{username}' is not a valid Letterboxd username."
        )
    return FEED_URL_TEMPLATE.format(username=quote(candidate.casefold(), safe=""))


def fetch_feed(username: str, *, session: Any | None = None) -> bytes:
    """Fetch one member feed, mapping transport failures to domain errors."""
    import requests

    url = build_feed_url(username)
    getter = session.get if session is not None else requests.get

    try:
        response = getter(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/rss+xml"},
            timeout=_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 - every transport failure is a NetworkError
        raise NetworkError(
            "Could not reach Letterboxd's public feed."
        ) from exc

    status = getattr(response, "status_code", None)
    if status == 404:
        raise ProfileNotFoundError(
            f"Letterboxd has no public feed for '{username}'. The name may be "
            "misspelled, or the profile may be private."
        )
    if status == 403:
        raise BlockedError(
            "Letterboxd refused this server's request for the public feed."
        )
    if status != 200:
        raise NetworkError(
            f"Letterboxd's public feed answered with status {status}."
        )

    content = response.content
    if len(content) > _MAX_FEED_BYTES:
        raise NetworkError("Letterboxd's public feed response was unexpectedly large.")
    return content


def _child_text(item: ElementTree.Element, tag: str) -> str | None:
    found = item.find(tag)
    if found is None or found.text is None:
        return None
    text = found.text.strip()
    return text or None


def _slug_from_link(link: str | None) -> str | None:
    """Pull the film slug out of a diary permalink.

    Repeat viewings append a counter, as in `/film/parasite-2019/1/`, so the
    segment right after `/film/` is the slug.
    """
    if not link or "/film/" not in link:
        return None
    tail = link.split("/film/", 1)[1]
    slug = tail.split("/", 1)[0].strip()
    return slug or None


def _optional_year(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _optional_rating(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _optional_flag(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if normalized in {"yes", "true", "1"}:
        return True
    if normalized in {"no", "false", "0"}:
        return False
    return None


def parse_feed(xml_source: bytes | str, year: int | None = None) -> DiaryFeed:
    """Turn one member feed into validated viewings for a single year.

    Feed items that are not diary viewings, such as published lists, carry no
    film title or watched date and are skipped rather than counted.
    """
    expected_year = datetime.now().year if year is None else year

    try:
        root = ElementTree.fromstring(xml_source)
    except ElementTree.ParseError as exc:
        raise NetworkError(
            "Letterboxd's public feed returned a response we could not read."
        ) from exc

    entries: list[DiaryEntry] = []
    diary_dates: list[date] = []

    for index, item in enumerate(root.findall("./channel/item")):
        title = _child_text(item, f"{{{_LETTERBOXD_NS}}}filmTitle")
        watched_text = _child_text(item, f"{{{_LETTERBOXD_NS}}}watchedDate")
        if not title or not watched_text:
            continue

        try:
            watched_on = date.fromisoformat(watched_text)
        except ValueError:
            continue

        diary_dates.append(watched_on)
        if watched_on.year != expected_year:
            continue

        link = _child_text(item, "link")
        entries.append(
            DiaryEntry(
                viewing_id=_child_text(item, "guid") or link or str(index),
                title=title,
                release_year=_optional_year(
                    _child_text(item, f"{{{_LETTERBOXD_NS}}}filmYear")
                ),
                slug=_slug_from_link(link),
                watched_on=watched_on,
                rating=_optional_rating(
                    _child_text(item, f"{{{_LETTERBOXD_NS}}}memberRating")
                ),
                rewatched=_optional_flag(
                    _child_text(item, f"{{{_LETTERBOXD_NS}}}rewatch")
                ),
            )
        )

    entries.sort(key=lambda entry: entry.watched_on)

    # Seeing an older viewing proves the feed reached past the requested year,
    # so nothing from that year fell off the end of it.
    reached_before_year = any(watched.year < expected_year for watched in diary_dates)
    return DiaryFeed(
        entries=tuple(entries),
        year=expected_year,
        diary_item_count=len(diary_dates),
        truncated=bool(entries) and not reached_before_year,
    )


def fetch_diary_feed(
    username: str,
    year: int | None = None,
    *,
    fetch: Callable[[str], bytes] = fetch_feed,
) -> DiaryFeed:
    """Read one member's public feed into a single year of viewings."""
    feed = parse_feed(fetch(username), year)
    if not feed.entries:
        raise EmptyDiaryError(
            f"Letterboxd's public feed for '{username}' has no {feed.year} "
            "diary entries."
        )
    return feed
