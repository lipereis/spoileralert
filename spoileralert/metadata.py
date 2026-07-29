"""Optional TMDB enrichment for immutable diary viewings.

This module deliberately has no UI dependency. All remote failures are treated as
recoverable because metadata must never be required to generate a Wrapped.
"""

from __future__ import annotations

import os
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from spoileralert.models import DiaryEntry, EnrichedViewing, MovieMetadata


_API_BASE_URL = "https://api.themoviedb.org/3"
_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
_REQUEST_TIMEOUT = (3.05, 10.0)
_MINIMUM_CONFIDENCE = 0.85
_POSTER_PATH = re.compile(r"^/(?!/)(?!.*\.\.)[A-Za-z0-9_./-]+\.(?:jpe?g|png|webp)$", re.IGNORECASE)
_STREAMLIT_MISSING_SECRET_ERRORS = {
    ("streamlit.errors", "StreamlitSecretNotFoundError"),
}


def _is_unavailable_secrets_error(exc: Exception) -> bool:
    if isinstance(exc, (FileNotFoundError, PermissionError)):
        return True
    return any(
        (base.__module__, base.__name__) in _STREAMLIT_MISSING_SECRET_ERRORS
        for base in type(exc).__mro__
    )


def get_tmdb_api_key(
    secrets: Mapping[str, object] | None = None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Return the first non-empty key from secrets, then the environment."""
    if secrets is not None:
        try:
            value = secrets.get("TMDB_API_KEY")
        except Exception as exc:
            if not _is_unavailable_secrets_error(exc):
                raise
            value = None
        if isinstance(value, str) and value.strip():
            return value.strip()

    environment = os.environ if environ is None else environ
    value = environment.get("TMDB_API_KEY")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def normalize_title(value: str) -> str:
    """Create a deterministic comparison form without guessing title aliases."""
    decomposed = unicodedata.normalize("NFKD", value)
    characters: list[str] = []
    for character in decomposed.casefold():
        if unicodedata.combining(character):
            continue
        characters.append(character if character.isalnum() else " ")
    return " ".join("".join(characters).split())


def _release_year(value: object) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value).year
    except ValueError:
        return None


def _candidate_titles(candidate: Mapping[str, object]) -> tuple[str, ...]:
    titles: list[str] = []
    for field in ("title", "original_title"):
        value = candidate.get(field)
        if isinstance(value, str) and value.strip():
            titles.append(value)
    return tuple(titles)


def _confidence(
    title: str,
    release_year: int | None,
    candidate: Mapping[str, object],
) -> float:
    expected_title = normalize_title(title)
    if not expected_title or all(
        normalize_title(candidate_title) != expected_title
        for candidate_title in _candidate_titles(candidate)
    ):
        return 0.0

    release_date = candidate.get("release_date")
    candidate_year = _release_year(release_date)
    has_malformed_date = release_date is not None and (
        not isinstance(release_date, str)
        or (bool(release_date.strip()) and candidate_year is None)
    )
    if has_malformed_date:
        return 0.0
    if release_year is None or candidate_year is None:
        return _MINIMUM_CONFIDENCE
    difference = abs(candidate_year - release_year)
    if difference == 0:
        return 1.0
    if difference == 1:
        return 0.9
    return 0.0


def match_confidence(entry: DiaryEntry, candidate: Mapping[str, object]) -> float:
    """Score exact normalized title matches with deterministic year handling."""
    return _confidence(entry.title, entry.release_year, candidate)


def _request_json(session: Any, url: str, params: dict[str, object]) -> object | None:
    try:
        response = session.get(url, params=params, timeout=_REQUEST_TIMEOUT)
        if getattr(response, "status_code", None) != 200:
            return None
        return response.json()
    except Exception:
        return None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _named_items(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    names: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = _optional_text(item.get("name"))
        if name is not None and name not in names:
            names.append(name)
    return tuple(names)


def _poster_url(value: object) -> str | None:
    if not isinstance(value, str) or _POSTER_PATH.fullmatch(value) is None:
        return None
    return f"{_POSTER_BASE_URL}{value}"


def _valid_search_candidate(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping) or _positive_int(value.get("id")) is None:
        return None
    if not _candidate_titles(value):
        return None
    release_date = value.get("release_date")
    if release_date is not None and not isinstance(release_date, str):
        return None
    if isinstance(release_date, str) and release_date.strip() and _release_year(release_date) is None:
        return None
    return value


def _select_candidate(
    results: object,
    title: str,
    release_year: int | None,
) -> tuple[Mapping[str, object], float] | None:
    if not isinstance(results, list):
        return None
    scored: list[tuple[Mapping[str, object], float]] = []
    for raw_candidate in results:
        candidate = _valid_search_candidate(raw_candidate)
        if candidate is None:
            continue
        confidence = _confidence(title, release_year, candidate)
        if confidence >= _MINIMUM_CONFIDENCE:
            scored.append((candidate, confidence))
    if not scored:
        return None

    highest_confidence = max(confidence for _, confidence in scored)
    best = [item for item in scored if item[1] == highest_confidence]
    if len(best) != 1:
        return None
    return best[0]


def lookup_movie_metadata(
    title: str,
    release_year: int | None,
    api_key: str,
    *,
    session=None,
) -> MovieMetadata | None:
    """Look up one movie, returning ``None`` for every recoverable failure."""
    if not isinstance(api_key, str) or not api_key.strip() or not normalize_title(title):
        return None

    if session is None:
        import requests

        session = requests

    common_params: dict[str, object] = {"api_key": api_key.strip()}
    search_params = {**common_params, "query": title}
    if isinstance(release_year, int) and not isinstance(release_year, bool):
        search_params["year"] = release_year

    search_payload = _request_json(
        session,
        f"{_API_BASE_URL}/search/movie",
        search_params,
    )
    if not isinstance(search_payload, Mapping):
        return None
    selected = _select_candidate(search_payload.get("results"), title, release_year)
    if selected is None:
        return None
    candidate, confidence = selected
    tmdb_id = _positive_int(candidate.get("id"))
    if tmdb_id is None:
        return None

    detail_payload = _request_json(
        session, f"{_API_BASE_URL}/movie/{tmdb_id}", common_params
    )
    if not isinstance(detail_payload, Mapping):
        return None

    detail_id = _positive_int(detail_payload.get("id"))
    detail_title = _optional_text(detail_payload.get("title"))
    genres = _named_items(detail_payload.get("genres"))
    countries = _named_items(detail_payload.get("production_countries"))
    detail_confidence = _confidence(title, release_year, detail_payload)
    if (
        detail_id != tmdb_id
        or detail_title is None
        or genres is None
        or countries is None
        or detail_confidence < _MINIMUM_CONFIDENCE
    ):
        return None

    credits_payload = _request_json(
        session, f"{_API_BASE_URL}/movie/{tmdb_id}/credits", common_params
    )
    keywords_payload = _request_json(
        session, f"{_API_BASE_URL}/movie/{tmdb_id}/keywords", common_params
    )
    if not isinstance(credits_payload, Mapping) or not isinstance(
        keywords_payload, Mapping
    ):
        return None

    credits_id = _positive_int(credits_payload.get("id"))
    keywords_id = _positive_int(keywords_payload.get("id"))
    if credits_id is None or keywords_id is None:
        return None

    crew = credits_payload.get("crew")
    if credits_id == tmdb_id and not isinstance(crew, list):
        return None
    if credits_id != tmdb_id:
        crew = []

    keywords_blob = keywords_payload.get("keywords", keywords_payload.get("results"))
    if keywords_id == tmdb_id:
        keywords = _named_items(keywords_blob)
        if keywords is None:
            return None
    else:
        keywords = ()

    directors: list[str] = []
    for member in crew:
        if not isinstance(member, Mapping) or member.get("job") != "Director":
            continue
        name = _optional_text(member.get("name"))
        if name is not None and name not in directors:
            directors.append(name)

    runtime = _positive_int(detail_payload.get("runtime"))
    detail_release_year = _release_year(detail_payload.get("release_date"))
    return MovieMetadata(
        tmdb_id=tmdb_id,
        title=detail_title,
        release_year=detail_release_year,
        genres=genres,
        director_names=tuple(directors),
        runtime_minutes=runtime,
        original_language=_optional_text(detail_payload.get("original_language")),
        production_countries=countries,
        keywords=keywords,
        overview=_optional_text(detail_payload.get("overview")),
        poster_url=_poster_url(detail_payload.get("poster_path")),
        match_confidence=min(confidence, detail_confidence),
    )


def enrich_diary_entries(
    entries: Sequence[DiaryEntry],
    api_key: str | None,
    *,
    lookup=lookup_movie_metadata,
) -> list[EnrichedViewing]:
    """Enrich unique movies while retaining each individual diary viewing."""
    if not isinstance(api_key, str) or not api_key.strip():
        return [EnrichedViewing(diary=entry, metadata=None) for entry in entries]

    metadata_by_key: dict[tuple[str, int | None], MovieMetadata | None] = {}
    for entry in entries:
        key = (normalize_title(entry.title), entry.release_year)
        if key in metadata_by_key:
            continue
        try:
            metadata = lookup(entry.title, entry.release_year, api_key.strip())
        except Exception:
            metadata = None
        metadata_by_key[key] = metadata if isinstance(metadata, MovieMetadata) else None

    return [
        EnrichedViewing(
            diary=entry,
            metadata=metadata_by_key[(normalize_title(entry.title), entry.release_year)],
        )
        for entry in entries
    ]
