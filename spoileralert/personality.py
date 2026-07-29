"""Deterministic cinema-personality analysis from observed viewing facts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import fsum

from spoileralert.models import CinemaPersonality, EnrichedViewing


# This order is both the approved taxonomy and the public tie-break contract.
ARCHETYPE_PRIORITY: tuple[str, ...] = (
    "explorer",
    "auteur_hunter",
    "comfort_watcher",
    "midnight_critic",
    "time_traveler",
    "festival_drifter",
    "genre_devotee",
    "blockbuster_navigator",
    "emotional_archaeologist",
    "chaos_curator",
)

ARCHETYPE_TITLES: Mapping[str, str] = {
    "explorer": "The Explorer",
    "auteur_hunter": "The Auteur Hunter",
    "comfort_watcher": "The Comfort Watcher",
    "midnight_critic": "The Midnight Critic",
    "time_traveler": "The Time Traveler",
    "festival_drifter": "The Festival Drifter",
    "genre_devotee": "The Genre Devotee",
    "blockbuster_navigator": "The Blockbuster Navigator",
    "emotional_archaeologist": "The Emotional Archaeologist",
    "chaos_curator": "The Chaos Curator",
}


@dataclass(frozen=True)
class _ArchetypeCopy:
    subtitle: str
    description: str
    accent_color: str


_ARCHETYPE_COPY: Mapping[str, _ArchetypeCopy] = {
    "explorer": _ArchetypeCopy(
        "Your watchlist crosses borders, eras, and categories.",
        "Variety is the through-line in the films you chose.",
        "#69D2E7",
    ),
    "auteur_hunter": _ArchetypeCopy(
        "You follow filmmakers, not just films.",
        "Recurring director credits reveal a taste for a distinct creative voice.",
        "#F4A261",
    ),
    "comfort_watcher": _ArchetypeCopy(
        "Familiar stories still have something to give.",
        "Rewatches and comforting genres shape this return-friendly diary.",
        "#F15BB5",
    ),
    "midnight_critic": _ArchetypeCopy(
        "You make room for cinema's darker, longer shadows.",
        "Dark genres and substantial runtimes lead this observed profile.",
        "#6D597A",
    ),
    "time_traveler": _ArchetypeCopy(
        "Release dates are invitations, not boundaries.",
        "Older films and a broad release-year range keep film history in conversation.",
        "#9B5DE5",
    ),
    "festival_drifter": _ArchetypeCopy(
        "Your cinema map wanders beyond one familiar lane.",
        "International and festival-associated signals guide this portrait.",
        "#00F5D4",
    ),
    "genre_devotee": _ArchetypeCopy(
        "One cinematic lane keeps calling you back.",
        "A clear genre concentration gives your diary its signature.",
        "#E76F51",
    ),
    "blockbuster_navigator": _ArchetypeCopy(
        "You keep a compass pointed toward cinema's big currents.",
        "Recent releases and observed blockbuster genres lead this profile.",
        "#00BBF9",
    ),
    "emotional_archaeologist": _ArchetypeCopy(
        "You dig for the human feeling beneath the story.",
        "Emotion-centered genres recur across the films you chose.",
        "#FEE440",
    ),
    "chaos_curator": _ArchetypeCopy(
        "You collect films that refuse to sit still.",
        "Volatile genres and genre variety give this diary its restless edge.",
        "#577590",
    ),
}

_FULL_SAMPLE_SIZE = 5
_LIMITED_TITLE = "Your Cinema Story Is Taking Shape"

_COMFORT_GENRES = frozenset({"Animation", "Comedy", "Family", "Music", "Romance"})
_DARK_GENRES = frozenset({"Crime", "Horror", "Mystery", "Thriller", "War"})
_FESTIVAL_GENRES = frozenset({"Documentary", "Drama", "History"})
_BLOCKBUSTER_GENRES = frozenset({"Action", "Adventure", "Fantasy", "Science Fiction"})
_EMOTIONAL_GENRES = frozenset({"Drama", "Family", "History", "Romance"})
_CHAOTIC_GENRES = frozenset({"Action", "Crime", "Horror", "Mystery", "Thriller"})


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _weighted_available(
    weighted_features: Sequence[tuple[float | None, float]],
) -> float | None:
    available = [(value, weight) for value, weight in weighted_features if value is not None]
    if not available:
        return None
    total_weight = fsum(weight for _, weight in available)
    return fsum(_clamp(value) * weight for value, weight in available) / total_weight


def _normalized_breadth(unique_count: int, observed_count: int, cap: int) -> float | None:
    if observed_count <= 0:
        return None
    return _clamp(unique_count / cap)


def _stable_counter_peak(counter: Counter[str]) -> tuple[str, int] | None:
    if not counter:
        return None
    return min(counter.items(), key=lambda item: (-item[1], item[0].casefold(), item[0]))


def _group_share(
    observed_sets: Sequence[frozenset[str]], supported: frozenset[str]
) -> float | None:
    if not observed_sets:
        return None
    return sum(bool(values & supported) for values in observed_sets) / len(observed_sets)


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or f"{singular}s")


def select_archetype(scores: Mapping[str, float]) -> str:
    """Select the highest approved score, breaking ties by public priority."""
    declared_scores = [(key, float(scores[key])) for key in ARCHETYPE_PRIORITY if key in scores]
    if not declared_scores:
        raise ValueError("scores must contain at least one declared archetype")
    highest = max(score for _, score in declared_scores)
    return next(key for key, score in declared_scores if score == highest)


def _limited_personality(viewings: Sequence[EnrichedViewing]) -> CinemaPersonality:
    viewing_count = len(viewings)
    enriched_count = sum(viewing.metadata is not None for viewing in viewings)
    return CinemaPersonality(
        key="limited_sample",
        title=_LIMITED_TITLE,
        subtitle="There is not enough observed film data for a reliable archetype yet.",
        description="Keep logging films; the portrait will become clearer without guessing at missing metadata.",
        evidence=(
            f"{viewing_count} diary {_plural(viewing_count, 'viewing')}",
            f"{enriched_count} enriched {_plural(enriched_count, 'film')}",
        ),
        accent_color="#9CA3AF",
        limited_sample=True,
    )


def calculate_cinema_personality(
    viewings: Sequence[EnrichedViewing],
) -> CinemaPersonality:
    """Return one approved archetype using only present diary/metadata signals."""
    items = tuple(viewings)
    enriched = tuple(viewing for viewing in items if viewing.metadata is not None)
    if not items or not enriched:
        return _limited_personality(items)

    genre_counts: Counter[str] = Counter()
    country_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    director_counts: Counter[str] = Counter()
    genre_sets: list[frozenset[str]] = []
    country_sets: list[frozenset[str]] = []
    director_observations = 0
    runtimes: list[int] = []
    release_years: list[int] = []

    for viewing in enriched:
        metadata = viewing.metadata
        assert metadata is not None
        genres = frozenset(metadata.genres)
        if genres:
            genre_sets.append(genres)
            genre_counts.update(genres)
        countries = frozenset(metadata.production_countries)
        if countries:
            country_sets.append(countries)
            country_counts.update(countries)
        if metadata.original_language:
            language_counts[metadata.original_language] += 1
        directors = frozenset(metadata.director_names)
        if directors:
            director_observations += 1
            director_counts.update(directors)
        if metadata.runtime_minutes is not None and metadata.runtime_minutes > 0:
            runtimes.append(metadata.runtime_minutes)
        release_year = metadata.release_year or viewing.diary.release_year
        if release_year is not None and release_year > 0:
            release_years.append(release_year)

    genre_observations = len(genre_sets)
    country_observations = len(country_sets)
    language_observations = sum(language_counts.values())
    genre_peak = _stable_counter_peak(genre_counts)
    director_peak = _stable_counter_peak(director_counts)
    decades = {year // 10 * 10 for year in release_years}

    genre_breadth = _normalized_breadth(len(genre_counts), genre_observations, 6)
    country_breadth = _normalized_breadth(len(country_counts), country_observations, 6)
    language_breadth = _normalized_breadth(len(language_counts), language_observations, 4)
    decade_breadth = _normalized_breadth(len(decades), len(release_years), 6)
    genre_concentration = (
        genre_peak[1] / genre_observations if genre_peak is not None else None
    )
    director_concentration = (
        director_peak[1] / director_observations if director_peak is not None else None
    )
    director_repeat_share = (
        (director_peak[1] - 1) / max(1, director_observations - 1)
        if director_peak is not None and director_observations > 1
        else (0.0 if director_peak is not None else None)
    )
    era_span = (
        _clamp((max(release_years) - min(release_years)) / 50)
        if release_years
        else None
    )
    older_share = (
        sum(year < 2000 for year in release_years) / len(release_years)
        if release_years
        else None
    )
    known_rewatches = [
        viewing.diary.rewatched for viewing in items if viewing.diary.rewatched is not None
    ]
    rewatch_share = (
        sum(value is True for value in known_rewatches) / len(known_rewatches)
        if known_rewatches
        else None
    )
    runtime_scale = (
        _clamp((fsum(runtimes) / len(runtimes) - 90) / 90) if runtimes else None
    )
    non_english_share = (
        sum(language.casefold() != "en" for language in language_counts.elements())
        / language_observations
        if language_observations
        else None
    )
    non_us_country_share = (
        sum(
            any(country.casefold() not in {"united states", "united states of america"} for country in countries)
            for countries in country_sets
        )
        / country_observations
        if country_observations
        else None
    )
    dated_viewings: list[tuple[int, int]] = []
    for viewing in items:
        metadata_year = viewing.metadata.release_year if viewing.metadata is not None else None
        release_year = metadata_year or viewing.diary.release_year
        if release_year is not None:
            dated_viewings.append((release_year, viewing.diary.watched_on.year))
    recent_share = (
        sum(year >= watched_year - 2 for year, watched_year in dated_viewings)
        / len(dated_viewings)
        if dated_viewings
        else None
    )

    comfort_share = _group_share(genre_sets, _COMFORT_GENRES)
    dark_share = _group_share(genre_sets, _DARK_GENRES)
    festival_genre_share = _group_share(genre_sets, _FESTIVAL_GENRES)
    blockbuster_genre_share = _group_share(genre_sets, _BLOCKBUSTER_GENRES)
    emotional_share = _group_share(genre_sets, _EMOTIONAL_GENRES)
    chaotic_share = _group_share(genre_sets, _CHAOTIC_GENRES)

    scores = {
        "explorer": _weighted_available(
            ((genre_breadth, 0.30), (country_breadth, 0.30), (language_breadth, 0.25), (decade_breadth, 0.15))
        ),
        "auteur_hunter": _weighted_available(
            ((director_concentration, 0.70), (director_repeat_share, 0.30))
        ),
        "comfort_watcher": _weighted_available(((rewatch_share, 0.70), (comfort_share, 0.30))),
        "midnight_critic": _weighted_available(
            (((dark_share * 0.85) if dark_share is not None else None, 0.75), (runtime_scale, 0.25))
        ),
        "time_traveler": _weighted_available(((era_span, 0.60), (older_share, 0.40))),
        "festival_drifter": _weighted_available(
            ((non_english_share, 0.35), (non_us_country_share, 0.25), (festival_genre_share, 0.25), (language_breadth, 0.15))
        ),
        "genre_devotee": _weighted_available(((genre_concentration, 1.0),)),
        "blockbuster_navigator": _weighted_available(
            ((recent_share, 0.45), (blockbuster_genre_share, 0.40), (runtime_scale, 0.15))
        ),
        "emotional_archaeologist": _weighted_available(
            ((emotional_share, 0.75), (older_share, 0.25))
        ),
        "chaos_curator": _weighted_available(
            (((chaotic_share * 0.65) if chaotic_share is not None else None, 0.75), (genre_breadth, 0.25))
        ),
    }
    positive_scores = {
        key: score for key, score in scores.items() if score is not None and score > 0
    }
    if not positive_scores:
        return _limited_personality(items)

    selected = select_archetype(positive_scores)
    copy = _ARCHETYPE_COPY[selected]
    title = ARCHETYPE_TITLES[selected]
    evidence: list[str] = []

    if selected == "explorer":
        if genre_observations:
            evidence.append(f"{len(genre_counts)} observed genres across {genre_observations} films")
        if country_observations:
            evidence.append(f"{len(country_counts)} observed countries across {country_observations} films")
        if language_observations:
            evidence.append(f"{len(language_counts)} observed languages across {language_observations} films")
        if release_years:
            evidence.append(f"{len(decades)} release decades across {len(release_years)} dated films")
    elif selected == "auteur_hunter" and director_peak is not None:
        evidence = [
            f"{director_peak[0]} directed {director_peak[1]} of {director_observations} credited viewings",
            f"{len(director_counts)} observed directors",
        ]
    elif selected == "comfort_watcher":
        rewatch_count = sum(value is True for value in known_rewatches)
        evidence = [f"{rewatch_count} of {len(known_rewatches)} viewings marked as rewatches"]
    elif selected == "midnight_critic":
        dark_count = sum(bool(genres & _DARK_GENRES) for genres in genre_sets)
        evidence = [f"{dark_count} of {genre_observations} films with genre data use dark genres"]
        if runtimes:
            evidence.append(f"{len(runtimes)} films have an observed average runtime of {fsum(runtimes) / len(runtimes):.0f} minutes")
    elif selected == "time_traveler":
        evidence = [f"{len(decades)} release decades across {len(release_years)} dated films"]
        if release_years:
            evidence.append(f"Observed releases span {min(release_years)} to {max(release_years)}")
    elif selected == "festival_drifter":
        if language_observations:
            non_english_count = sum(language.casefold() != "en" for language in language_counts.elements())
            evidence.append(f"{non_english_count} of {language_observations} films use an observed non-English language")
        if country_observations:
            evidence.append(f"{len(country_counts)} observed production countries")
    elif selected == "genre_devotee" and genre_peak is not None:
        title = f"The {genre_peak[0]} Devotee"
        evidence = [
            f"{genre_peak[0]} appears in {genre_peak[1]} of {genre_observations} films with genre data",
            f"{len(genre_counts)} observed genres",
        ]
    elif selected == "blockbuster_navigator":
        recent_count = sum(year >= watched_year - 2 for year, watched_year in dated_viewings)
        evidence = [f"{recent_count} of {len(dated_viewings)} dated films were recent when watched"]
        if genre_observations:
            blockbuster_count = sum(bool(genres & _BLOCKBUSTER_GENRES) for genres in genre_sets)
            evidence.append(f"{blockbuster_count} of {genre_observations} films with genre data use blockbuster genres")
    elif selected == "emotional_archaeologist":
        emotional_count = sum(bool(genres & _EMOTIONAL_GENRES) for genres in genre_sets)
        evidence = [f"{emotional_count} of {genre_observations} films with genre data use emotional genres"]
    else:
        chaotic_count = sum(bool(genres & _CHAOTIC_GENRES) for genres in genre_sets)
        evidence = [f"{chaotic_count} of {genre_observations} films with genre data use volatile genres"]

    return CinemaPersonality(
        key=selected,
        title=title,
        subtitle=copy.subtitle,
        description=copy.description,
        evidence=tuple(evidence),
        accent_color=copy.accent_color,
        limited_sample=len(enriched) < _FULL_SAMPLE_SIZE,
    )
