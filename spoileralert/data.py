"""Data ingestion layer: talks to Letterboxd via letterboxdpy and flattens the
messy nested diary structure into a plain list of dicts pandas can chew on.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from spoileralert.models import DiaryEntry


class NetworkError(Exception):
    """Raised when Letterboxd cannot be reached reliably."""


class ProfileNotFoundError(Exception):
    """Raised when the username does not identify an available public profile."""


class EmptyDiaryError(Exception):
    """Raised when the profile has no diary entries for the current year."""


_NETWORK_EXCEPTION_CLASSES = {
    ("requests.exceptions", "ConnectionError"),
    ("requests.exceptions", "Timeout"),
    ("urllib3.exceptions", "ConnectionError"),
    ("urllib3.exceptions", "TimeoutError"),
    ("curl_cffi.requests.exceptions", "RequestException"),
    ("letterboxdpy.core.exceptions", "PageLoadError"),
    ("socket", "gaierror"),
}


def _exception_chain(exc: BaseException):
    """Yield an exception and its explicit, implicit, or reason chain once."""
    pending = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        for related in (
            current.__cause__,
            current.__context__,
            getattr(current, "reason", None),
        ):
            if isinstance(related, BaseException):
                pending.append(related)


def _is_network_failure(exc: BaseException) -> bool:
    """Classify only known transport failures across wrapper chains."""
    for current in _exception_chain(exc):
        if isinstance(current, (ConnectionError, TimeoutError)):
            return True
        if any(
            (base.__module__, base.__name__) in _NETWORK_EXCEPTION_CLASSES
            for base in type(current).__mro__
        ):
            return True
    return False


def fetch_user(username: str):
    """Instantiate a letterboxdpy User, translating library failures into
    our own domain exceptions so the UI layer can react cleanly.
    """
    from letterboxdpy.user import User

    username = username.strip().lstrip("@")
    if not username:
        raise ProfileNotFoundError("Empty username.")

    try:
        user = User(username)
    except Exception as exc:  # letterboxdpy raises assorted errors on 404/private
        if _is_network_failure(exc):
            raise NetworkError(
                "Could not reach Letterboxd while loading the profile."
            ) from exc
        raise ProfileNotFoundError(
            f"Could not load Letterboxd profile '{username}'. "
            "It may be misspelled, private, or unavailable."
        ) from exc

    return user


def _as_entry(item: Any) -> dict | None:
    """Normalize a single diary item (dict, or a [day, name] pair) into a
    plain {"name": ...} dict.
    """
    if isinstance(item, dict):
        return item
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return {"day": item[0], "name": item[1]}
    return None


def _entries_from_day_bucket(day_value: Any) -> list[dict]:
    """A single day's bucket can be a list of movie dicts/pairs or a
    single dict -- normalize to a list of dicts.
    """
    if isinstance(day_value, dict):
        return [day_value]
    if isinstance(day_value, list):
        entries = [_as_entry(item) for item in day_value]
        return [e for e in entries if e is not None]
    return []


def flatten_diary(recent_diary: dict, current_year: int | None = None) -> list[dict]:
    """Flatten letterboxdpy's `user.recent.get('diary', {})` payload into a
    list of {"title": str, "month": int} dicts.

    Handles both known shapes of the `months` structure across letterboxdpy
    forks/versions:
      - {"1": {"31": [{"name": ...}, ...]}}          (day -> list of films)
      - {"1": [["29", "PlayTime"], ...]}              (list of [day, name])
    """
    months_blob = (recent_diary or {}).get("months", {})
    flattened: list[dict] = []

    for month_key, month_value in months_blob.items():
        try:
            month_number = int(month_key)
        except (TypeError, ValueError):
            continue
        if not (1 <= month_number <= 12):
            continue

        if isinstance(month_value, dict):
            # {"day": [movie_dict, ...]} -- iterate each day's bucket.
            for day_value in month_value.values():
                for entry in _entries_from_day_bucket(day_value):
                    title = entry.get("name") or entry.get("title")
                    if title:
                        flattened.append({"title": title, "month": month_number})
        elif isinstance(month_value, list):
            # A flat list where each item is either a movie dict or a
            # [day, name] pair -- each item is already one entry.
            for item in month_value:
                entry = _as_entry(item)
                if not entry:
                    continue
                title = entry.get("name") or entry.get("title")
                if title:
                    flattened.append({"title": title, "month": month_number})

    return flattened


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _optional_rating(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _optional_rewatch(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return None


def normalize_year_diary(year_diary: dict, current_year: int) -> list[DiaryEntry]:
    """Turn a complete Letterboxd diary response into validated viewings.

    Each valid raw row becomes one ``DiaryEntry``; intentionally no title- or
    slug-based deduplication happens here because rewatches are viewings too.
    """
    raw_entries = (year_diary or {}).get("entries", {})
    if isinstance(raw_entries, dict):
        items = raw_entries.items()
    elif isinstance(raw_entries, (list, tuple)):
        items = enumerate(raw_entries)
    else:
        return []

    normalized: list[DiaryEntry] = []
    for viewing_id, entry in items:
        if not isinstance(entry, dict):
            continue
        title = entry.get("name") or entry.get("title")
        date_text = entry.get("date")
        if not isinstance(title, str) or not title.strip() or not isinstance(date_text, str):
            continue
        try:
            watched_on = date.fromisoformat(date_text)
        except ValueError:
            continue
        if watched_on.year != current_year:
            continue

        actions = entry.get("actions")
        actions = actions if isinstance(actions, dict) else {}
        release_year = _optional_int(entry.get("release", entry.get("release_year")))
        slug = entry.get("slug")
        normalized.append(
            DiaryEntry(
                viewing_id=str(viewing_id),
                title=title,
                release_year=release_year,
                slug=slug if isinstance(slug, str) and slug else None,
                watched_on=watched_on,
                rating=_optional_rating(actions.get("rating", entry.get("rating"))),
                rewatched=_optional_rewatch(
                    actions.get("rewatched", entry.get("rewatched"))
                ),
            )
        )

    return normalized


def flatten_year_diary(
    year_diary: dict, current_year: int | None = None
) -> list[dict]:
    """Compatibility helper that projects complete diary entries to overview data."""
    expected_year = current_year or datetime.now().year
    return [
        {"title": entry.title, "month": entry.watched_on.month}
        for entry in normalize_year_diary(year_diary, expected_year)
    ]


def get_rich_diary_entries(username: str, year: int | None = None) -> list[DiaryEntry]:
    """Fetch every valid viewing from a user's selected calendar year.

    Existing domain exceptions are deliberately retained so current UI error
    handling remains unchanged.
    """
    requested_year = datetime.now().year if year is None else year
    user = fetch_user(username)
    try:
        year_diary = user.get_diary_year(requested_year)
    except Exception as exc:
        if _is_network_failure(exc):
            raise NetworkError(
                "Could not reach Letterboxd while loading the yearly diary."
            ) from exc
        raise

    entries = normalize_year_diary(year_diary, requested_year)

    if not entries:
        raise EmptyDiaryError(
            f"'{username}' has no diary entries for {requested_year} to build a Wrapped from."
        )

    return entries


def get_diary_entries(username: str) -> list[dict]:
    """Fetch legacy overview dictionaries from the complete current-year diary."""
    return [
        {"title": entry.title, "month": entry.watched_on.month}
        for entry in get_rich_diary_entries(username)
    ]
