"""Immutable domain records shared by the enhanced analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spoileralert.analysis import WrappedStats


@dataclass(frozen=True)
class DiaryEntry:
    viewing_id: str
    title: str
    release_year: int | None
    slug: str | None
    watched_on: date
    rating: float | None
    rewatched: bool | None


@dataclass(frozen=True)
class MovieMetadata:
    tmdb_id: int | None
    title: str
    release_year: int | None
    genres: tuple[str, ...] = ()
    director_names: tuple[str, ...] = ()
    runtime_minutes: int | None = None
    original_language: str | None = None
    production_countries: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    overview: str | None = None
    poster_url: str | None = None
    match_confidence: float | None = None


@dataclass(frozen=True)
class EnrichedViewing:
    diary: DiaryEntry
    metadata: MovieMetadata | None


@dataclass(frozen=True)
class GenreScore:
    name: str
    count: int
    percentage: float


@dataclass(frozen=True)
class MoodScore:
    name: str
    score: float
    percentage: int


@dataclass(frozen=True)
class DirectorStat:
    name: str
    film_count: int
    total_runtime_minutes: int | None
    percentage: float
    titles: tuple[str, ...]
    average_release_year: float | None


@dataclass(frozen=True)
class TimelinePoint:
    label: str
    film_count: int
    total_runtime_minutes: int | None
    average_rating: float | None
    rewatch_count: int | None


@dataclass(frozen=True)
class CinemaPersonality:
    key: str
    title: str
    subtitle: str
    description: str
    evidence: tuple[str, ...]
    accent_color: str
    limited_sample: bool


@dataclass(frozen=True)
class MovieDNA:
    top_genres: tuple[GenreScore, ...]
    top_decades: tuple[GenreScore, ...]
    top_languages: tuple[GenreScore, ...]
    top_countries: tuple[GenreScore, ...]
    represented_decades: int
    country_count: int | None
    language_count: int | None
    diversity_score: int | None
    dominant_trait: str
    limited_sample: bool


@dataclass(frozen=True)
class EnhancedWrappedStats:
    overview: WrappedStats
    personality: CinemaPersonality
    movie_dna: MovieDNA
    moods: tuple[MoodScore, ...]
    mood_sentence: str
    directors: tuple[DirectorStat, ...]
    timeline: tuple[TimelinePoint, ...]
    busiest_period: TimelinePoint | None
    least_active_period: TimelinePoint | None
    average_films_per_active_period: float | None
    first_to_last_change: int | None
    active_days: int
    longest_streak_days: int | None
    enriched_film_count: int
    total_viewing_count: int


@dataclass(frozen=True)
class RenderedCard:
    slug: str
    title: str
    filename: str
    png_bytes: bytes
