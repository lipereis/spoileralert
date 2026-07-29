from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date

from spoileralert.analysis import DNA_TRAIT_PRIORITY, calculate_movie_dna
from spoileralert.models import DiaryEntry, EnrichedViewing, GenreScore, MovieMetadata


def _viewing(
    viewing_id: str,
    *,
    title: str,
    tmdb_id: int | None,
    release_year: int | None,
    genres: tuple[str, ...] = (),
    directors: tuple[str, ...] = (),
    language: str | None = None,
    countries: tuple[str, ...] = (),
) -> EnrichedViewing:
    diary = DiaryEntry(
        viewing_id=viewing_id,
        title=title,
        release_year=release_year,
        slug=title.casefold().replace(" ", "-"),
        watched_on=date(2026, 1, int(viewing_id)),
        rating=None,
        rewatched=False,
    )
    return EnrichedViewing(
        diary=diary,
        metadata=MovieMetadata(
            tmdb_id=tmdb_id,
            title=title,
            release_year=release_year,
            genres=genres,
            director_names=directors,
            original_language=language,
            production_countries=countries,
        ),
    )


class MovieDNATests(unittest.TestCase):
    def test_multi_genre_percentages_use_distinct_enriched_film_denominator(self):
        """Would fail if genres used total assignments or metadata-bearing rows."""
        first = _viewing(
            "1",
            title="One",
            tmdb_id=1,
            release_year=2016,
            genres=("Drama", "Romance"),
        )
        second = _viewing(
            "2",
            title="Two",
            tmdb_id=2,
            release_year=2018,
            genres=("Drama",),
        )

        dna = calculate_movie_dna((first, second))

        self.assertEqual(dna.top_genres[0], GenreScore("Drama", 2, 100.0))
        self.assertEqual(dna.top_genres[1], GenreScore("Romance", 1, 50.0))

    def test_rewatch_does_not_inflate_metadata_richness(self):
        """Would fail if a repeat viewing counted as another genre or decade film."""
        original = _viewing(
            "1",
            title="Arrival",
            tmdb_id=329865,
            release_year=2016,
            genres=("Drama", "Science Fiction"),
            directors=("Denis Villeneuve",),
            language="en",
            countries=("United States",),
        )
        rewatch = replace(
            original,
            diary=replace(
                original.diary,
                viewing_id="2",
                watched_on=date(2026, 1, 2),
                rewatched=True,
            ),
        )

        once = calculate_movie_dna((original,))
        twice = calculate_movie_dna((original, rewatch))

        self.assertEqual(twice, once)
        self.assertTrue(twice.limited_sample)

    def test_missing_components_are_omitted_and_score_stays_bounded(self):
        """Would fail if absent countries or languages were scored as zero."""
        full = _viewing(
            "1",
            title="One",
            tmdb_id=1,
            release_year=1980,
            genres=("Drama",),
            directors=("Director One",),
            language="fr",
            countries=("France",),
        )
        sparse = replace(
            full,
            metadata=replace(
                full.metadata,
                original_language=None,
                production_countries=(),
            ),
        )

        complete_dna = calculate_movie_dna((full,))
        sparse_dna = calculate_movie_dna((sparse,))

        self.assertEqual(sparse_dna.country_count, None)
        self.assertEqual(sparse_dna.language_count, None)
        self.assertEqual(sparse_dna.diversity_score, complete_dna.diversity_score)
        self.assertGreaterEqual(sparse_dna.diversity_score or -1, 0)
        self.assertLessEqual(sparse_dna.diversity_score or 101, 100)

    def test_empty_and_title_only_inputs_are_honest(self):
        """Would fail if missing metadata produced a fabricated diversity score."""
        empty = calculate_movie_dna(())
        title_only = _viewing(
            "1", title="One", tmdb_id=1, release_year=None
        )
        title_only = replace(
            title_only,
            metadata=replace(title_only.metadata, release_year=None),
        )

        self.assertIsNone(empty.diversity_score)
        self.assertEqual(empty.dominant_trait, "Insufficient metadata")
        self.assertTrue(empty.limited_sample)
        self.assertIsNone(calculate_movie_dna((title_only,)).diversity_score)

    def test_dominant_trait_priority_is_declared_and_order_independent(self):
        """Would fail if input ordering or set iteration changed a tied trait."""
        viewings = (
            _viewing(
                "1",
                title="One",
                tmdb_id=1,
                release_year=1960,
                genres=("Drama",),
                directors=("A",),
                language="fr",
                countries=("France",),
            ),
            _viewing(
                "2",
                title="Two",
                tmdb_id=2,
                release_year=2020,
                genres=("Comedy",),
                directors=("B",),
                language="ja",
                countries=("Japan",),
            ),
        )

        self.assertGreater(len(DNA_TRAIT_PRIORITY), 1)
        self.assertEqual(
            calculate_movie_dna(viewings).dominant_trait,
            calculate_movie_dna(tuple(reversed(viewings))).dominant_trait,
        )


if __name__ == "__main__":
    unittest.main()
