from __future__ import annotations

import sys
import unittest
from contextlib import contextmanager
from datetime import datetime
from types import ModuleType
from unittest.mock import patch

from letterboxdpy.core.exceptions import PageLoadError

from spoileralert import data
from spoileralert.data import normalize_year_diary


class _MissingNetworkError(Exception):
    """Test sentinel used until the domain exception exists."""


NetworkError = getattr(data, "NetworkError", _MissingNetworkError)


@contextmanager
def _fake_letterboxd_user(user_factory):
    package = ModuleType("letterboxdpy")
    package.__path__ = []
    user_module = ModuleType("letterboxdpy.user")
    setattr(user_module, "User", user_factory)

    original_package = sys.modules.get("letterboxdpy")
    original_user_module = sys.modules.get("letterboxdpy.user")
    sys.modules["letterboxdpy"] = package
    sys.modules["letterboxdpy.user"] = user_module
    try:
        yield
    finally:
        if original_package is None:
            sys.modules.pop("letterboxdpy", None)
        else:
            sys.modules["letterboxdpy"] = original_package
        if original_user_module is None:
            sys.modules.pop("letterboxdpy.user", None)
        else:
            sys.modules["letterboxdpy.user"] = original_user_module


class FetchUserBoundaryTests(unittest.TestCase):
    def test_successful_constructor_result_is_returned_unchanged(self):
        expected_user = object()

        def fake_user(username):
            self.assertEqual(username, "cinefan")
            return expected_user

        with _fake_letterboxd_user(fake_user):
            actual_user = data.fetch_user("  @cinefan  ")

        self.assertIs(actual_user, expected_user)

    def test_non_network_constructor_failure_remains_profile_not_found(self):
        def fake_user(_username):
            raise ValueError("private parser detail")

        with _fake_letterboxd_user(fake_user):
            with self.assertRaises(data.ProfileNotFoundError) as caught:
                data.fetch_user("cinefan")

        self.assertNotIsInstance(caught.exception, NetworkError)
        self.assertNotIn("private parser detail", str(caught.exception))

    def test_direct_connection_failure_becomes_domain_network_error(self):
        def fake_user(_username):
            raise ConnectionError("secret host and token")

        with _fake_letterboxd_user(fake_user):
            try:
                data.fetch_user("cinefan")
            except Exception as exc:
                self.assertIsInstance(exc, NetworkError)
                self.assertNotIn("secret host and token", str(exc))
            else:
                self.fail("fetch_user did not raise for a connection failure")

    def test_chained_timeout_failure_becomes_domain_network_error(self):
        def fake_user(_username):
            try:
                raise TimeoutError("secret timeout detail")
            except TimeoutError as exc:
                raise RuntimeError("library wrapper detail") from exc

        with _fake_letterboxd_user(fake_user):
            try:
                data.fetch_user("cinefan")
            except Exception as exc:
                self.assertIsInstance(exc, NetworkError)
                self.assertNotIn("secret timeout detail", str(exc))
                self.assertNotIn("library wrapper detail", str(exc))
            else:
                self.fail("fetch_user did not raise for a chained timeout")

    def test_letterboxd_page_load_failure_becomes_domain_network_error(self):
        def fake_user(_username):
            raise PageLoadError(
                "https://letterboxd.example/private",
                "Network error (Timeout): secret transport detail",
            )

        with _fake_letterboxd_user(fake_user):
            try:
                data.fetch_user("cinefan")
            except Exception as exc:
                self.assertIsInstance(exc, NetworkError)
                self.assertNotIn("letterboxd.example", str(exc))
                self.assertNotIn("secret transport detail", str(exc))
            else:
                self.fail("fetch_user did not raise for a page-load failure")


class FullYearDiaryTests(unittest.TestCase):
    def test_get_diary_entries_fetches_the_complete_current_year(self):
        current_year = datetime.now().year

        class FakeUser:
            def __init__(self):
                self.requested_years: list[int] = []

            def get_diary_year(self, year: int):
                self.requested_years.append(year)
                return {
                    "entries": {
                        "101": {"name": "Arrival", "date": f"{year}-01-04"},
                        "102": {"name": "Moonlight", "date": f"{year}-05-18"},
                        "103": {"name": "Arrival", "date": f"{year}-07-22"},
                    }
                }

        user = FakeUser()
        with patch.object(data, "fetch_user", return_value=user):
            entries = data.get_diary_entries("cinefan")

        self.assertEqual(user.requested_years, [current_year])
        self.assertEqual(
            entries,
            [
                {"title": "Arrival", "month": 1},
                {"title": "Moonlight", "month": 5},
                {"title": "Arrival", "month": 7},
            ],
        )

    def test_get_diary_entries_does_not_use_the_recent_profile_preview(self):
        current_year = datetime.now().year

        class FakeUser:
            recent = {
                "diary": {
                    "months": {"1": [["01", "Only recent preview film"]]}
                }
            }

            def get_diary_year(self, year: int):
                self.requested_year = year
                return {
                    "entries": {
                        str(index): {
                            "name": f"Full diary film {index}",
                            "date": f"{year}-02-01",
                        }
                        for index in range(81)
                    }
                }

        user = FakeUser()
        with patch.object(data, "fetch_user", return_value=user):
            entries = data.get_diary_entries("cinefan")

        self.assertEqual(user.requested_year, current_year)
        self.assertEqual(len(entries), 81)


class RichDiaryTests(unittest.TestCase):
    def test_normalization_accepts_letterboxd_utc_datetime_dates(self):
        """Would fail when real letterboxdpy timestamps are treated as malformed."""
        payload = {
            "entries": {
                "1416315797": {
                    "name": "To Die For",
                    "release": 1995,
                    "slug": "to-die-for",
                    "date": "2026-07-26T00:00:00.000000Z",
                    "actions": {"rating": 3.5, "rewatched": False},
                }
            }
        }

        entries = normalize_year_diary(payload, 2026)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].watched_on.isoformat(), "2026-07-26")
        self.assertEqual(entries[0].title, "To Die For")

    def test_full_year_preserves_distinct_viewings_dates_ratings_and_rewatches(self):
        """Would fail if repeated films were deduplicated or rich values discarded."""
        payload = {
            "entries": {
                "1": {
                    "name": "Arrival",
                    "release": 2016,
                    "slug": "arrival",
                    "date": "2026-01-02",
                    "actions": {"rating": 4.5, "rewatched": False},
                },
                "2": {
                    "name": "Arrival",
                    "release": 2016,
                    "slug": "arrival",
                    "date": "2026-03-04",
                    "actions": {"rating": 5.0, "rewatched": True},
                },
            }
        }

        entries = normalize_year_diary(payload, 2026)

        self.assertEqual(len(entries), 2)
        self.assertEqual([entry.viewing_id for entry in entries], ["1", "2"])
        self.assertEqual(entries[0].watched_on.isoformat(), "2026-01-02")
        self.assertEqual(entries[0].rating, 4.5)
        self.assertEqual(entries[1].watched_on.isoformat(), "2026-03-04")
        self.assertEqual(entries[1].rating, 5.0)
        self.assertTrue(entries[1].rewatched)

    def test_normalization_ignores_malformed_rows_and_wrong_year_dates(self):
        """Would fail if invalid or out-of-scope diary rows reached analysis."""
        payload = {
            "entries": {
                "valid": {"name": "Arrival", "date": "2026-01-02"},
                "missing-title": {"date": "2026-01-03"},
                "invalid-date": {"name": "Bad", "date": "not-a-date"},
                "other-year": {"name": "Old", "date": "2025-12-31"},
                "not-a-dict": "Arrival",
            }
        }

        entries = normalize_year_diary(payload, 2026)

        self.assertEqual([(entry.viewing_id, entry.title) for entry in entries], [("valid", "Arrival")])

    def test_compatibility_adapter_returns_only_title_and_month_dictionaries(self):
        """Would fail if legacy consumers received rich objects or extra fields."""
        current_year = datetime.now().year

        class FakeUser:
            def get_diary_year(self, year: int):
                return {
                    "entries": {
                        "1": {
                            "name": "Arrival",
                            "release": 2016,
                            "slug": "arrival",
                            "date": f"{year}-03-04",
                            "actions": {"rating": 5.0, "rewatched": True},
                        }
                    }
                }

        with patch.object(data, "fetch_user", return_value=FakeUser()):
            entries = data.get_diary_entries("cinefan")

        self.assertEqual(entries, [{"title": "Arrival", "month": 3}])


if __name__ == "__main__":
    unittest.main()
