from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from spoileralert.analysis import compute_enhanced_stats, compute_stats
from spoileralert.models import DiaryEntry, EnrichedViewing, MovieMetadata


def _entry(viewing_id: int, watched_on: date, *, rewatched: bool = False) -> DiaryEntry:
    return DiaryEntry(
        viewing_id=str(viewing_id),
        title="Arrival" if viewing_id < 3 else "Moonlight",
        release_year=2016,
        slug="arrival" if viewing_id < 3 else "moonlight",
        watched_on=watched_on,
        rating=4.0,
        rewatched=rewatched,
    )


class EnhancedAnalysisTests(unittest.TestCase):
    def test_orchestration_calls_overview_once_and_composes_all_results(self):
        """Would fail if orchestration duplicated overview work or omitted analyses."""
        entries = (
            _entry(1, date(2026, 1, 31)),
            _entry(2, date(2026, 2, 1), rewatched=True),
            _entry(3, date(2026, 2, 3)),
        )
        arrival = MovieMetadata(
            tmdb_id=329865,
            title="Arrival",
            release_year=2016,
            genres=("Drama", "Science Fiction"),
            director_names=("Denis Villeneuve",),
            runtime_minutes=116,
            original_language="en",
            production_countries=("United States",),
        )
        moonlight = MovieMetadata(
            tmdb_id=376867,
            title="Moonlight",
            release_year=2016,
            genres=("Drama",),
            director_names=("Barry Jenkins",),
            runtime_minutes=111,
            original_language="en",
            production_countries=("United States",),
        )
        enriched = (
            EnrichedViewing(entries[0], arrival),
            EnrichedViewing(entries[1], arrival),
            EnrichedViewing(entries[2], moonlight),
        )

        with patch("spoileralert.analysis.compute_stats", wraps=None) as overview_mock:
            from spoileralert.analysis import WrappedStats

            overview_mock.return_value = WrappedStats(
                username="cinefan",
                total_movies=3,
                peak_month_label="Fevereiro",
                peak_month_count=2,
                top_titles=["Arrival", "Moonlight"],
                monthly_counts=None,  # type: ignore[arg-type]
            )
            stats = compute_enhanced_stats("cinefan", entries, enriched)

        overview_mock.assert_called_once_with(
            "cinefan",
            [
                {"title": "Arrival", "month": 1},
                {"title": "Arrival", "month": 2},
                {"title": "Moonlight", "month": 2},
            ],
        )
        self.assertIs(stats.overview, overview_mock.return_value)
        self.assertEqual(stats.total_viewing_count, 3)
        self.assertEqual(stats.enriched_film_count, 2)
        self.assertEqual(stats.active_days, 3)
        self.assertEqual(stats.longest_streak_days, 2)
        self.assertEqual([point.film_count for point in stats.timeline], [1, 2])
        self.assertEqual(stats.busiest_period, stats.timeline[1])
        self.assertEqual(stats.least_active_period, stats.timeline[0])
        self.assertEqual(stats.average_films_per_active_period, 1.5)
        self.assertEqual(stats.first_to_last_change, 1)
        self.assertTrue(stats.movie_dna.limited_sample)
        self.assertEqual(stats.movie_dna.top_genres[0].name, "Drama")
        self.assertTrue(stats.moods)
        self.assertTrue(stats.mood_sentence)
        self.assertEqual(stats.directors[0].name, "Denis Villeneuve")

    def test_empty_input_returns_honest_coverage_and_streak_values(self):
        """Would fail if empty diaries fabricated coverage or a one-day streak."""
        stats = compute_enhanced_stats("cinefan", (), ())

        self.assertEqual(stats.total_viewing_count, 0)
        self.assertEqual(stats.enriched_film_count, 0)
        self.assertEqual(stats.active_days, 0)
        self.assertIsNone(stats.longest_streak_days)
        self.assertEqual(stats.timeline, ())
        self.assertIsNone(stats.busiest_period)
        self.assertIsNone(stats.least_active_period)
        self.assertIsNone(stats.average_films_per_active_period)
        self.assertIsNone(stats.first_to_last_change)
        self.assertEqual(stats.directors, ())
        self.assertIsNone(stats.movie_dna.diversity_score)
        self.assertEqual(stats.overview.peak_month_label, "Unavailable")
        self.assertEqual(stats.overview.peak_month_count, 0)

    def test_timeline_insights_use_earliest_ties_and_exclude_internal_zero_gaps(self):
        """Would fail if zero padding won least-active or ties chose a later period."""
        entries = (
            _entry(1, date(2026, 1, 1)),
            _entry(2, date(2026, 1, 2)),
            _entry(3, date(2026, 3, 1)),
            _entry(4, date(2026, 4, 1)),
        )
        enriched = tuple(EnrichedViewing(entry, None) for entry in entries)

        stats = compute_enhanced_stats("cinefan", entries, enriched)

        self.assertEqual(
            [(point.label, point.film_count) for point in stats.timeline],
            [("Jan", 2), ("Feb", 0), ("Mar", 1), ("Apr", 1)],
        )
        self.assertEqual(stats.busiest_period, stats.timeline[0])
        self.assertEqual(stats.least_active_period, stats.timeline[2])
        self.assertEqual(stats.average_films_per_active_period, 1.33)
        self.assertEqual(stats.first_to_last_change, -1)

    def test_single_period_is_both_extremes_with_zero_change(self):
        """Would fail if insight calculations assumed multiple represented periods."""
        entry = _entry(1, date(2026, 7, 4))

        stats = compute_enhanced_stats(
            "cinefan",
            (entry,),
            (EnrichedViewing(entry, None),),
        )

        self.assertEqual(stats.busiest_period, stats.timeline[0])
        self.assertEqual(stats.least_active_period, stats.timeline[0])
        self.assertEqual(stats.average_films_per_active_period, 1.0)
        self.assertEqual(stats.first_to_last_change, 0)

    def test_empty_overview_uses_an_unavailable_peak_label(self):
        """Would fail if idxmax fabricated January from twelve zero counts."""
        stats = compute_stats("cinefan", [])

        self.assertEqual(stats.peak_month_label, "Unavailable")
        self.assertEqual(stats.peak_month_count, 0)


if __name__ == "__main__":
    unittest.main()
