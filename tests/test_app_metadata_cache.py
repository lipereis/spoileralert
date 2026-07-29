from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

import streamlit

with patch.object(streamlit, "set_page_config"):
    import app

from spoileralert.models import MovieMetadata


def _metadata(year: int = 2016) -> MovieMetadata:
    return MovieMetadata(tmdb_id=329865, title="Arrival", release_year=year)


class AppMetadataCacheTests(unittest.TestCase):
    def setUp(self):
        app._cached_lookup_movie_metadata.clear()

    def tearDown(self):
        app._cached_lookup_movie_metadata.clear()

    def test_repeated_normalized_success_uses_one_pure_lookup(self):
        """Would fail if punctuation variants caused duplicate successful lookups."""
        with (
            patch.object(app, "lookup_movie_metadata", return_value=_metadata()) as lookup,
            app.tmdb_credential_scope(lambda: "private-key"),
        ):
            first = app.lookup_cached_movie_metadata("  ARRIVAL! ", 2016)
            second = app.lookup_cached_movie_metadata("arrival", 2016)

        self.assertEqual(first, _metadata())
        self.assertEqual(second, _metadata())
        lookup.assert_called_once_with("arrival", 2016, "private-key")

    def test_none_and_failure_are_not_cached(self):
        """Would fail if a recoverable miss poisoned later generations."""
        for first_result in (None, TimeoutError("private failure")):
            with self.subTest(first_result=first_result):
                app._cached_lookup_movie_metadata.clear()
                side_effect = [first_result, _metadata()]
                with (
                    patch.object(app, "lookup_movie_metadata", side_effect=side_effect) as lookup,
                    app.tmdb_credential_scope(lambda: "private-key"),
                ):
                    self.assertIsNone(app.lookup_cached_movie_metadata("Arrival", 2016))
                    self.assertEqual(
                        app.lookup_cached_movie_metadata("Arrival", 2016),
                        _metadata(),
                    )
                self.assertEqual(lookup.call_count, 2)

    def test_release_year_is_part_of_the_public_cache_key(self):
        """Would fail if remakes with the same normalized title shared metadata."""
        with (
            patch.object(
                app,
                "lookup_movie_metadata",
                side_effect=lambda title, year, key: _metadata(year or 2016),
            ) as lookup,
            app.tmdb_credential_scope(lambda: "private-key"),
        ):
            app.lookup_cached_movie_metadata("Arrival", 2016)
            app.lookup_cached_movie_metadata("Arrival", 2017)

        self.assertEqual(lookup.call_count, 2)

    def test_cached_function_accepts_only_public_normalized_configuration(self):
        """Would fail if the API key entered cache arguments or representations."""
        parameters = tuple(inspect.signature(app._cached_lookup_movie_metadata).parameters)

        self.assertEqual(
            parameters,
            ("normalized_title", "release_year", "configuration_version"),
        )
        self.assertNotIn("private-key", repr(app._cached_lookup_movie_metadata))
        self.assertNotIn("api_key", " ".join(parameters).casefold())
        self.assertEqual(app._cached_lookup_movie_metadata._info.ttl, 86400)
        self.assertEqual(app._cached_lookup_movie_metadata._info.max_entries, 2048)
        self.assertIsNone(app._TMDB_CREDENTIAL_PROVIDER.get())


if __name__ == "__main__":
    unittest.main()
