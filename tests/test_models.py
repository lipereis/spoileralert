from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from spoileralert.models import DiaryEntry, MovieMetadata


class DomainModelTests(unittest.TestCase):
    def test_diary_entry_is_an_immutable_typed_viewing_record(self):
        """Would fail if a viewing could lose its unique id or be mutated."""
        entry = DiaryEntry(
            viewing_id="42",
            title="Arrival",
            release_year=2016,
            slug="arrival",
            watched_on=date(2026, 1, 2),
            rating=4.5,
            rewatched=False,
        )

        self.assertEqual(entry.viewing_id, "42")
        self.assertEqual(entry.watched_on.isoformat(), "2026-01-02")
        with self.assertRaises(FrozenInstanceError):
            entry.title = "Changed"  # type: ignore[misc]

    def test_metadata_uses_empty_tuples_for_unavailable_collections(self):
        """Would fail if unavailable metadata became mutable shared lists."""
        metadata = MovieMetadata(tmdb_id=None, title="Arrival", release_year=2016)

        self.assertEqual(metadata.genres, ())
        self.assertEqual(metadata.director_names, ())
        self.assertEqual(metadata.production_countries, ())
        self.assertEqual(metadata.keywords, ())


if __name__ == "__main__":
    unittest.main()
