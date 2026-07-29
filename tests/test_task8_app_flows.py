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


def _click(app: AppTest, label: str) -> AppTest:
    """Click by visible label so landing reordering cannot silently retarget."""
    return next(button for button in app.button if button.label == label).click().run()


def _type_username(app: AppTest, value: str) -> None:
    """Fill the live-profile field by label, since it carries no widget key.

    A keyed landing widget would break these flows: a rerun cycle leaves the
    landing elements in the tree after the stage changes, and Streamlit has
    already discarded the keyed state they point at.
    """
    field = next(
        element for element in app.text_input if element.label == "Letterboxd username"
    )
    field.input(value)


def _submitted_app(scenario: str) -> AppTest:
    app = AppTest.from_function(_run_fixture_app, default_timeout=30).run()
    app.session_state["_task8_scenario"] = scenario
    _type_username(app, "cinefan")
    return _click(app, "Generate My Wrapped")


def _run_seeded_error_app() -> None:
    """Start directly in a genuine error stage.

    Rendering the landing page first would leave its trailing widgets in the
    test element tree, because a shorter error render does not overwrite every
    delta path the longer landing render wrote. Seeding the stage keeps each
    assertion about what the error stage itself produced.
    """
    import streamlit as st

    import app as app_module
    from components.errors import map_exception
    from spoileralert.data import BlockedError, ProfileNotFoundError
    from spoileralert.ui_state import initialize_state, set_error

    initialize_state(st.session_state)
    if not st.session_state.get("_task8_error_seeded"):
        failure: Exception = (
            BlockedError("raw blocked diary url detail")
            if st.session_state.get("_task8_error_kind") == "blocked"
            else ProfileNotFoundError("raw upstream profile detail")
        )
        set_error(st.session_state, map_exception(failure))
        st.session_state["_task8_error_seeded"] = True

    app_module.main()


def _seeded_error_app(kind: str) -> AppTest:
    app = AppTest.from_function(_run_seeded_error_app, default_timeout=30)
    app.session_state["_task8_error_kind"] = kind
    return app.run()


def _run_csv_app() -> None:
    """Run the real pipeline from uploaded diary bytes, never scraping."""
    from datetime import date
    from unittest.mock import patch

    import streamlit as st

    import app as app_module
    from spoileralert.ui_state import begin_generation, initialize_state

    initialize_state(st.session_state)
    if not st.session_state.get("_task8_csv_seeded"):
        year = date.today().year
        export = (
            "Date,Name,Year,Letterboxd URI,Rating,Rewatch,Watched Date\n"
            f"{year}-01-05,Arrival,2016,https://boxd.it/aaa,4.5,No,{year}-01-05\n"
            f"{year}-02-11,Whiplash,2014,https://boxd.it/bbb,5,No,{year}-02-11\n"
            f"{year}-02-12,Arrival,2016,https://boxd.it/ccc,4.5,Yes,{year}-02-12\n"
        )
        begin_generation(st.session_state, "cinefan", export.encode("utf-8"))
        st.session_state["_task8_csv_seeded"] = True

    def refuse_scraping(_username: str):
        raise AssertionError("the upload path must not reach Letterboxd")

    with (
        patch.object(app_module, "get_rich_diary_entries", side_effect=refuse_scraping),
        patch.object(app_module, "get_tmdb_api_key", return_value=None),
        patch.object(app_module.logging, "warning"),
    ):
        app_module.main()


def _run_demo_app() -> None:
    """Run the real landing page with scraping and TMDB unavailable."""
    from unittest.mock import patch

    import app as app_module

    def refuse_scraping(_username: str):
        raise AssertionError("the sample must not reach Letterboxd")

    with (
        patch.object(app_module, "get_rich_diary_entries", side_effect=refuse_scraping),
        patch.object(app_module, "get_tmdb_api_key", return_value=None),
        patch.object(app_module.logging, "warning"),
    ):
        app_module.main()


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
            [
                "See a sample Wrapped",
                "Generate My Wrapped from CSV",
                "Generate My Wrapped",
            ],
        )

    def test_invalid_profile_enters_safe_error_without_leaking_upstream_text(self):
        app = _submitted_app("invalid")

        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["stage"], "error")
        rendered = "\n".join(element.value for element in app.markdown)
        self.assertIn("The username may be misspelled, private, or unavailable.", rendered)
        self.assertNotIn("raw upstream profile detail", rendered)

    def test_retry_only_error_returns_to_landing_without_offering_an_upload(self):
        app = _seeded_error_app("profile")

        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual([button.label for button in app.button], ["Try Again"])
        self.assertEqual(len(app.get("file_uploader")), 0)

        app = _click(app, "Try Again")
        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["stage"], "landing")

    def test_sample_button_alone_produces_the_full_six_card_story(self):
        """Would fail if a first-time visitor could not see the product without
        an account, an export, or a host Letterboxd is willing to answer.
        """
        app = AppTest.from_function(_run_demo_app, default_timeout=90).run()
        app = _click(app, "See a sample Wrapped")

        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["stage"], "result")
        self.assertEqual(app.session_state["username"], "cinephile")
        self.assertEqual(len(app.session_state["wrapped_cards"]), 6)
        self.assertEqual(len(app.download_button), 8)
        self.assertEqual(app.session_state["stats"].total_viewing_count, 28)

    def test_blocked_host_offers_the_upload_instead_of_a_doomed_retry(self):
        """Would fail if a shared-IP block left the retry button as the only
        action, which reruns the same blocked request forever.
        """
        app = _seeded_error_app("blocked")

        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["stage"], "error")

        rendered = "\n".join(element.value for element in app.markdown)
        self.assertIn("Letterboxd blocked this server.", rendered)
        self.assertIn("diary.csv", rendered)
        self.assertNotIn("raw blocked diary url detail", rendered)

        self.assertEqual(
            [button.label for button in app.button],
            ["Generate My Wrapped from CSV", "Start Over"],
        )
        self.assertEqual(len(app.get("file_uploader")), 1)

    def test_uploaded_export_reaches_a_six_card_result_without_scraping(self):
        """Would fail if the scraping-free path could not carry a real export
        through analysis and rendering while Letterboxd is unreachable.
        """
        app = AppTest.from_function(_run_csv_app, default_timeout=60).run()

        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["stage"], "result")
        self.assertEqual(len(app.session_state["wrapped_cards"]), 6)
        self.assertEqual(len(app.download_button), 8)

        stats = app.session_state["stats"]
        self.assertEqual(stats.total_viewing_count, 3)
        self.assertEqual(stats.enriched_film_count, 0)

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
