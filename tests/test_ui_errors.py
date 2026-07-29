import unittest
from unittest.mock import patch

import components.errors as errors
from components.errors import UiError, map_exception, render_error
from spoileralert import data
from spoileralert.data import BlockedError, EmptyDiaryError, InvalidCsvError, ProfileNotFoundError


class _MissingNetworkError(Exception):
    """Test sentinel used until the domain exception exists."""


NetworkError = getattr(data, "NetworkError", _MissingNetworkError)


class UiErrorTests(unittest.TestCase):
    def assert_safe_mapping(self, exc, expected):
        error = map_exception(exc)

        self.assertEqual(error, expected)
        for field in (error.title, error.message, error.action):
            self.assertNotIn("secret", field.lower())

    def test_profile_error_returns_complete_safe_copy(self):
        self.assert_safe_mapping(
            ProfileNotFoundError("secret profile detail"),
            UiError(
                "We could not open this diary.",
                "The username may be misspelled, private, or unavailable.",
                "Check the spelling and confirm the Letterboxd profile is public.",
            ),
        )

    def test_empty_diary_error_returns_complete_safe_copy(self):
        self.assert_safe_mapping(
            EmptyDiaryError("secret diary detail"),
            UiError(
                "There is not enough diary activity yet.",
                "This profile has no public diary entries for the current year.",
                "Add a diary entry for this year on Letterboxd, then try again.",
            ),
        )

    def test_invalid_csv_error_returns_complete_safe_copy(self):
        self.assert_safe_mapping(
            InvalidCsvError("secret parser detail"),
            UiError(
                "That file isn't a Letterboxd diary export.",
                "We could not find the expected columns in this CSV file.",
                "Export diary.csv from Letterboxd's Settings \u2192 Import & Export page, then upload it here.",
                allow_csv_recovery=True,
            ),
        )

    def test_blocked_error_returns_complete_safe_copy(self):
        self.assert_safe_mapping(
            BlockedError("secret blocked url detail"),
            UiError(
                "Letterboxd blocked this server.",
                "Letterboxd's anti-bot protection is blocking requests from this "
                "hosting provider's shared IP address, not from your account.",
                "Retrying will not help, but uploading your diary export will: "
                "get diary.csv from Letterboxd's Settings \u2192 Import & Export page "
                "and upload it below for your complete Wrapped.",
                allow_csv_recovery=True,
            ),
        )

    def test_only_upload_recoverable_failures_offer_the_upload_path(self):
        """Would fail if a retry-only failure advertised an irrelevant upload,
        or if a host-level block hid the one path that can still succeed.
        """
        for exc in (BlockedError("blocked"), InvalidCsvError("wrong file")):
            with self.subTest(exception_type=type(exc).__name__):
                self.assertTrue(map_exception(exc).allow_csv_recovery)

        for exc in (
            ProfileNotFoundError("missing"),
            EmptyDiaryError("empty"),
            NetworkError("offline"),
            ConnectionError("offline"),
            TimeoutError("slow"),
            errors.IncompleteStoryError("five cards"),
            RuntimeError("unexpected"),
        ):
            with self.subTest(exception_type=type(exc).__name__):
                self.assertFalse(map_exception(exc).allow_csv_recovery)

    def test_blocked_copy_names_the_upload_without_advising_a_bare_retry(self):
        """Would fail if the block copy sent users back to the doomed path."""
        error = map_exception(BlockedError("blocked"))

        self.assertIn("diary.csv", error.action)
        self.assertIn("Retrying will not help", error.action)
        self.assertNotIn("Try again later", error.action)

    def test_network_and_unexpected_errors_return_complete_safe_copy(self):
        network_copy = UiError(
            "Letterboxd is taking a break.",
            "We could not reach the profile service right now.",
            "Wait a moment and try the same username again.",
        )
        cases = (
            (NetworkError("secret domain network detail"), network_copy),
            (ConnectionError("secret connection detail"), network_copy),
            (TimeoutError("secret timeout detail"), network_copy),
            (
                RuntimeError("secret parser detail"),
                UiError(
                    "The reel stopped unexpectedly.",
                    "We could not finish this Wrapped safely.",
                    "Try again. If the problem continues, use another public profile.",
                ),
            ),
        )
        for exc, expected in cases:
            with self.subTest(exception_type=type(exc).__name__):
                self.assert_safe_mapping(exc, expected)

    def test_incomplete_story_error_has_safe_retry_copy(self):
        """Would fail if a partial card set exposed renderer internals."""
        error_type = errors.IncompleteStoryError

        self.assert_safe_mapping(
            error_type("secret renderer returned five cards"),
            UiError(
                "The final cut is incomplete.",
                "We could not assemble all six story cards safely.",
                "Try this profile again in a moment.",
            ),
        )

    def test_render_error_uses_one_escaped_live_region_with_h1(self):
        class FakeStreamlit:
            def __init__(self):
                self.calls = []

            def markdown(self, text, *, unsafe_allow_html):
                self.calls.append(("markdown", text, unsafe_allow_html))

        fake_streamlit = FakeStreamlit()
        with patch.object(errors, "st", fake_streamlit):
            render_error(
                UiError(
                    '<script>alert("title")</script>',
                    '<img src=x onerror="message">',
                    'Click "<b>here</b>"',
                )
            )

        self.assertEqual(len(fake_streamlit.calls), 1)
        _, markup, unsafe_allow_html = fake_streamlit.calls[0]
        self.assertTrue(unsafe_allow_html)
        self.assertEqual(markup.count('aria-live="polite"'), 1)
        self.assertIn('<section class="error-panel" aria-live="polite">', markup)
        self.assertTrue(markup.endswith("</section>"))
        self.assertIn(
            "<h1>&lt;script&gt;alert(&quot;title&quot;)&lt;/script&gt;</h1>",
            markup,
        )
        self.assertIn("&lt;img src=x onerror=&quot;message&quot;&gt;", markup)
        self.assertIn("Click &quot;&lt;b&gt;here&lt;/b&gt;&quot;", markup)
        self.assertNotIn("<h2>", markup)
        self.assertNotIn("<script>", markup)
        self.assertNotIn("<img", markup)


if __name__ == "__main__":
    unittest.main()
