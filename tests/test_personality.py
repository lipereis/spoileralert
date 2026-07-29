from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date

from spoileralert.models import DiaryEntry, EnrichedViewing, MovieMetadata
from spoileralert.personality import (
    ARCHETYPE_PRIORITY,
    ARCHETYPE_TITLES,
    calculate_cinema_personality,
    select_archetype,
)


def _viewing(
    viewing_id: int,
    *,
    title: str | None = None,
    release_year: int | None = 2020,
    genres: tuple[str, ...] = (),
    directors: tuple[str, ...] = (),
    language: str | None = "en",
    countries: tuple[str, ...] = ("United States",),
    runtime: int | None = 100,
    rating: float | None = None,
    rewatched: bool | None = False,
    enriched: bool = True,
) -> EnrichedViewing:
    movie_title = title or f"Film {viewing_id}"
    diary = DiaryEntry(
        viewing_id=str(viewing_id),
        title=movie_title,
        release_year=release_year,
        slug=f"film-{viewing_id}",
        watched_on=date(2026, 1, viewing_id),
        rating=rating,
        rewatched=rewatched,
    )
    metadata = None
    if enriched:
        metadata = MovieMetadata(
            tmdb_id=viewing_id,
            title=movie_title,
            release_year=release_year,
            genres=genres,
            director_names=directors,
            runtime_minutes=runtime,
            original_language=language,
            production_countries=countries,
        )
    return EnrichedViewing(diary=diary, metadata=metadata)


def _explorer_fixture() -> tuple[EnrichedViewing, ...]:
    facts = (
        ("Drama", "France", "fr", 1974),
        ("Comedy", "Japan", "ja", 1985),
        ("Horror", "Brazil", "pt", 1996),
        ("Documentary", "Senegal", "wo", 2007),
        ("Animation", "Spain", "es", 2018),
        ("Science Fiction", "South Korea", "ko", 2025),
    )
    return tuple(
        _viewing(
            index,
            release_year=year,
            genres=(genre,),
            directors=(f"Director {index}",),
            language=language,
            countries=(country,),
        )
        for index, (genre, country, language, year) in enumerate(facts, 1)
    )


class PersonalityTests(unittest.TestCase):
    def test_declares_exactly_ten_stable_archetypes(self):
        """Would fail if the public tie-break contract drifted or duplicated keys."""
        expected = (
            ("explorer", "The Explorer"),
            ("auteur_hunter", "The Auteur Hunter"),
            ("comfort_watcher", "The Comfort Watcher"),
            ("midnight_critic", "The Midnight Critic"),
            ("time_traveler", "The Time Traveler"),
            ("festival_drifter", "The Festival Drifter"),
            ("genre_devotee", "The Genre Devotee"),
            ("blockbuster_navigator", "The Blockbuster Navigator"),
            ("emotional_archaeologist", "The Emotional Archaeologist"),
            ("chaos_curator", "The Chaos Curator"),
        )

        self.assertEqual(ARCHETYPE_PRIORITY, tuple(key for key, _ in expected))
        self.assertEqual(
            tuple((key, ARCHETYPE_TITLES[key]) for key in ARCHETYPE_PRIORITY),
            expected,
        )

    def test_explorer_wins_for_broad_genres_countries_languages_and_decades(self):
        """Would fail if breadth signals were ignored or replaced with concentration."""
        personality = calculate_cinema_personality(_explorer_fixture())

        self.assertEqual(personality.key, "explorer")
        self.assertGreaterEqual(len(personality.evidence), 2)
        self.assertTrue(any("6" in item and "genres" in item for item in personality.evidence))
        self.assertFalse(personality.limited_sample)

    def test_auteur_hunter_wins_for_a_repeated_observed_director(self):
        """Would fail if repeated director credits did not affect the result."""
        viewings = tuple(
            _viewing(
                index,
                genres=(genre,),
                directors=("Agnes Example",),
                release_year=2010 + index,
            )
            for index, genre in enumerate(("Drama", "Comedy", "Horror", "Romance"), 1)
        )

        personality = calculate_cinema_personality(viewings)

        self.assertEqual(personality.key, "auteur_hunter")
        self.assertTrue(any("Agnes Example" in item and "4" in item for item in personality.evidence))
        self.assertTrue(personality.limited_sample)

    def test_genre_devotee_title_adapts_to_the_observed_dominant_genre(self):
        """Would fail if the visible archetype title fabricated or hid its genre."""
        viewings = tuple(
            _viewing(
                index,
                genres=("Horror",),
                directors=(f"Director {index}",),
                release_year=2020 + index,
            )
            for index in range(1, 5)
        )

        personality = calculate_cinema_personality(viewings)

        self.assertEqual(personality.key, "genre_devotee")
        self.assertIn("Horror", personality.title)
        self.assertTrue(any("4 of 4" in item and "Horror" in item for item in personality.evidence))
        self.assertTrue(personality.limited_sample)

    def test_blockbuster_navigator_uses_an_observed_metadata_release_year(self):
        """Would fail if a metadata year vanished when the diary omitted its year."""
        viewings = []
        for index in range(1, 4):
            viewing = _viewing(index, release_year=None)
            assert viewing.metadata is not None
            viewings.append(
                replace(
                    viewing,
                    metadata=replace(viewing.metadata, release_year=2025),
                )
            )

        personality = calculate_cinema_personality(tuple(viewings))

        self.assertEqual(personality.key, "blockbuster_navigator")
        self.assertEqual(
            personality.evidence,
            ("3 of 3 dated films were recent when watched",),
        )
        self.assertTrue(personality.limited_sample)

    def test_tie_breaking_uses_declared_priority_not_mapping_order(self):
        """Would fail if dict insertion order decided equal archetype scores."""
        forward = {"time_traveler": 0.5, "explorer": 0.5}
        reverse = {"explorer": 0.5, "time_traveler": 0.5}

        self.assertEqual(select_archetype(forward), "explorer")
        self.assertEqual(select_archetype(reverse), "explorer")

    def test_one_unenriched_film_returns_an_honest_limited_sample(self):
        """Would fail if missing metadata were silently converted into taste claims."""
        personality = calculate_cinema_personality((_viewing(1, enriched=False),))

        self.assertEqual(personality.key, "limited_sample")
        self.assertTrue(personality.limited_sample)
        self.assertEqual(personality.evidence, ("1 diary viewing", "0 enriched films"))

    def test_title_only_metadata_without_positive_signals_is_limited(self):
        """Would fail if unavailable features won an all-zero archetype tie."""
        viewings = tuple(
            EnrichedViewing(
                diary=DiaryEntry(
                    viewing_id=str(index),
                    title=f"Film {index}",
                    release_year=None,
                    slug=None,
                    watched_on=date(2026, 1, 4 + index),
                    rating=None,
                    rewatched=None,
                ),
                metadata=MovieMetadata(
                    tmdb_id=index,
                    title=f"Film {index}",
                    release_year=None,
                ),
            )
            for index in range(1, 4)
        )

        personality = calculate_cinema_personality(viewings)

        self.assertEqual(personality.key, "limited_sample")
        self.assertTrue(personality.limited_sample)
        self.assertEqual(personality.evidence, ("3 diary viewings", "3 enriched films"))

    def test_one_enriched_film_can_make_a_visibly_limited_inference(self):
        """Would fail if a safe one-film inference hid its limited sample."""
        viewings = (
            _viewing(
                1,
                release_year=None,
                genres=("Horror",),
                directors=(),
                language=None,
                countries=(),
                runtime=None,
                rewatched=None,
            ),
        )

        personality = calculate_cinema_personality(viewings)

        self.assertEqual(personality.key, "genre_devotee")
        self.assertTrue(personality.limited_sample)

    def test_returned_personality_record_is_immutable(self):
        """Would fail if callers could mutate an analysis result after calculation."""
        personality = calculate_cinema_personality(_explorer_fixture())

        with self.assertRaises(FrozenInstanceError):
            personality.title = "Changed"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
