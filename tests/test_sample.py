from __future__ import annotations

import unittest
from datetime import date

from spoileralert.data import parse_diary_csv
from spoileralert.sample import (
    SAMPLE_DISPLAY_NAME,
    SAMPLE_VIEWING_COUNT,
    sample_diary_csv_bytes,
    sample_watch_dates,
)


class SampleDiaryTests(unittest.TestCase):
    def test_sample_is_a_readable_export_for_the_running_year(self):
        """Would fail if the demo could not travel the same upload path a real
        export takes, or if it aged out of the current-year analysis scope.
        """
        entries = parse_diary_csv(sample_diary_csv_bytes())

        self.assertEqual(len(entries), SAMPLE_VIEWING_COUNT)
        self.assertTrue(all(entry.watched_on.year == date.today().year for entry in entries))
        self.assertTrue(all(entry.title for entry in entries))
        self.assertTrue(all(entry.release_year for entry in entries))
        self.assertTrue(all(entry.slug for entry in entries))
        self.assertTrue(all(entry.rating for entry in entries))

    def test_sample_never_claims_a_viewing_in_the_future(self):
        """Would fail if the demo diary read as films watched tomorrow."""
        today = date(2026, 7, 29)
        watched = sample_watch_dates(today)

        self.assertEqual(len(watched), SAMPLE_VIEWING_COUNT)
        self.assertEqual(min(watched), date(2026, 1, 1))
        self.assertEqual(max(watched), today)
        self.assertEqual(list(watched), sorted(watched))

    def test_sample_stays_inside_the_year_on_its_very_first_day(self):
        """Would fail on January 1, when no elapsed days exist to spread over."""
        watched = sample_watch_dates(date(2026, 1, 1))

        self.assertEqual(set(watched), {date(2026, 1, 1)})
        entries = parse_diary_csv(sample_diary_csv_bytes(date(2026, 1, 1)), year=2026)
        self.assertEqual(len(entries), SAMPLE_VIEWING_COUNT)

    def test_sample_keeps_rewatches_as_separate_viewings(self):
        """Would fail if the demo hid the rewatch handling the app promises."""
        entries = parse_diary_csv(sample_diary_csv_bytes(date(2026, 7, 29)), year=2026)
        titles = [entry.title for entry in entries]

        self.assertGreater(len(titles), len(set(titles)))
        self.assertGreaterEqual(sum(1 for entry in entries if entry.rewatched), 2)

    def test_sample_spans_decades_and_months_so_every_card_has_material(self):
        """Would fail if the demo produced a flat timeline or a single decade."""
        entries = parse_diary_csv(sample_diary_csv_bytes(date(2026, 7, 29)), year=2026)

        decades = {(entry.release_year or 0) // 10 for entry in entries}
        months = {entry.watched_on.month for entry in entries}

        self.assertGreaterEqual(len(decades), 5)
        self.assertGreaterEqual(len(months), 6)
        self.assertGreaterEqual(len({entry.title for entry in entries}), 20)

    def test_sample_bytes_are_deterministic_for_one_day(self):
        """Would fail if two visitors on the same day saw different demos."""
        first = sample_diary_csv_bytes(date(2026, 7, 29))
        second = sample_diary_csv_bytes(date(2026, 7, 29))

        self.assertEqual(first, second)
        self.assertTrue(
            first.startswith(
                b"Date,Name,Year,Letterboxd URI,Rating,Rewatch,Watched Date\n"
            )
        )

    def test_sample_display_name_is_safe_for_a_filename(self):
        """Would fail if the demo name broke the card filenames or the ZIP."""
        self.assertTrue(SAMPLE_DISPLAY_NAME.isascii())
        self.assertTrue(SAMPLE_DISPLAY_NAME.isalnum())


if __name__ == "__main__":
    unittest.main()
