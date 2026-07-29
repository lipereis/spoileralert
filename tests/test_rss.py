from __future__ import annotations

import unittest
from datetime import date

from spoileralert.data import (
    BlockedError,
    EmptyDiaryError,
    NetworkError,
    ProfileNotFoundError,
)
from spoileralert.rss import (
    DiaryFeed,
    build_feed_url,
    fetch_diary_feed,
    fetch_feed,
    parse_feed,
)

FEED_HEADER = (
    "<?xml version='1.0' encoding='utf-8'?>\n"
    '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:letterboxd="https://letterboxd.com" '
    'xmlns:tmdb="https://themoviedb.org"><channel>'
    "<title>Letterboxd - Felipe</title>"
)
FEED_FOOTER = "</channel></rss>"


def diary_item(
    *,
    title: str = "Parasite",
    film_year: str = "2019",
    watched: str = "2026-03-24",
    rating: str | None = "4.5",
    rewatch: str = "No",
    guid: str = "letterboxd-watch-1",
    slug: str = "parasite-2019",
    repeat: str = "",
) -> str:
    rating_element = (
        f"<letterboxd:memberRating>{rating}</letterboxd:memberRating>" if rating else ""
    )
    return (
        "<item>"
        f"<title>{title}, {film_year}</title>"
        f"<link>https://letterboxd.com/cinefan/film/{slug}/{repeat}</link>"
        f"<guid>{guid}</guid>"
        "<pubDate>Tue, 24 Mar 2026 09:11:13 +1300</pubDate>"
        f"<letterboxd:watchedDate>{watched}</letterboxd:watchedDate>"
        f"<letterboxd:rewatch>{rewatch}</letterboxd:rewatch>"
        f"<letterboxd:filmTitle>{title}</letterboxd:filmTitle>"
        f"<letterboxd:filmYear>{film_year}</letterboxd:filmYear>"
        f"{rating_element}"
        "<letterboxd:memberLike>No</letterboxd:memberLike>"
        "<tmdb:movieId>496243</tmdb:movieId>"
        "<description>&lt;p&gt;poster&lt;/p&gt;</description>"
        "<dc:creator>Felipe</dc:creator>"
        "</item>"
    )


LIST_ITEM = (
    "<item>"
    "<title>My favourite films</title>"
    "<link>https://letterboxd.com/cinefan/list/my-favourite-films/</link>"
    "<guid>letterboxd-list-99</guid>"
    "<pubDate>Tue, 24 Mar 2026 09:11:13 +1300</pubDate>"
    "<description>&lt;p&gt;a list&lt;/p&gt;</description>"
    "<dc:creator>Felipe</dc:creator>"
    "</item>"
)


def feed(*items: str) -> str:
    return FEED_HEADER + "".join(items) + FEED_FOOTER


class FeedUrlTests(unittest.TestCase):
    def test_username_is_normalized_into_the_documented_feed_url(self):
        for raw in ("cinefan", "  cinefan  ", "@cinefan", "CineFan"):
            with self.subTest(raw=raw):
                self.assertEqual(
                    build_feed_url(raw),
                    "https://letterboxd.com/cinefan/rss/",
                )

    def test_unusable_usernames_are_refused_before_any_request(self):
        """Would fail if path characters or blanks reached the URL."""
        for raw in ("", "   ", "@", "cine fan", "cinefan/../admin", "a" * 51, "cine?fan"):
            with self.subTest(raw=raw):
                with self.assertRaises(ProfileNotFoundError):
                    build_feed_url(raw)


class ParseFeedTests(unittest.TestCase):
    def test_diary_items_become_validated_viewings(self):
        parsed = parse_feed(feed(diary_item()), year=2026)

        self.assertEqual(len(parsed.entries), 1)
        entry = parsed.entries[0]
        self.assertEqual(entry.viewing_id, "letterboxd-watch-1")
        self.assertEqual(entry.title, "Parasite")
        self.assertEqual(entry.release_year, 2019)
        self.assertEqual(entry.slug, "parasite-2019")
        self.assertEqual(entry.watched_on, date(2026, 3, 24))
        self.assertEqual(entry.rating, 4.5)
        self.assertIs(entry.rewatched, False)

    def test_non_diary_items_are_skipped_rather_than_counted(self):
        """Would fail if published lists inflated the viewing totals."""
        parsed = parse_feed(feed(LIST_ITEM, diary_item(), LIST_ITEM), year=2026)

        self.assertEqual(len(parsed.entries), 1)
        self.assertEqual(parsed.diary_item_count, 1)

    def test_only_the_requested_year_is_kept_and_order_is_chronological(self):
        parsed = parse_feed(
            feed(
                diary_item(watched="2026-05-02", guid="c", slug="c-film"),
                diary_item(watched="2025-12-30", guid="old", slug="old-film"),
                diary_item(watched="2026-01-08", guid="a", slug="a-film"),
            ),
            year=2026,
        )

        self.assertEqual(
            [entry.watched_on for entry in parsed.entries],
            [date(2026, 1, 8), date(2026, 5, 2)],
        )
        self.assertEqual(parsed.diary_item_count, 3)

    def test_repeat_viewing_links_still_resolve_one_film_slug(self):
        """Would fail if a rewatch permalink counter leaked into the slug."""
        parsed = parse_feed(
            feed(diary_item(slug="parasite-2019", repeat="1/", rewatch="Yes")),
            year=2026,
        )

        self.assertEqual(parsed.entries[0].slug, "parasite-2019")
        self.assertIs(parsed.entries[0].rewatched, True)

    def test_absent_or_unreadable_fields_stay_absent(self):
        parsed = parse_feed(
            feed(diary_item(rating=None, film_year="not-a-year")),
            year=2026,
        )

        self.assertIsNone(parsed.entries[0].rating)
        self.assertIsNone(parsed.entries[0].release_year)

    def test_unreadable_watch_dates_are_dropped_not_guessed(self):
        parsed = parse_feed(feed(diary_item(watched="24/03/2026")), year=2026)

        self.assertEqual(parsed.entries, ())
        self.assertEqual(parsed.diary_item_count, 0)

    def test_a_year_that_fills_the_whole_feed_is_reported_as_truncated(self):
        """Would fail if a cut-off year were presented as a complete one."""
        parsed = parse_feed(
            feed(*(diary_item(watched="2026-02-02", guid=str(index)) for index in range(6))),
            year=2026,
        )

        self.assertTrue(parsed.truncated)
        self.assertIsNotNone(parsed.coverage_note)
        note = parsed.coverage_note or ""
        self.assertIn("2026", note)
        self.assertIn("export", note)

    def test_a_feed_reaching_into_last_year_proves_the_year_is_complete(self):
        parsed = parse_feed(
            feed(
                diary_item(watched="2026-02-02", guid="new"),
                diary_item(watched="2025-11-30", guid="old"),
            ),
            year=2026,
        )

        self.assertFalse(parsed.truncated)
        self.assertIsNone(parsed.coverage_note)

    def test_an_empty_year_is_never_called_truncated(self):
        parsed = parse_feed(feed(diary_item(watched="2025-04-04")), year=2026)

        self.assertEqual(parsed.entries, ())
        self.assertFalse(parsed.truncated)
        self.assertIsNone(parsed.coverage_note)

    def test_unreadable_xml_becomes_a_network_error(self):
        with self.assertRaises(NetworkError):
            parse_feed("<rss><channel><item></broken>", year=2026)


class _Response:
    def __init__(self, status_code: int, content: bytes = b""):
        self.status_code = status_code
        self.content = content


class FetchFeedTests(unittest.TestCase):
    def _session(self, response=None, error: Exception | None = None):
        calls: list[tuple[str, dict[str, object]]] = []

        class Session:
            def get(self, url, **kwargs):
                calls.append((url, kwargs))
                if error is not None:
                    raise error
                return response

        return Session(), calls

    def test_a_successful_feed_returns_bytes_and_identifies_the_client(self):
        session, calls = self._session(_Response(200, b"<rss/>"))

        self.assertEqual(fetch_feed("cinefan", session=session), b"<rss/>")
        url, kwargs = calls[0]
        self.assertEqual(url, "https://letterboxd.com/cinefan/rss/")
        headers = kwargs["headers"]
        assert isinstance(headers, dict)
        self.assertIn("SpoilerAlert", headers["User-Agent"])
        self.assertIsNotNone(kwargs["timeout"])

    def test_each_refusal_maps_to_the_matching_domain_error(self):
        """Would fail if a block, a missing profile, and an outage looked alike."""
        cases = (
            (403, BlockedError),
            (404, ProfileNotFoundError),
            (500, NetworkError),
            (302, NetworkError),
        )
        for status, expected in cases:
            with self.subTest(status=status):
                session, _ = self._session(_Response(status, b""))
                with self.assertRaises(expected):
                    fetch_feed("cinefan", session=session)

    def test_transport_failures_become_a_network_error(self):
        session, _ = self._session(error=TimeoutError("connect timed out"))

        with self.assertRaises(NetworkError):
            fetch_feed("cinefan", session=session)

    def test_an_implausibly_large_feed_is_refused_before_parsing(self):
        session, _ = self._session(_Response(200, b"x" * (9 * 1024 * 1024)))

        with self.assertRaises(NetworkError):
            fetch_feed("cinefan", session=session)


class FetchDiaryFeedTests(unittest.TestCase):
    def test_a_year_with_viewings_is_returned_whole(self):
        result = fetch_diary_feed(
            "cinefan",
            2026,
            fetch=lambda _username: feed(diary_item()).encode("utf-8"),
        )

        self.assertIsInstance(result, DiaryFeed)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.year, 2026)

    def test_a_readable_feed_without_this_year_raises_empty_diary(self):
        """Would fail if an inactive year looked like a broken profile."""
        with self.assertRaises(EmptyDiaryError):
            fetch_diary_feed(
                "cinefan",
                2026,
                fetch=lambda _username: feed(diary_item(watched="2025-01-01")).encode(),
            )

    def test_fetch_failures_reach_the_caller_unchanged(self):
        def blocked(_username: str) -> bytes:
            raise BlockedError("refused")

        with self.assertRaises(BlockedError):
            fetch_diary_feed("cinefan", 2026, fetch=blocked)


if __name__ == "__main__":
    unittest.main()
