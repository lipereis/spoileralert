from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def _run_fixture_app() -> None:
    """Run the real coordinator/UI with only external services replaced."""
    from datetime import date
    from unittest.mock import patch

    import streamlit as st

    import app as app_module
    from spoileralert.data import ProfileNotFoundError
    from spoileralert.models import DiaryEntry, EnrichedViewing, MovieMetadata
    from tests.test_card_renderers import enhanced_fixture

    scenario = st.session_state.get("_task8_scenario", "valid")
    entry = DiaryEntry(
        viewing_id="task8-arrival",
        title="Arrival",
        release_year=2016,
        slug="arrival",
        watched_on=date(2026, 1, 2),
        rating=4.5,
        rewatched=False,
    )
    metadata = MovieMetadata(
        tmdb_id=329865,
        title="Arrival",
        release_year=2016,
        genres=("Drama", "Science Fiction"),
        director_names=("Denis Villeneuve",),
        runtime_minutes=116,
        original_language="en",
        production_countries=("United States of America",),
        keywords=("space exploration",),
        overview="A linguist joins a reflective first-contact mission.",
        poster_url=None,
        match_confidence=1.0,
    )

    def fetch_diary(_username: str):
        if scenario == "invalid":
            raise ProfileNotFoundError("raw upstream profile detail")
        return (entry,)

    def api_key(_secrets):
        return None if scenario == "no-key" else "fixture-key"

    def enrich(entries, key):
        if scenario == "metadata-failure":
            raise TimeoutError("raw TMDB URL containing fixture-key")
        return tuple(
            EnrichedViewing(item, metadata if key is not None else None)
            for item in entries
        )

    with (
        patch.object(app_module, "get_rich_diary_entries", side_effect=fetch_diary),
        patch.object(app_module, "get_tmdb_api_key", side_effect=api_key),
        patch.object(app_module, "enrich_diary_entries", side_effect=enrich),
        patch.object(app_module, "compute_enhanced_stats", return_value=enhanced_fixture()),
        patch.object(app_module.logging, "exception"),
        patch.object(app_module.logging, "warning"),
    ):
        app_module.main()


def _submitted_app(scenario: str) -> AppTest:
    app = AppTest.from_function(_run_fixture_app, default_timeout=30).run()
    app.session_state["_task8_scenario"] = scenario
    app.text_input[0].input("cinefan")
    return app.button[0].click().run()


def _run_seeded_result_app() -> None:
    """Start directly at a genuine rendered result for reset interaction testing."""
    import streamlit as st

    import app as app_module
    from spoileralert.render import render_story_cards
    from spoileralert.ui_state import initialize_state, set_result
    from tests.test_card_renderers import enhanced_fixture

    initialize_state(st.session_state)
    if not st.session_state.get("_task8_result_seeded"):
        stats = enhanced_fixture()
        set_result(st.session_state, stats, render_story_cards(stats))
        st.session_state["_task8_result_seeded"] = True
    app_module.main()


class Task8AppFlowTests(unittest.TestCase):
    def test_valid_enhanced_fixture_exposes_gallery_downloads_and_create_another(self):
        app = _submitted_app("valid")

        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["stage"], "result")
        self.assertEqual([box.label for box in app.selectbox], ["Choose a story card"])
        self.assertEqual(len(app.image), 1)
        self.assertEqual(len(app.download_button), 8)
        self.assertTrue(app.download_button[0].proto.url.endswith(".png"))
        self.assertTrue(app.download_button[-1].proto.url.endswith(".zip"))

        reset_app = AppTest.from_function(
            _run_seeded_result_app,
            default_timeout=30,
        ).run()
        create_another = next(
            button for button in reset_app.button if button.key == "create-another"
        )
        reset_app = create_another.click().run()
        self.assertEqual([exception.message for exception in reset_app.exception], [])
        self.assertEqual(reset_app.session_state["stage"], "landing")
        self.assertEqual(
            [button.label for button in reset_app.button],
            ["Generate My Wrapped"],
        )

    def test_invalid_profile_enters_safe_error_and_try_again_returns_to_landing(self):
        app = _submitted_app("invalid")

        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["stage"], "error")
        rendered = "\n".join(element.value for element in app.markdown)
        self.assertIn("The username may be misspelled, private, or unavailable.", rendered)
        self.assertNotIn("raw upstream profile detail", rendered)

        app = next(button for button in app.button if button.label == "Try Again").click().run()
        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["stage"], "landing")

    def test_no_key_and_metadata_failure_both_reach_six_card_result(self):
        for scenario in ("no-key", "metadata-failure"):
            with self.subTest(scenario=scenario):
                app = _submitted_app(scenario)
                self.assertEqual([exception.message for exception in app.exception], [])
                self.assertEqual(app.session_state["stage"], "result")
                self.assertEqual(len(app.download_button), 8)
                self.assertEqual(len(app.session_state["wrapped_cards"]), 6)


if __name__ == "__main__":
    unittest.main()
