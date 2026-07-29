from __future__ import annotations

import unittest
from datetime import date

from spoileralert.analysis import calculate_director_universe
from spoileralert.models import DiaryEntry, EnrichedViewing, MovieMetadata


def _viewing(
    viewing_id: int,
    title: str,
    directors: tuple[str, ...],
    *,
    runtime: int | None,
    release_year: int | None,
) -> EnrichedViewing:
    diary = DiaryEntry(
        viewing_id=str(viewing_id),
        title=title,
        release_year=release_year,
        slug=title.casefold().replace(" ", "-"),
        watched_on=date(2026, 1, viewing_id),
        rating=None,
        rewatched=viewing_id > 3,
    )
    return EnrichedViewing(
        diary=diary,
        metadata=MovieMetadata(
            tmdb_id=viewing_id,
            title=title,
            release_year=release_year,
            director_names=directors,
            runtime_minutes=runtime,
        ),
    )


class DirectorUniverseTests(unittest.TestCase):
    def test_every_co_director_gets_viewing_credit_and_titles_are_deduplicated(self):
        """Would fail if co-directors or rewatch counts were discarded."""
        viewings = (
            _viewing(1, "Shared Film", ("A Director", "B Director"), runtime=100, release_year=2000),
            _viewing(2, "Solo Film", ("A Director",), runtime=None, release_year=2010),
            _viewing(4, "Shared Film", ("A Director", "B Director"), runtime=100, release_year=2000),
        )

        directors = calculate_director_universe(viewings)
        a_director, b_director = directors

        self.assertEqual(a_director.film_count, 3)
        self.assertEqual(a_director.titles, ("Shared Film", "Solo Film"))
        self.assertEqual(a_director.total_runtime_minutes, 200)
        self.assertAlmostEqual(a_director.percentage, 100.0)
        self.assertAlmostEqual(a_director.average_release_year or 0, 2003.3)
        self.assertEqual(b_director.film_count, 2)
        self.assertAlmostEqual(b_director.percentage, 66.7)

    def test_order_is_count_then_available_runtime_then_name(self):
        """Would fail if None runtime beat known runtime or input order leaked."""
        viewings = (
            _viewing(1, "B Film", ("B Director",), runtime=None, release_year=2000),
            _viewing(2, "A Film", ("A Director",), runtime=90, release_year=2000),
            _viewing(3, "C Film", ("C Director",), runtime=90, release_year=2000),
        )

        directors = calculate_director_universe(viewings)

        self.assertEqual(
            [director.name for director in directors],
            ["A Director", "C Director", "B Director"],
        )

    def test_missing_directors_return_no_stats_and_missing_runtime_stays_none(self):
        """Would fail if absent metadata values became anonymous or zero-valued facts."""
        no_director = _viewing(1, "Unknown", (), runtime=90, release_year=2000)
        known = _viewing(2, "Known", ("Director",), runtime=None, release_year=None)

        self.assertEqual(calculate_director_universe((no_director,)), ())
        stat = calculate_director_universe((known,))[0]
        self.assertIsNone(stat.total_runtime_minutes)
        self.assertIsNone(stat.average_release_year)


if __name__ == "__main__":
    unittest.main()
