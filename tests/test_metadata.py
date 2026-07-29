from __future__ import annotations

import unittest
from collections.abc import Iterator, Mapping
from datetime import date

from spoileralert.metadata import (
    enrich_diary_entries,
    get_tmdb_api_key,
    lookup_movie_metadata,
    match_confidence,
    normalize_title,
)
from spoileralert.models import DiaryEntry, MovieMetadata


def _entry(
    viewing_id: str = "1",
    title: str = "Arrival",
    release_year: int | None = 2016,
) -> DiaryEntry:
    return DiaryEntry(
        viewing_id=viewing_id,
        title=title,
        release_year=release_year,
        slug="arrival",
        watched_on=date(2026, 1, int(viewing_id)),
        rating=4.5,
        rewatched=False,
    )


class _Response:
    def __init__(self, payload, status_code: int = 200, *, json_error=None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict, tuple[float, float]]] = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class StreamlitSecretNotFoundError(Exception):
    """Dependency-free stand-in with the real Streamlit exception identity."""


StreamlitSecretNotFoundError.__module__ = "streamlit.errors"


class _RaisingSecrets(Mapping[str, object]):
    def __init__(self, error: Exception):
        self.error = error

    def __getitem__(self, key: str) -> object:
        raise self.error

    def __iter__(self) -> Iterator[str]:
        return iter(())

    def __len__(self) -> int:
        return 0


def _successful_responses(*, search_results=None, poster_path="/arrival.jpg"):
    return [
        _Response(
            {
                "page": 1,
                "results": search_results
                if search_results is not None
                else [
                    {
                        "id": 329865,
                        "title": "Arrival",
                        "original_title": "Arrival",
                        "release_date": "2016-11-10",
                    }
                ],
                "total_pages": 1,
                "total_results": 1,
            }
        ),
        _Response(
            {
                "id": 329865,
                "title": "Arrival",
                "release_date": "2016-11-10",
                "genres": [{"id": 18, "name": "Drama"}, {"id": 878, "name": "Science Fiction"}],
                "runtime": 116,
                "original_language": "en",
                "production_countries": [{"iso_3166_1": "US", "name": "United States of America"}],
                "overview": "A linguist works with the military to communicate with aliens.",
                "poster_path": poster_path,
            }
        ),
        _Response(
            {
                "id": 329865,
                "cast": [],
                "crew": [
                    {"id": 137427, "job": "Director", "name": "Denis Villeneuve"},
                    {"id": 123, "job": "Writer", "name": "Eric Heisserer"},
                ],
            }
        ),
        _Response(
            {
                "id": 329865,
                "keywords": [
                    {"id": 9951, "name": "alien"},
                    {"id": 1612, "name": "spacecraft"},
                ],
            }
        ),
    ]


class ApiKeyTests(unittest.TestCase):
    def test_secrets_key_takes_precedence_and_is_trimmed(self):
        self.assertEqual(
            get_tmdb_api_key(
                {"TMDB_API_KEY": "  secret-key  "},
                {"TMDB_API_KEY": "environment-key"},
            ),
            "secret-key",
        )

    def test_missing_or_non_string_keys_are_unavailable(self):
        self.assertIsNone(get_tmdb_api_key({}, {}))
        self.assertIsNone(get_tmdb_api_key({"TMDB_API_KEY": object()}, {}))
        self.assertIsNone(get_tmdb_api_key({"TMDB_API_KEY": "   "}, {}))

    def test_missing_streamlit_secrets_file_falls_back_to_environment(self):
        secrets = _RaisingSecrets(
            StreamlitSecretNotFoundError("No secrets files were found")
        )

        self.assertEqual(
            get_tmdb_api_key(secrets, {"TMDB_API_KEY": "environment-key"}),
            "environment-key",
        )

    def test_unrelated_secrets_proxy_failure_is_not_silently_swallowed(self):
        secrets = _RaisingSecrets(RuntimeError("unsafe proxy failure"))

        with self.assertRaisesRegex(RuntimeError, "unsafe proxy failure"):
            get_tmdb_api_key(secrets, {"TMDB_API_KEY": "environment-key"})


class MatchingTests(unittest.TestCase):
    def test_title_normalization_is_unicode_punctuation_and_space_stable(self):
        self.assertEqual(normalize_title("  WALL·E: L’Aventure!  "), "wall e l aventure")
        self.assertEqual(normalize_title("Amélie"), "amelie")

    def test_exact_title_and_exact_year_receive_full_confidence(self):
        candidate = {"title": "  ARRIVAL! ", "release_date": "2016-11-10"}
        self.assertEqual(match_confidence(_entry(), candidate), 1.0)

    def test_adjacent_release_year_is_compatible_but_lower_confidence(self):
        candidate = {"title": "Arrival", "release_date": "2015-09-01"}
        self.assertEqual(match_confidence(_entry(), candidate), 0.9)

    def test_incompatible_year_or_non_exact_title_is_rejected(self):
        self.assertEqual(
            match_confidence(
                _entry(), {"title": "Arrival 2", "release_date": "2016-01-01"}
            ),
            0.0,
        )
        self.assertEqual(
            match_confidence(
                _entry(), {"title": "Arrival", "release_date": "2013-01-01"}
            ),
            0.0,
        )


class LookupTests(unittest.TestCase):
    def test_missing_key_returns_without_making_a_request(self):
        session = _Session([])
        self.assertIsNone(lookup_movie_metadata("Arrival", 2016, "", session=session))
        self.assertEqual(session.calls, [])

    def test_lookup_normalizes_valid_detail_credits_keywords_and_poster(self):
        session = _Session(_successful_responses())

        metadata = lookup_movie_metadata("Arrival", 2016, "key", session=session)

        self.assertEqual(
            metadata,
            MovieMetadata(
                tmdb_id=329865,
                title="Arrival",
                release_year=2016,
                genres=("Drama", "Science Fiction"),
                director_names=("Denis Villeneuve",),
                runtime_minutes=116,
                original_language="en",
                production_countries=("United States of America",),
                keywords=("alien", "spacecraft"),
                overview="A linguist works with the military to communicate with aliens.",
                poster_url="https://image.tmdb.org/t/p/w500/arrival.jpg",
                match_confidence=1.0,
            ),
        )
        self.assertEqual(len(session.calls), 4)
        self.assertTrue(all(call[2] == (3.05, 10.0) for call in session.calls))
        self.assertTrue(all(call[1]["api_key"] == "key" for call in session.calls))

    def test_invalid_poster_path_is_not_composed_into_a_url(self):
        session = _Session(_successful_responses(poster_path="//evil.example/poster.jpg"))

        metadata = lookup_movie_metadata("Arrival", 2016, "key", session=session)

        self.assertIsNotNone(metadata)
        self.assertIsNone(metadata.poster_url)

    def test_unique_highest_confidence_candidate_is_selected(self):
        session = _Session(
            _successful_responses(
                search_results=[
                    {"id": 1, "title": "Arrival", "release_date": "2015-09-01"},
                    {"id": 329865, "title": "Arrival", "release_date": "2016-11-10"},
                ]
            )
        )

        metadata = lookup_movie_metadata("Arrival", 2016, "key", session=session)

        self.assertIsNotNone(metadata)
        self.assertIn("/movie/329865", session.calls[1][0])

    def test_ambiguous_equal_confidence_candidates_are_rejected(self):
        session = _Session(
            [
                _Response(
                    {
                        "page": 1,
                        "results": [
                            {"id": 1, "title": "Arrival", "release_date": "2016-01-01"},
                            {"id": 2, "title": "Arrival", "release_date": "2016-11-10"},
                        ],
                        "total_pages": 1,
                        "total_results": 2,
                    }
                )
            ]
        )

        self.assertIsNone(lookup_movie_metadata("Arrival", 2016, "key", session=session))
        self.assertEqual(len(session.calls), 1)

    def test_malformed_search_release_date_cannot_qualify_at_threshold(self):
        session = _Session(
            _successful_responses(
                search_results=[
                    {
                        "id": 329865,
                        "title": "Arrival",
                        "release_date": "not-a-date",
                    }
                ]
            )
        )

        self.assertIsNone(
            lookup_movie_metadata("Arrival", 2016, "key", session=session)
        )
        self.assertEqual(len(session.calls), 1)

    def test_exact_search_result_cannot_authorize_inconsistent_detail(self):
        inconsistent_fields = (
            ("title", "Moonlight"),
            ("release_date", "2010-01-01"),
            ("release_date", "not-a-date"),
            ("id", 376867),
        )
        for field, value in inconsistent_fields:
            with self.subTest(field=field, value=value):
                responses = _successful_responses()
                responses[1].payload[field] = value

                self.assertIsNone(
                    lookup_movie_metadata(
                        "Arrival", 2016, "key", session=_Session(responses)
                    )
                )

    def test_mismatched_supplemental_ids_are_ignored_not_joined_to_movie(self):
        responses = _successful_responses()
        responses[2].payload["id"] = 376867
        responses[3].payload["id"] = 376867

        metadata = lookup_movie_metadata(
            "Arrival", 2016, "key", session=_Session(responses)
        )

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.director_names, ())
        self.assertEqual(metadata.keywords, ())

    def test_timeout_rate_limit_and_malformed_json_are_recoverable(self):
        cases = (
            _Session([TimeoutError("private timeout")]),
            _Session([_Response({}, status_code=429)]),
            _Session([_Response(None, json_error=ValueError("private payload"))]),
        )
        for session in cases:
            with self.subTest(session=session):
                self.assertIsNone(
                    lookup_movie_metadata("Arrival", 2016, "key", session=session)
                )

    def test_malformed_search_detail_credits_or_keyword_payload_is_recoverable(self):
        valid = _successful_responses()
        malformed_sequences = (
            [_Response({"results": "not-a-list"})],
            [valid[0], _Response(["not-a-detail-object"])],
            [valid[0], valid[1], _Response({"crew": "not-a-list"})],
            [valid[0], valid[1], valid[2], _Response({"keywords": "not-a-list"})],
        )
        for responses in malformed_sequences:
            with self.subTest(responses=responses):
                self.assertIsNone(
                    lookup_movie_metadata(
                        "Arrival", 2016, "key", session=_Session(responses)
                    )
                )


class EnrichmentTests(unittest.TestCase):
    def test_missing_key_preserves_every_viewing_without_calling_lookup(self):
        entries = [_entry("1"), _entry("2")]
        calls = []

        def lookup(*args):
            calls.append(args)
            raise AssertionError("lookup must not run without a key")

        enriched = enrich_diary_entries(entries, None, lookup=lookup)

        self.assertEqual([item.diary for item in enriched], entries)
        self.assertEqual([item.metadata for item in enriched], [None, None])
        self.assertEqual(calls, [])

    def test_duplicate_titles_lookup_once_and_preserve_distinct_viewings(self):
        entries = [
            _entry("1"),
            _entry("2", "  ARRIVAL!  ", 2016),
            _entry("3", "Moonlight", 2016),
        ]
        arrival = MovieMetadata(tmdb_id=329865, title="Arrival", release_year=2016)
        moonlight = MovieMetadata(tmdb_id=376867, title="Moonlight", release_year=2016)
        calls = []

        def lookup(title, release_year, api_key):
            calls.append((title, release_year, api_key))
            return arrival if title == "Arrival" else moonlight

        enriched = enrich_diary_entries(entries, "key", lookup=lookup)

        self.assertEqual(
            calls,
            [("Arrival", 2016, "key"), ("Moonlight", 2016, "key")],
        )
        self.assertEqual([item.diary.viewing_id for item in enriched], ["1", "2", "3"])
        self.assertIs(enriched[0].metadata, arrival)
        self.assertIs(enriched[1].metadata, arrival)
        self.assertIs(enriched[2].metadata, moonlight)

    def test_lookup_failure_isolated_to_its_unique_movie(self):
        entries = [_entry("1"), _entry("2", "Moonlight", 2016)]

        def lookup(title, release_year, api_key):
            if title == "Arrival":
                raise RuntimeError("private service detail")
            return MovieMetadata(tmdb_id=376867, title=title, release_year=release_year)

        enriched = enrich_diary_entries(entries, "key", lookup=lookup)

        self.assertIsNone(enriched[0].metadata)
        self.assertEqual(enriched[1].metadata.tmdb_id, 376867)


if __name__ == "__main__":
    unittest.main()
