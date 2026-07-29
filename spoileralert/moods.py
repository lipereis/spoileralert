"""Transparent deterministic mood inference from optional movie metadata."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence

from spoileralert.models import EnrichedViewing, MoodScore


MOOD_CATEGORIES: tuple[str, ...] = (
    "Melancholic",
    "Hopeful",
    "Tense",
    "Comforting",
    "Chaotic",
    "Romantic",
    "Dark",
    "Playful",
    "Reflective",
    "Adventurous",
)

GENRE_MOOD_WEIGHTS: Mapping[str, Mapping[str, float]] = {
    "Action": {"Adventurous": 1.2, "Chaotic": 0.6},
    "Adventure": {"Adventurous": 1.2, "Hopeful": 0.4},
    "Animation": {"Playful": 0.9, "Hopeful": 0.5},
    "Comedy": {"Playful": 1.2, "Comforting": 0.4},
    "Crime": {"Dark": 0.8, "Tense": 0.8, "Reflective": 0.2},
    "Documentary": {"Reflective": 1.0},
    "Drama": {"Reflective": 0.8, "Melancholic": 0.6},
    "Family": {"Comforting": 1.0, "Playful": 0.5},
    "Fantasy": {"Adventurous": 0.8, "Hopeful": 0.5, "Playful": 0.3},
    "History": {"Reflective": 0.9, "Melancholic": 0.3},
    "Horror": {"Tense": 1.2, "Dark": 1.0, "Chaotic": 0.7},
    "Music": {"Playful": 0.8, "Comforting": 0.5},
    "Mystery": {"Tense": 0.8, "Reflective": 0.5, "Dark": 0.3},
    "Romance": {"Romantic": 1.2, "Hopeful": 0.4, "Comforting": 0.3},
    "Science Fiction": {"Adventurous": 0.8, "Reflective": 0.6, "Chaotic": 0.2},
    "Thriller": {"Tense": 1.4, "Dark": 0.7, "Chaotic": 0.4},
    "War": {"Dark": 0.8, "Tense": 0.8, "Melancholic": 0.5},
    "Western": {"Adventurous": 0.7, "Reflective": 0.4},
}

KEYWORD_MOOD_WEIGHTS: Mapping[str, Mapping[str, float]] = {
    "adrenaline": {"Adventurous": 1.0, "Chaotic": 0.3},
    "coming of age": {"Reflective": 0.6, "Hopeful": 0.5},
    "dance": {"Playful": 1.0},
    "dystopia": {"Dark": 0.9, "Tense": 0.5},
    "family reunion": {"Comforting": 1.0},
    "friendship": {"Comforting": 1.0, "Hopeful": 0.5},
    "grief": {"Melancholic": 1.0, "Reflective": 0.5},
    "haunted house": {"Dark": 1.0, "Tense": 0.5},
    "serial killer": {"Tense": 1.0, "Dark": 0.8},
    "space exploration": {"Adventurous": 1.0, "Reflective": 0.4},
    "surrealism": {"Chaotic": 0.8, "Reflective": 0.5},
}

OVERVIEW_PHRASE_MOOD_WEIGHTS: Mapping[str, Mapping[str, float]] = {
    "falls in love": {"Romantic": 0.8},
    "haunted by the past": {"Melancholic": 0.6, "Reflective": 0.5},
    "race against time": {"Tense": 0.9},
    "struggles with grief": {"Melancholic": 0.8},
    "surreal journey": {"Chaotic": 0.7, "Reflective": 0.4},
}


def _normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    characters: list[str] = []
    for character in decomposed.casefold():
        if unicodedata.combining(character):
            continue
        characters.append(character if character.isalnum() else " ")
    return " ".join("".join(characters).split())


_NORMALIZED_GENRES = {
    _normalized_text(genre): weights for genre, weights in GENRE_MOOD_WEIGHTS.items()
}
_NORMALIZED_KEYWORDS = {
    _normalized_text(keyword): weights for keyword, weights in KEYWORD_MOOD_WEIGHTS.items()
}
_NORMALIZED_OVERVIEW_PHRASES = {
    _normalized_text(phrase): weights
    for phrase, weights in OVERVIEW_PHRASE_MOOD_WEIGHTS.items()
}


def _add_weights(scores: dict[str, float], weights: Mapping[str, float]) -> None:
    for mood, weight in sorted(weights.items()):
        if weight > 0:
            scores[mood] += float(weight)


def _largest_remainder_percentages(
    ordered_scores: Sequence[tuple[str, float]],
) -> dict[str, int]:
    total = math.fsum(score for _, score in ordered_scores)
    exact = {name: score * 100.0 / total for name, score in ordered_scores}
    percentages = {name: math.floor(value) for name, value in exact.items()}
    remaining = 100 - sum(percentages.values())
    remainder_order = sorted(
        exact,
        key=lambda name: (-(exact[name] - percentages[name]), name),
    )
    for name in remainder_order[:remaining]:
        percentages[name] += 1
    return percentages


def calculate_mood_profile(
    viewings: Sequence[EnrichedViewing],
) -> tuple[MoodScore, ...]:
    """Aggregate supported metadata signals into an exact 100% mood profile."""
    scores: dict[str, float] = defaultdict(float)
    for viewing in viewings:
        metadata = viewing.metadata
        if metadata is None:
            continue

        normalized_genres = sorted({_normalized_text(value) for value in metadata.genres})
        for genre in normalized_genres:
            weights = _NORMALIZED_GENRES.get(genre)
            if weights is not None:
                _add_weights(scores, weights)

        normalized_keywords = sorted(
            {_normalized_text(value) for value in metadata.keywords}
        )
        for keyword in normalized_keywords:
            weights = _NORMALIZED_KEYWORDS.get(keyword)
            if weights is not None:
                _add_weights(scores, weights)

        if metadata.overview:
            overview = _normalized_text(metadata.overview)
            padded_overview = f" {overview} "
            for phrase, weights in sorted(_NORMALIZED_OVERVIEW_PHRASES.items()):
                if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", padded_overview):
                    _add_weights(scores, weights)

    ordered_scores = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    if not ordered_scores:
        return ()
    percentages = _largest_remainder_percentages(ordered_scores)
    return tuple(
        MoodScore(name=name, score=round(score, 6), percentage=percentages[name])
        for name, score in ordered_scores
    )


def mood_profile_sentence(scores: Sequence[MoodScore]) -> str:
    """Describe the top three moods with fixed, order-preserving templates."""
    names = [score.name for score in scores[:3]]
    if not names:
        return "No supported mood signals were found in the available metadata."
    if len(names) == 1:
        return f"Your movie mood is led by {names[0]}."
    if len(names) == 2:
        return f"Your movie mood is led by {names[0]}, followed by {names[1]}."
    return (
        f"Your movie mood is led by {names[0]}, followed by {names[1]} "
        f"and {names[2]}."
    )
