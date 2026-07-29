from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

import streamlit

with patch.object(streamlit, "set_page_config"):
    import app

from spoileralert.data import ProfileNotFoundError
from spoileralert.models import DiaryEntry, EnrichedViewing, RenderedCard


class _Progress:
    def __init__(self):
        self.calls: list[tuple[int, str]] = []

    def progress(self, value: int, *, text: str) -> None:
        self.calls.append((value, text))


class _Status:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def update(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _Streamlit:
    def __init__(self, state: dict[str, object], secrets=None):
        self.session_state = state
        self.secrets = {} if secrets is None else secrets
        self.rerun_calls = 0

    def rerun(self) -> None:
        self.rerun_calls += 1


def _state() -> dict[str, object]:
    return {
        "stage": "generating",
        "username": "cinefan",
        "stats": None,
        "image_bytes": None,
        "ui_error": None,
        "wrapped_cards": (),
        "selected_card_index": 0,
    }


def _entry() -> DiaryEntry:
    return DiaryEntry(
        viewing_id="2026-12-31-arrival",
        title="Arrival",
        release_year=2016,
        slug="arrival",
        watched_on=date(2026, 12, 31),
        rating=4.5,
        rewatched=True,
    )


def _cards() -> tuple[RenderedCard, ...]:
    slugs = ("overview", "personality", "movie-dna", "moods", "directors", "timeline")
    return tuple(
        RenderedCard(slug, slug, f"spoileralert-cinefan-{slug}.png", b"png")
        for slug in slugs
    )


class EnhancedAppFlowTests(unittest.TestCase):
    def test_missing_key_preserves_full_year_viewing_and_reaches_six_card_result(self):
        """Would fail if enrichment became required or rich diary fields were projected away."""
        state = _state()
        st = _Streamlit(state)
        status, progress = _Status(), _Progress()
        entries = (_entry(),)
        enriched = (EnrichedViewing(entries[0], None),)
        stats = object()

        def enrich(actual_entries, api_key):
            self.assertIs(actual_entries, entries)
            self.assertIsNone(api_key)
            self.assertTrue(actual_entries[0].rewatched)
            self.assertEqual(actual_entries[0].watched_on, date(2026, 12, 31))
            return enriched

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_loading_shell", return_value=(status, progress)),
            patch.object(app, "get_tmdb_api_key", return_value=None) as key,
            patch.object(app, "get_rich_diary_entries", return_value=entries),
            patch.object(app, "enrich_diary_entries", side_effect=enrich),
            patch.object(app, "compute_enhanced_stats", return_value=stats),
            patch.object(app, "render_story_cards", return_value=_cards()),
        ):
            app.render_current_stage()

        key.assert_called_once_with(st.secrets)
        self.assertEqual(state["stage"], "result")
        self.assertEqual(len(state["wrapped_cards"]), 6)
        self.assertIsNone(state["image_bytes"])
        self.assertEqual([value for value, _ in progress.calls], [25, 50, 75, 100])
        self.assertEqual(st.rerun_calls, 1)

    def test_metadata_failure_logs_no_detail_or_key_and_continues_unenriched(self):
        """Would fail if an optional TMDB outage blocked or exposed a generation."""
        state = _state()
        st = _Streamlit(state, {"TMDB_API_KEY": "do-not-log-this"})
        status, progress = _Status(), _Progress()
        entries = (_entry(),)
        stats = object()

        def analyze(username, actual_entries, enriched):
            self.assertEqual(username, "cinefan")
            self.assertIs(actual_entries, entries)
            self.assertEqual(enriched, (EnrichedViewing(entries[0], None),))
            return stats

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_loading_shell", return_value=(status, progress)),
            patch.object(app, "get_tmdb_api_key", return_value="do-not-log-this"),
            patch.object(app, "get_rich_diary_entries", return_value=entries),
            patch.object(
                app,
                "enrich_diary_entries",
                side_effect=TimeoutError("https://tmdb.invalid?api_key=do-not-log-this"),
            ),
            patch.object(app, "compute_enhanced_stats", side_effect=analyze),
            patch.object(app, "render_story_cards", return_value=_cards()),
            patch.object(app.logging, "warning") as warning,
        ):
            app.render_current_stage()

        logged = " ".join(str(value) for value in warning.call_args.args)
        self.assertNotIn("do-not-log-this", logged)
        self.assertNotIn("tmdb.invalid", logged)
        self.assertEqual(state["stage"], "result")
        self.assertEqual(len(state["wrapped_cards"]), 6)
        self.assertNotIn("do-not-log-this", tuple(state.values()))

    def test_wrong_card_count_is_a_safe_fatal_error(self):
        """Would fail if an incomplete story could enter the result gallery."""
        state = _state()
        st = _Streamlit(state)
        entries = (_entry(),)
        enriched = (EnrichedViewing(entries[0], None),)

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_loading_shell", return_value=(_Status(), _Progress())),
            patch.object(app, "get_tmdb_api_key", return_value=None),
            patch.object(app, "get_rich_diary_entries", return_value=entries),
            patch.object(app, "enrich_diary_entries", return_value=enriched),
            patch.object(app, "compute_enhanced_stats", return_value=object()),
            patch.object(app, "render_story_cards", return_value=_cards()[:-1]),
            patch.object(app.logging, "exception"),
        ):
            app.render_current_stage()

        self.assertEqual(state["stage"], "error")
        self.assertEqual(state["wrapped_cards"], ())
        self.assertEqual(state["ui_error"].title, "The final cut is incomplete.")
        self.assertNotIn("five", state["ui_error"].message.casefold())

    def test_wrong_card_order_is_a_safe_fatal_error(self):
        """Would fail if six misordered cards could enter the ordered gallery."""
        state = _state()
        st = _Streamlit(state)
        entries = (_entry(),)
        enriched = (EnrichedViewing(entries[0], None),)
        cards = _cards()

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_loading_shell", return_value=(_Status(), _Progress())),
            patch.object(app, "get_tmdb_api_key", return_value=None),
            patch.object(app, "get_rich_diary_entries", return_value=entries),
            patch.object(app, "enrich_diary_entries", return_value=enriched),
            patch.object(app, "compute_enhanced_stats", return_value=object()),
            patch.object(
                app,
                "render_story_cards",
                return_value=(cards[1], cards[0], *cards[2:]),
            ),
            patch.object(app.logging, "exception"),
        ):
            app.render_current_stage()

        self.assertEqual(state["stage"], "error")
        self.assertEqual(state["wrapped_cards"], ())
        self.assertEqual(state["ui_error"].title, "The final cut is incomplete.")

    def test_letterboxd_failure_remains_fatal_and_does_not_start_enrichment(self):
        """Would fail if profile failures were incorrectly treated as optional metadata."""
        state = _state()
        st = _Streamlit(state)

        with (
            patch.object(app, "st", st),
            patch.object(app, "render_loading_shell", return_value=(_Status(), _Progress())),
            patch.object(
                app,
                "get_rich_diary_entries",
                side_effect=ProfileNotFoundError("raw external profile detail"),
            ),
            patch.object(app, "enrich_diary_entries") as enrich,
            patch.object(app.logging, "exception"),
        ):
            app.render_current_stage()

        enrich.assert_not_called()
        self.assertEqual(state["stage"], "error")
        self.assertNotIn("raw external profile detail", state["ui_error"].message)
        self.assertEqual(st.rerun_calls, 1)


if __name__ == "__main__":
    unittest.main()
