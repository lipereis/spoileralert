from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import streamlit

with patch.object(streamlit, "set_page_config"):
    import app
from components.errors import UiError
from spoileralert.models import RenderedCard


class _ProgressHandle:
    def __init__(self):
        self.calls: list[tuple[int, str]] = []

    def progress(self, value: int, *, text: str):
        self.calls.append((value, text))


class _StatusHandle:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def update(self, **kwargs):
        self.calls.append(kwargs)


class _AppStreamlitDouble:
    def __init__(self, state: dict[str, object], *, button_clicked: bool = False):
        self.session_state = state
        self.secrets = {}
        self.button_clicked = button_clicked
        self.rerun_calls = 0
        self.button_calls: list[tuple[str, dict[str, object]]] = []

    def rerun(self):
        self.rerun_calls += 1

    def button(self, label: str, **kwargs):
        self.button_calls.append((label, kwargs))
        return self.button_clicked


class AppCoordinatorTests(unittest.TestCase):
    def test_blank_submission_enters_safe_error_without_fetching(self):
        state = {
            "stage": "landing",
            "username": "",
            "stats": None,
            "image_bytes": None,
            "ui_error": None,
        }
        st = _AppStreamlitDouble(state)
        fetch = Mock(side_effect=AssertionError("fetch must not run"))

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_hero"),
            patch.object(app, "render_generator_form", return_value="  \t "),
            patch.object(app, "render_csv_uploader_form", return_value=None),
            patch.object(app, "render_features"),
            patch.object(app, "render_footer"),
            patch.object(app, "get_rich_diary_entries", fetch),
        ):
            app.render_current_stage()

        fetch.assert_not_called()
        self.assertEqual(state["stage"], "error")
        self.assertEqual(
            state["ui_error"].title,
            "A username belongs in the starring role.",
        )
        self.assertNotIn("\t", state["ui_error"].message)
        self.assertEqual(st.rerun_calls, 1)

    def test_at_only_submission_enters_blank_error_without_fetching(self):
        state = {
            "stage": "landing",
            "username": "",
            "stats": None,
            "image_bytes": None,
            "ui_error": None,
        }
        st = _AppStreamlitDouble(state)
        fetch = Mock(side_effect=AssertionError("fetch must not run"))

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_hero"),
            patch.object(app, "render_generator_form", return_value="  @  "),
            patch.object(app, "render_csv_uploader_form", return_value=None),
            patch.object(app, "render_features"),
            patch.object(app, "render_footer"),
            patch.object(app, "render_loading_shell", return_value=(_StatusHandle(), _ProgressHandle())),
            patch.object(app, "get_rich_diary_entries", fetch),
        ):
            app.render_current_stage()
            app.render_current_stage()

        fetch.assert_not_called()
        self.assertEqual(state["stage"], "error")
        self.assertEqual(
            state["ui_error"].title,
            "A username belongs in the starring role.",
        )
        self.assertEqual(st.rerun_calls, 1)

    def test_generating_runs_each_enhanced_operation_once_then_result_rerun_does_not_repeat_it(self):
        state = {
            "stage": "generating",
            "username": "cinefan",
            "stats": None,
            "image_bytes": None,
            "ui_error": None,
        }
        st = _AppStreamlitDouble(state)
        progress = _ProgressHandle()
        status = _StatusHandle()
        entries = (object(),)
        enriched = (object(),)
        stats = object()
        slugs = ("overview", "personality", "movie-dna", "moods", "directors", "timeline")
        cards = tuple(
            RenderedCard(slug, slug, f"{slug}.png", b"png") for slug in slugs
        )
        operation_order: list[str] = []

        def fetch(username):
            operation_order.append("diary")
            self.assertEqual(username, "cinefan")
            return entries

        def enrich(actual_entries, api_key, *, lookup):
            operation_order.append("enrich")
            self.assertIs(actual_entries, entries)
            self.assertEqual(api_key, "tmdb-key")
            self.assertIs(lookup, app.lookup_cached_movie_metadata_with_key)
            return enriched

        def compute(username, actual_entries, actual_enriched):
            operation_order.append("analyze")
            self.assertEqual(username, "cinefan")
            self.assertIs(actual_entries, entries)
            self.assertIs(actual_enriched, enriched)
            return stats

        def render(actual_stats):
            operation_order.append("render")
            self.assertIs(actual_stats, stats)
            return cards

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_loading_shell", return_value=(status, progress)),
            patch.object(app, "get_tmdb_api_key", return_value="tmdb-key") as key,
            patch.object(app, "get_rich_diary_entries", side_effect=fetch),
            patch.object(app, "enrich_diary_entries", side_effect=enrich),
            patch.object(app, "compute_enhanced_stats", side_effect=compute),
            patch.object(app, "render_story_cards", side_effect=render),
            patch.object(app, "render_result", return_value=False) as result_view,
        ):
            app.render_current_stage()
            app.render_current_stage()

        self.assertEqual(operation_order, ["diary", "enrich", "analyze", "render"])
        self.assertEqual([value for value, _ in progress.calls], [25, 50, 75, 100])
        self.assertEqual(status.calls[-1]["state"], "complete")
        self.assertFalse(status.calls[-1]["expanded"])
        self.assertEqual(state["stage"], "result")
        self.assertIs(state["stats"], stats)
        self.assertIsNone(state["image_bytes"])
        self.assertEqual(state["wrapped_cards"], cards)
        key.assert_called_once_with(st.secrets)
        result_view.assert_called_once_with(stats, cards)
        self.assertEqual(st.rerun_calls, 1)

    def test_generation_exception_is_logged_and_mapped_without_raw_text(self):
        state = {
            "stage": "generating",
            "username": "cinefan",
            "stats": None,
            "image_bytes": None,
            "ui_error": None,
        }
        st = _AppStreamlitDouble(state)
        progress = _ProgressHandle()
        status = _StatusHandle()
        failure = RuntimeError("private parser internals")

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_loading_shell", return_value=(status, progress)),
            patch.object(app, "get_rich_diary_entries", side_effect=failure),
            patch.object(app.logging, "exception") as log_exception,
        ):
            app.render_current_stage()

        log_exception.assert_called_once()
        self.assertEqual(state["stage"], "error")
        self.assertNotIn("private parser internals", state["ui_error"].message)
        self.assertNotIn("private parser internals", state["ui_error"].action)
        self.assertEqual(st.rerun_calls, 1)

    def test_loading_shell_exception_also_enters_safe_error_state(self):
        state = {
            "stage": "generating",
            "username": "cinefan",
            "stats": None,
            "image_bytes": None,
            "ui_error": None,
        }
        st = _AppStreamlitDouble(state)

        with (
            patch.object(app, "st", st),
            patch.object(
                app,
                "render_loading_shell",
                side_effect=RuntimeError("private loading internals"),
            ),
            patch.object(app.logging, "exception") as log_exception,
        ):
            app.render_current_stage()

        log_exception.assert_called_once()
        self.assertEqual(state["stage"], "error")
        self.assertNotIn("private loading internals", state["ui_error"].message)
        self.assertEqual(st.rerun_calls, 1)

    def test_result_and_error_actions_reset_session_without_generation(self):
        stats = object()
        image_bytes = b"png"
        state = {
            "stage": "result",
            "username": "cinefan",
            "stats": stats,
            "image_bytes": image_bytes,
            "ui_error": None,
        }
        st = _AppStreamlitDouble(state, button_clicked=True)
        fetch = Mock(side_effect=AssertionError("fetch must not run"))

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_result", return_value=True),
            patch.object(app, "get_rich_diary_entries", fetch),
        ):
            app.render_current_stage()

        self.assertEqual(state["stage"], "landing")
        self.assertEqual(st.rerun_calls, 1)

        error = UiError("Safe title", "Safe message", "Safe action")
        state.update(
            {
                "stage": "error",
                "username": "cinefan",
                "stats": None,
                "image_bytes": None,
                "ui_error": error,
            }
        )
        with (
            patch.object(app, "st", st),
            patch.object(app, "render_error") as error_view,
            patch.object(app, "render_footer") as footer,
            patch.object(app, "get_rich_diary_entries", fetch),
        ):
            app.render_current_stage()

        error_view.assert_called_once_with(error)
        footer.assert_called_once_with()
        fetch.assert_not_called()
        self.assertEqual(state["stage"], "landing")
        self.assertEqual(st.rerun_calls, 2)
        self.assertEqual(
            st.button_calls,
            [("Try Again", {"width": "stretch"})],
        )

    def test_upload_recoverable_error_offers_the_upload_beside_a_restart(self):
        """Would fail if a host-level block left a retry as the only action,
        since that retry hits the same blocked path again.
        """
        error = UiError(
            "Letterboxd blocked this server.",
            "Safe message",
            "Safe action",
            allow_csv_recovery=True,
        )
        state = {
            "stage": "error",
            "username": "cinefan",
            "stats": None,
            "image_bytes": None,
            "ui_error": error,
        }
        st = _AppStreamlitDouble(state)

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_error"),
            patch.object(app, "render_footer"),
            patch.object(app, "render_csv_uploader_form", return_value=None) as uploader,
        ):
            app.render_current_stage()

        uploader.assert_called_once_with(form_key="csv_recovery_form")
        self.assertEqual(state["stage"], "error")
        self.assertEqual(
            st.button_calls,
            [("Start Over", {"width": "stretch"})],
        )

    def test_error_stage_upload_starts_a_csv_generation_without_scraping(self):
        """Would fail if recovering from the error screen scraped the blocked
        profile instead of reading the uploaded export.
        """
        state = {
            "stage": "error",
            "username": "cinefan",
            "stats": None,
            "image_bytes": None,
            "ui_error": UiError(
                "Blocked",
                "Safe message",
                "Safe action",
                allow_csv_recovery=True,
            ),
        }
        st = _AppStreamlitDouble(state)
        fetch = Mock(side_effect=AssertionError("fetch must not run"))

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_error"),
            patch.object(app, "render_footer") as footer,
            patch.object(
                app,
                "render_csv_uploader_form",
                return_value=("  @Cinefan  ", b"Date,Name\n2026-01-01,Arrival\n"),
            ),
            patch.object(app, "get_rich_diary_entries", fetch),
        ):
            app.render_current_stage()

        fetch.assert_not_called()
        footer.assert_not_called()
        self.assertEqual(state["stage"], "generating")
        self.assertEqual(state["username"], "Cinefan")
        self.assertEqual(state["diary_csv_bytes"], b"Date,Name\n2026-01-01,Arrival\n")
        self.assertIsNone(state["ui_error"])
        self.assertEqual(st.button_calls, [])
        self.assertEqual(st.rerun_calls, 1)


if __name__ == "__main__":
    unittest.main()
