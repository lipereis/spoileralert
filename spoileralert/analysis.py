"""Analytical layer: turns a flat list of diary entries into the handful
of headline stats the Wrapped card needs, using pandas.
"""

from __future__ import annotations

import unicodedata
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from math import fsum
from typing import cast

import pandas as pd

from spoileralert.models import (
    DiaryEntry,
    DirectorStat,
    EnhancedWrappedStats,
    EnrichedViewing,
    GenreScore,
    MovieDNA,
    TimelinePoint,
)
from spoileralert.moods import calculate_mood_profile, mood_profile_sentence
from spoileralert.personality import calculate_cinema_personality

MONTHS_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

DNA_TRAIT_PRIORITY: tuple[str, ...] = (
    "genre_fluid",
    "director_driven",
    "internationally_curious",
    "historically_diverse",
    "contemporary_focused",
    "emotionally_intense",
    "genre_centered",
    "balanced_mix",
)

_DNA_TRAIT_LABELS = {
    "genre_fluid": "Genre-fluid",
    "director_driven": "Director-driven",
    "internationally_curious": "Internationally curious",
    "historically_diverse": "Historically diverse",
    "contemporary_focused": "Contemporary focused",
    "emotionally_intense": "Emotionally intense",
    "genre_centered": "Genre-centered",
    "balanced_mix": "Balanced mix",
}

_DIVERSITY_WEIGHTS = {
    "genres": 0.30,
    "decades": 0.25,
    "countries": 0.20,
    "languages": 0.15,
    "directors": 0.10,
}

_DIVERSITY_CAPS = {
    "genres": 5,
    "decades": 5,
    "countries": 5,
    "languages": 4,
    "directors": 5,
}

_INTENSE_GENRES = {"crime", "drama", "horror", "thriller", "war"}

_MONTH_ABBREVIATIONS = (
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


@dataclass
class WrappedStats:
    username: str
    total_movies: int
    peak_month_label: str
    peak_month_count: int
    top_titles: list[str]
    monthly_counts: pd.Series


def build_dataframe(entries: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(entries, columns=["title", "month"])
    df["month_label"] = df["month"].map(MONTHS_PT.get)
    return df


def compute_stats(username: str, entries: list[dict]) -> WrappedStats:
    df = build_dataframe(entries)

    total_movies = len(df)

    monthly_counts = cast(
        pd.Series,
        df.groupby("month")["title"]
        .count()
        .reindex(range(1, 13), fill_value=0)
        .rename(index=MONTHS_PT),
    )

    if total_movies:
        peak_month_label = cast(str, monthly_counts.idxmax())
        peak_month_count = int(cast(int, monthly_counts.max()))
    else:
        peak_month_label = "Unavailable"
        peak_month_count = 0

    top_titles = df["title"].drop_duplicates().head(5).tolist()

    return WrappedStats(
        username=username,
        total_movies=total_movies,
        peak_month_label=peak_month_label,
        peak_month_count=peak_month_count,
        top_titles=top_titles,
        monthly_counts=monthly_counts,
    )


def _normalized_identity_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    characters: list[str] = []
    for character in decomposed.casefold():
        if unicodedata.combining(character):
            continue
        characters.append(character if character.isalnum() else " ")
    return " ".join("".join(characters).split())


def _valid_release_year(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 1 <= value <= 9999 else None


def _film_identity(viewing: EnrichedViewing) -> tuple[object, ...] | None:
    metadata = viewing.metadata
    if metadata is None:
        return None
    if (
        isinstance(metadata.tmdb_id, int)
        and not isinstance(metadata.tmdb_id, bool)
        and metadata.tmdb_id > 0
    ):
        return ("tmdb", metadata.tmdb_id)

    release_year = _valid_release_year(metadata.release_year)
    if release_year is None:
        release_year = _valid_release_year(viewing.diary.release_year)
    if viewing.diary.slug and viewing.diary.slug.strip():
        return (
            "slug",
            _normalized_identity_text(viewing.diary.slug),
            release_year,
        )
    title = metadata.title or viewing.diary.title
    normalized_title = _normalized_identity_text(title)
    return ("title", normalized_title, release_year) if normalized_title else None


def _distinct_enriched_viewings(
    viewings: Sequence[EnrichedViewing],
) -> tuple[EnrichedViewing, ...]:
    distinct: dict[tuple[object, ...], EnrichedViewing] = {}
    for viewing in viewings:
        identity = _film_identity(viewing)
        if identity is not None and identity not in distinct:
            distinct[identity] = viewing
    return tuple(distinct.values())


def _clean_unique(values: Sequence[str]) -> tuple[str, ...]:
    by_identity: dict[str, str] = {}
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        display = value.strip()
        key = display.casefold()
        current = by_identity.get(key)
        if current is None or (display.casefold(), display) < (current.casefold(), current):
            by_identity[key] = display
    return tuple(sorted(by_identity.values(), key=lambda value: (value.casefold(), value)))


def _rank_scores(counter: Counter[str], denominator: int) -> tuple[GenreScore, ...]:
    if denominator <= 0:
        return ()
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold(), item[0]))
    return tuple(
        GenreScore(name, count, round(count * 100.0 / denominator, 1))
        for name, count in ranked[:5]
    )


def _diversity_component(
    unique_count: int,
    covered_film_count: int,
    cap: int,
) -> float | None:
    if unique_count <= 0 or covered_film_count <= 0:
        return None
    sample_target = min(covered_film_count, cap)
    return min(1.0, unique_count / sample_target) * 100.0


def _choose_dna_trait(
    *,
    genres: Counter[str],
    genre_covered: int,
    countries: Counter[str],
    languages: Counter[str],
    directors: Counter[str],
    director_covered: int,
    release_years: Sequence[int],
    represented_decades: int,
    has_any_component: bool,
) -> str:
    genre_peak = max(genres.values(), default=0)
    director_peak = max(directors.values(), default=0)
    intense_count = sum(
        count for genre, count in genres.items() if genre.casefold() in _INTENSE_GENRES
    )
    trait_matches = {
        "genre_fluid": genre_covered >= 2 and len(genres) >= min(3, genre_covered + 1),
        "director_driven": director_covered >= 2 and director_peak / director_covered >= 0.6,
        "internationally_curious": len(countries) >= 3 or len(languages) >= 3,
        "historically_diverse": represented_decades >= 3,
        "contemporary_focused": bool(release_years)
        and sum(year >= 2015 for year in release_years) / len(release_years) >= 0.7,
        "emotionally_intense": genre_covered >= 2 and intense_count / genre_covered >= 0.6,
        "genre_centered": genre_covered >= 2 and genre_peak / genre_covered >= 0.6,
        "balanced_mix": has_any_component,
    }
    for key in DNA_TRAIT_PRIORITY:
        if trait_matches[key]:
            return _DNA_TRAIT_LABELS[key]
    return "Insufficient metadata"


def calculate_movie_dna(viewings: Sequence[EnrichedViewing]) -> MovieDNA:
    """Summarize metadata richness once per distinct enriched film.

    Genre percentages deliberately use all distinct enriched films as their
    denominator. Since a film may contain several genres, those percentages
    are independent and are not expected to total 100.
    """
    films = _distinct_enriched_viewings(tuple(viewings))
    enriched_film_count = len(films)
    genres: Counter[str] = Counter()
    decades: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    countries: Counter[str] = Counter()
    directors: Counter[str] = Counter()
    genre_covered = country_covered = language_covered = director_covered = 0
    release_years: list[int] = []

    for viewing in films:
        metadata = viewing.metadata
        assert metadata is not None

        film_genres = _clean_unique(metadata.genres)
        if film_genres:
            genre_covered += 1
            genres.update(film_genres)

        release_year = _valid_release_year(metadata.release_year)
        if release_year is None:
            release_year = _valid_release_year(viewing.diary.release_year)
        if release_year is not None:
            release_years.append(release_year)
            decade = release_year // 10 * 10
            decades[f"{decade}s"] += 1

        language = metadata.original_language
        if isinstance(language, str) and language.strip():
            language_covered += 1
            languages[language.strip()] += 1

        film_countries = _clean_unique(metadata.production_countries)
        if film_countries:
            country_covered += 1
            countries.update(film_countries)

        film_directors = _clean_unique(metadata.director_names)
        if film_directors:
            director_covered += 1
            directors.update(film_directors)

    component_inputs = {
        "genres": (len(genres), genre_covered),
        "decades": (len(decades), len(release_years)),
        "countries": (len(countries), country_covered),
        "languages": (len(languages), language_covered),
        "directors": (len(directors), director_covered),
    }
    components = {
        name: _diversity_component(unique_count, coverage, _DIVERSITY_CAPS[name])
        for name, (unique_count, coverage) in component_inputs.items()
    }
    present = [
        (score, _DIVERSITY_WEIGHTS[name])
        for name, score in components.items()
        if score is not None
    ]
    diversity_score = None
    if present:
        weight_total = fsum(weight for _, weight in present)
        weighted_score = fsum(score * weight for score, weight in present) / weight_total
        diversity_score = max(0, min(100, round(weighted_score)))

    dominant_trait = _choose_dna_trait(
        genres=genres,
        genre_covered=genre_covered,
        countries=countries,
        languages=languages,
        directors=directors,
        director_covered=director_covered,
        release_years=release_years,
        represented_decades=len(decades),
        has_any_component=bool(present),
    )
    return MovieDNA(
        top_genres=_rank_scores(genres, enriched_film_count),
        top_decades=_rank_scores(decades, enriched_film_count),
        top_languages=_rank_scores(languages, enriched_film_count),
        top_countries=_rank_scores(countries, enriched_film_count),
        represented_decades=len(decades),
        country_count=len(countries) if countries else None,
        language_count=len(languages) if languages else None,
        diversity_score=diversity_score,
        dominant_trait=dominant_trait,
        limited_sample=enriched_film_count < 5,
    )


@dataclass
class _DirectorAccumulator:
    name: str
    film_count: int
    runtimes: list[int]
    titles: set[str]
    release_years: list[int]


def calculate_director_universe(
    viewings: Sequence[EnrichedViewing],
) -> tuple[DirectorStat, ...]:
    """Aggregate every credited director over diary viewings, including rewatches."""
    items = tuple(viewings)
    enriched_viewing_count = sum(viewing.metadata is not None for viewing in items)
    if enriched_viewing_count == 0:
        return ()

    accumulators: dict[str, _DirectorAccumulator] = {}
    for viewing in items:
        metadata = viewing.metadata
        if metadata is None:
            continue
        for name in _clean_unique(metadata.director_names):
            key = name.casefold()
            accumulator = accumulators.setdefault(
                key,
                _DirectorAccumulator(name, 0, [], set(), []),
            )
            accumulator.film_count += 1
            accumulator.titles.add(viewing.diary.title)
            if (
                isinstance(metadata.runtime_minutes, int)
                and not isinstance(metadata.runtime_minutes, bool)
                and metadata.runtime_minutes > 0
            ):
                accumulator.runtimes.append(metadata.runtime_minutes)
            release_year = _valid_release_year(metadata.release_year)
            if release_year is None:
                release_year = _valid_release_year(viewing.diary.release_year)
            if release_year is not None:
                accumulator.release_years.append(release_year)

    stats = tuple(
        DirectorStat(
            name=accumulator.name,
            film_count=accumulator.film_count,
            total_runtime_minutes=(sum(accumulator.runtimes) if accumulator.runtimes else None),
            percentage=round(
                accumulator.film_count * 100.0 / enriched_viewing_count,
                1,
            ),
            titles=tuple(
                sorted(accumulator.titles, key=lambda title: (title.casefold(), title))
            ),
            average_release_year=(
                round(fsum(accumulator.release_years) / len(accumulator.release_years), 1)
                if accumulator.release_years
                else None
            ),
        )
        for accumulator in accumulators.values()
    )
    return tuple(
        sorted(
            stats,
            key=lambda item: (
                -item.film_count,
                -(item.total_runtime_minutes or -1),
                item.name.casefold(),
                item.name,
            ),
        )
    )


@dataclass(frozen=True)
class _TimelineObservation:
    watched_on: date
    rating: float | None
    rewatched: bool | None
    runtime_minutes: int | None


def _timeline_observation(
    item: DiaryEntry | EnrichedViewing,
) -> _TimelineObservation:
    if isinstance(item, EnrichedViewing):
        diary = item.diary
        runtime = item.metadata.runtime_minutes if item.metadata is not None else None
    elif isinstance(item, DiaryEntry):
        diary = item
        runtime = None
    else:
        raise TypeError("timeline entries must be DiaryEntry or EnrichedViewing records")
    valid_runtime = (
        runtime
        if isinstance(runtime, int) and not isinstance(runtime, bool) and runtime > 0
        else None
    )
    return _TimelineObservation(
        watched_on=diary.watched_on,
        rating=diary.rating,
        rewatched=diary.rewatched,
        runtime_minutes=valid_runtime,
    )


def _timeline_point(
    label: str,
    observations: Sequence[_TimelineObservation],
) -> TimelinePoint:
    if not observations:
        return TimelinePoint(label, 0, None, None, None)
    runtimes = [
        observation.runtime_minutes
        for observation in observations
        if observation.runtime_minutes is not None
    ]
    ratings = [
        observation.rating
        for observation in observations
        if observation.rating is not None
    ]
    rewatches = [
        observation.rewatched
        for observation in observations
        if observation.rewatched is not None
    ]
    return TimelinePoint(
        label=label,
        film_count=len(observations),
        total_runtime_minutes=sum(runtimes) if runtimes else None,
        average_rating=round(fsum(ratings) / len(ratings), 2) if ratings else None,
        rewatch_count=sum(value is True for value in rewatches) if rewatches else None,
    )


def _month_sequence(start: tuple[int, int], end: tuple[int, int]):
    year, month = start
    while (year, month) <= end:
        yield year, month
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1


def calculate_viewing_timeline(
    entries: Sequence[DiaryEntry | EnrichedViewing],
    grouping: str = "monthly",
) -> tuple[TimelinePoint, ...]:
    """Group viewing dates monthly or by ISO week, inserting internal gaps only."""
    if grouping not in {"monthly", "weekly"}:
        raise ValueError("grouping must be monthly or weekly")
    observations = tuple(_timeline_observation(entry) for entry in entries)
    if not observations:
        return ()

    if grouping == "monthly":
        buckets: dict[tuple[int, int], list[_TimelineObservation]] = defaultdict(list)
        for observation in observations:
            key = (observation.watched_on.year, observation.watched_on.month)
            buckets[key].append(observation)
        keys = tuple(_month_sequence(min(buckets), max(buckets)))
        crosses_year = keys[0][0] != keys[-1][0]
        return tuple(
            _timeline_point(
                (
                    f"{_MONTH_ABBREVIATIONS[month]} {year}"
                    if crosses_year
                    else _MONTH_ABBREVIATIONS[month]
                ),
                buckets.get((year, month), ()),
            )
            for year, month in keys
        )

    weekly_buckets: dict[date, list[_TimelineObservation]] = defaultdict(list)
    for observation in observations:
        monday = observation.watched_on - timedelta(days=observation.watched_on.weekday())
        weekly_buckets[monday].append(observation)
    current = min(weekly_buckets)
    final = max(weekly_buckets)
    points: list[TimelinePoint] = []
    while current <= final:
        iso_year, iso_week, _ = current.isocalendar()
        points.append(
            _timeline_point(
                f"{iso_year}-W{iso_week:02d}",
                weekly_buckets.get(current, ()),
            )
        )
        current += timedelta(days=7)
    return tuple(points)


def _active_day_insights(entries: Sequence[DiaryEntry]) -> tuple[int, int | None]:
    watched_dates = sorted({entry.watched_on for entry in entries})
    if not watched_dates:
        return 0, None
    longest = current = 1
    for previous, watched_on in zip(watched_dates, watched_dates[1:]):
        if watched_on == previous + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return len(watched_dates), longest


def _timeline_insights(
    timeline: Sequence[TimelinePoint],
) -> tuple[TimelinePoint | None, TimelinePoint | None, float | None, int | None]:
    """Return extrema and change over represented (nonzero) periods.

    Timeline order supplies the deterministic tie-break: both extrema choose
    the earliest matching period. Change is the last represented film count
    minus the first represented film count.
    """
    active_periods = tuple(point for point in timeline if point.film_count > 0)
    if not active_periods:
        return None, None, None, None
    busiest = max(active_periods, key=lambda point: point.film_count)
    least_active = min(active_periods, key=lambda point: point.film_count)
    average = round(
        sum(point.film_count for point in active_periods) / len(active_periods),
        2,
    )
    change = active_periods[-1].film_count - active_periods[0].film_count
    return busiest, least_active, average, change


def compute_enhanced_stats(
    username: str,
    entries: Sequence[DiaryEntry],
    enriched: Sequence[EnrichedViewing],
) -> EnhancedWrappedStats:
    """Compose overview and enhanced analyses without caching user-specific state."""
    diary_entries = tuple(entries)
    enriched_viewings = tuple(enriched)
    overview_entries = [
        {"title": entry.title, "month": entry.watched_on.month}
        for entry in diary_entries
    ]
    overview = compute_stats(username, overview_entries)

    metadata_by_viewing_id = {
        viewing.diary.viewing_id: viewing.metadata for viewing in enriched_viewings
    }
    timeline_viewings = tuple(
        EnrichedViewing(
            diary=entry,
            metadata=metadata_by_viewing_id.get(entry.viewing_id),
        )
        for entry in diary_entries
    )
    moods = calculate_mood_profile(enriched_viewings)
    active_days, longest_streak = _active_day_insights(diary_entries)
    timeline = calculate_viewing_timeline(timeline_viewings)
    busiest, least_active, average_per_active, first_to_last_change = (
        _timeline_insights(timeline)
    )
    return EnhancedWrappedStats(
        overview=overview,
        personality=calculate_cinema_personality(enriched_viewings),
        movie_dna=calculate_movie_dna(enriched_viewings),
        moods=moods,
        mood_sentence=mood_profile_sentence(moods),
        directors=calculate_director_universe(enriched_viewings),
        timeline=timeline,
        busiest_period=busiest,
        least_active_period=least_active,
        average_films_per_active_period=average_per_active,
        first_to_last_change=first_to_last_change,
        active_days=active_days,
        longest_streak_days=longest_streak,
        enriched_film_count=len(_distinct_enriched_viewings(enriched_viewings)),
        total_viewing_count=len(diary_entries),
    )
