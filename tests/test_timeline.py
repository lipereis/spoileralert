from __future__ import annotations

import unittest
from datetime import date

from spoileralert.analysis import calculate_viewing_timeline
from spoileralert.models import DiaryEntry, EnrichedViewing, MovieMetadata, TimelinePoint


def _entry(
    viewing_id: int,
    watched_on: date,
    *,
    rating: float | None = None,
    rewatched: bool | None = None,
) -> DiaryEntry:
    return DiaryEntry(
        viewing_id=str(viewing_id),
        title=f"Film {viewing_id}",
        release_year=2020,
        slug=f"film-{viewing_id}",
        watched_on=watched_on,
        rating=rating,
        rewatched=rewatched,
    )


class TimelineTests(unittest.TestCase):
    def test_monthly_timeline_keeps_only_internal_zero_months(self):
        """Would fail if outer calendar months were padded or internal gaps omitted."""
        entries = (
            _entry(1, date(2026, 1, 1)),
            _entry(2, date(2026, 3, 1)),
        )

        points = calculate_viewing_timeline(entries)

        self.assertEqual([point.label for point in points], ["Jan", "Feb", "Mar"])
        self.assertEqual([point.film_count for point in points], [1, 0, 1])
        self.assertEqual(points[1], TimelinePoint("Feb", 0, None, None, None))

    def test_available_values_are_aggregated_without_fabricating_missing_values(self):
        """Would fail if unknown runtime, rating, or rewatch values became zeroes."""
        first = EnrichedViewing(
            diary=_entry(1, date(2026, 1, 1), rating=4.0, rewatched=False),
            metadata=MovieMetadata(
                tmdb_id=1,
                title="Film 1",
                release_year=2020,
                runtime_minutes=100,
            ),
        )
        second = EnrichedViewing(
            diary=_entry(2, date(2026, 1, 2), rating=None, rewatched=True),
            metadata=None,
        )

        point = calculate_viewing_timeline((first, second))[0]

        self.assertEqual(point.film_count, 2)
        self.assertEqual(point.total_runtime_minutes, 100)
        self.assertEqual(point.average_rating, 4.0)
        self.assertEqual(point.rewatch_count, 1)

        missing = calculate_viewing_timeline(
            (_entry(3, date(2026, 2, 1)),)
        )[0]
        self.assertIsNone(missing.total_runtime_minutes)
        self.assertIsNone(missing.average_rating)
        self.assertIsNone(missing.rewatch_count)

    def test_weekly_grouping_uses_iso_year_across_calendar_boundary(self):
        """Would fail if January dates were assigned to the wrong ISO year/week."""
        entries = (
            _entry(1, date(2025, 12, 28)),
            _entry(2, date(2025, 12, 29)),
            _entry(3, date(2026, 1, 5)),
        )

        points = calculate_viewing_timeline(entries, grouping="weekly")

        self.assertEqual(
            [(point.label, point.film_count) for point in points],
            [("2025-W52", 1), ("2026-W01", 1), ("2026-W02", 1)],
        )

    def test_empty_and_single_entry_ranges_are_supported(self):
        """Would fail if boundary ranges assumed at least two populated periods."""
        self.assertEqual(calculate_viewing_timeline(()), ())
        self.assertEqual(
            calculate_viewing_timeline((_entry(1, date(2026, 7, 4)),))[0].film_count,
            1,
        )

    def test_unknown_grouping_is_rejected(self):
        """Would fail if misspelled grouping silently returned misleading periods."""
        with self.assertRaisesRegex(ValueError, "monthly or weekly"):
            calculate_viewing_timeline((), grouping="daily")


if __name__ == "__main__":
    unittest.main()
