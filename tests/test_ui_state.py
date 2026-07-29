import unittest

from spoileralert.ui_state import (
    begin_generation,
    initialize_state,
    reset_generation,
    select_next_card,
    select_previous_card,
    set_error,
    set_result,
)
from spoileralert.models import RenderedCard


class UiStateTests(unittest.TestCase):
    def test_initialize_state_adds_defaults_without_overwriting_existing_values(self):
        state = {"stage": "result", "username": "existing"}

        initialize_state(state)

        self.assertEqual(state["stage"], "result")
        self.assertEqual(state["username"], "existing")
        self.assertIsNone(state["stats"])
        self.assertIsNone(state["image_bytes"])
        self.assertIsNone(state["ui_error"])
        self.assertEqual(state["wrapped_cards"], ())
        self.assertEqual(state["selected_card_index"], 0)
        self.assertIsNone(state["diary_csv_bytes"])

    def test_begin_generation_stores_uploaded_csv_bytes_for_the_run(self):
        """Would fail if the CSV-upload path lost track of which source to read."""
        state = {}
        initialize_state(state)

        begin_generation(state, "cinefan", b"Date,Name\n2026-01-01,Arrival\n")

        self.assertEqual(state["diary_csv_bytes"], b"Date,Name\n2026-01-01,Arrival\n")

        begin_generation(state, "cinefan")
        self.assertIsNone(state["diary_csv_bytes"])

    def test_generation_result_and_reset_lifecycle(self):
        state = {}
        initialize_state(state)

        begin_generation(state, "  @cinefan  ")
        self.assertEqual(
            state,
            {
                "stage": "generating",
                "username": "cinefan",
                "stats": None,
                "image_bytes": None,
                "ui_error": None,
                "wrapped_cards": (),
                "selected_card_index": 0,
                "diary_csv_bytes": None,
            },
        )

        stats = object()
        image_bytes = b"png"
        set_result(state, stats, image_bytes)
        self.assertEqual(state["stage"], "result")
        self.assertIs(state["stats"], stats)
        self.assertIs(state["image_bytes"], image_bytes)
        self.assertEqual(state["wrapped_cards"], ())
        self.assertEqual(state["selected_card_index"], 0)
        self.assertIsNone(state["ui_error"])

        reset_generation(state)
        self.assertEqual(
            state,
            {
                "stage": "landing",
                "username": "",
                "stats": None,
                "image_bytes": None,
                "ui_error": None,
                "wrapped_cards": (),
                "selected_card_index": 0,
                "diary_csv_bytes": None,
            },
        )

    def test_set_error_clears_partial_results_and_enters_error_stage(self):
        state = {
            "stage": "generating",
            "stats": object(),
            "image_bytes": b"partial",
        }
        error = object()

        set_error(state, error)

        self.assertEqual(state["stage"], "error")
        self.assertIsNone(state["stats"])
        self.assertIsNone(state["image_bytes"])
        self.assertEqual(state["wrapped_cards"], ())
        self.assertEqual(state["selected_card_index"], 0)
        self.assertIs(state["ui_error"], error)

    def test_card_result_is_immutable_and_resets_selection(self):
        """Would fail if enhanced results retained a mutable list or stale index."""
        cards = [
            RenderedCard("overview", "Overview", "overview.png", b"one"),
            RenderedCard("personality", "Personality", "personality.png", b"two"),
        ]
        state = {"selected_card_index": 1, "image_bytes": b"legacy"}

        set_result(state, object(), cards)
        cards.clear()

        self.assertEqual(len(state["wrapped_cards"]), 2)
        self.assertIsInstance(state["wrapped_cards"], tuple)
        self.assertEqual(state["selected_card_index"], 0)
        self.assertIsNone(state["image_bytes"])

    def test_card_navigation_clamps_at_both_bounds(self):
        """Would fail if repeated navigation escaped the available card range."""
        state = {"wrapped_cards": (object(),) * 6, "selected_card_index": 0}

        select_previous_card(state)
        self.assertEqual(state["selected_card_index"], 0)
        for _ in range(8):
            select_next_card(state)
        self.assertEqual(state["selected_card_index"], 5)
        for _ in range(8):
            select_previous_card(state)
        self.assertEqual(state["selected_card_index"], 0)

    def test_empty_navigation_normalizes_stale_index_to_zero(self):
        """Would fail if an empty card result could retain an invalid selection."""
        state = {"wrapped_cards": (), "selected_card_index": 99}

        select_next_card(state)
        self.assertEqual(state["selected_card_index"], 0)
        state["selected_card_index"] = -5
        select_previous_card(state)
        self.assertEqual(state["selected_card_index"], 0)


if __name__ == "__main__":
    unittest.main()
