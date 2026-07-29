from __future__ import annotations

import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from streamlit.testing.v1 import AppTest

from components import result
from spoileralert.models import RenderedCard


CARD_SPECS = (
    ("overview", "Overview"),
    ("personality", "Cinema Personality"),
    ("movie-dna", "Movie DNA"),
    ("moods", "Mood Analysis"),
    ("directors", "Director Universe"),
    ("timeline", "Viewing Timeline"),
)


def card_fixture(*, username: str = "cinefan") -> tuple[RenderedCard, ...]:
    return tuple(
        RenderedCard(
            slug=slug,
            title=title,
            filename=f"spoileralert-{username}-{slug}.png",
            png_bytes=f"png-{slug}".encode("ascii"),
        )
        for slug, title in CARD_SPECS
    )


class _Container:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _MetricColumn:
    def metric(self, label: str, value: object):
        pass


class _GalleryStreamlitDouble:
    def __init__(self, *, selected: int = 0, button_label: str | None = None):
        self.session_state = {"selected_card_index": selected}
        self.button_label = button_label
        self.container_keys: list[str] = []
        self.selectbox_calls: list[tuple[str, tuple[int, ...], dict[str, object]]] = []
        self.image_calls: list[tuple[object, dict[str, object]]] = []
        self.download_calls: list[tuple[str, object, dict[str, object]]] = []
        self.button_calls: list[tuple[str, dict[str, object]]] = []

    def container(self, *, key: str, **kwargs):
        self.container_keys.append(key)
        return _Container()

    def caption(self, body: str):
        pass

    def title(self, body: str):
        pass

    def write(self, body: str):
        pass

    def subheader(self, body: str):
        pass

    def columns(self, count: int):
        return [_MetricColumn() for _ in range(count)]

    def selectbox(self, label: str, options, **kwargs):
        values = tuple(options)
        self.selectbox_calls.append((label, values, kwargs))
        selected = self.session_state.get(
            kwargs["key"],
            values[kwargs.get("index", 0)],
        )
        self.session_state[kwargs["key"]] = selected
        return selected

    def image(self, image: object, **kwargs):
        self.image_calls.append((image, kwargs))

    def download_button(self, label: str, data: object, **kwargs):
        self.download_calls.append((label, data, kwargs))
        return False

    def button(self, label: str, **kwargs):
        self.button_calls.append((label, kwargs))
        clicked = label == self.button_label and not kwargs.get("disabled", False)
        if clicked and kwargs.get("on_click") is not None:
            kwargs["on_click"](*kwargs.get("args", ()))
        return clicked


def gallery_stats(username: str = "cinefan"):
    overview = SimpleNamespace(
        username=username,
        total_movies=12,
        peak_month_label="Maio",
        peak_month_count=4,
        monthly_counts=SimpleNamespace(tolist=lambda: [1, 0, 2, 0, 4]),
    )
    return SimpleNamespace(overview=overview)


def _render_real_enhanced_gallery() -> None:
    """Standalone script body consumed by Streamlit's real AppTest runner."""
    from components.result import render_result
    from spoileralert.render import render_story_cards
    from tests.test_card_renderers import enhanced_fixture

    stats = enhanced_fixture()
    render_result(stats, render_story_cards(stats))


class ResultGalleryTests(unittest.TestCase):
    def test_real_streamlit_gallery_renders_without_widget_state_exception(self):
        """Would fail if gallery code writes a keyed widget state after creation."""
        app = AppTest.from_function(
            _render_real_enhanced_gallery,
            default_timeout=10,
        ).run()

        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual([box.label for box in app.selectbox], ["Choose a story card"])
        self.assertEqual(
            [button.label for button in app.button],
            ["Previous", "Next", "Create Another"],
        )
        self.assertEqual(len(app.image), 1)
        self.assertEqual(len(app.download_button), 8)

    def test_real_streamlit_previous_and_next_callbacks_survive_reruns(self):
        """Would fail if navigation mutates widget state after instantiation."""
        app = AppTest.from_function(
            _render_real_enhanced_gallery,
            default_timeout=10,
        ).run()
        self.assertEqual([exception.message for exception in app.exception], [])

        app = next(button for button in app.button if button.key == "next-card").click().run()
        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["selected_card_index"], 1)

        app = next(button for button in app.button if button.key == "previous-card").click().run()
        self.assertEqual([exception.message for exception in app.exception], [])
        self.assertEqual(app.session_state["selected_card_index"], 0)

    def test_gallery_css_has_stable_anchors_and_mobile_stacking(self):
        """Would fail if the gallery lost its responsive application-owned anchors."""
        css = (
            Path(__file__).resolve().parents[1] / "styles" / "main.css"
        ).read_text(encoding="utf-8")

        for key in (
            "card-selector",
            "card-navigation",
            "selected-card-download",
            "card-download-list",
            "zip-download",
        ):
            self.assertIn(f".st-key-{key}", css)
        self.assertIn("@media (max-width: 768px)", css)
        self.assertIn("@media (max-width: 480px)", css)
        self.assertIn(".st-key-card-navigation", css[css.index("@media (max-width: 768px)"):])

    def test_zip_contains_six_original_payloads_in_registry_order(self):
        """Would fail if ZIP construction reordered, transformed, or omitted cards."""
        cards = card_fixture()

        payload = result.build_cards_zip("cinefan", cards)

        with ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(archive.namelist(), [card.filename for card in cards])
            for card in cards:
                self.assertEqual(archive.read(card.filename), card.png_bytes)

    def test_zip_rejects_wrong_order_duplicate_and_unsafe_filenames(self):
        """Would fail if malformed card collections could create ambiguous ZIPs."""
        cards = card_fixture()
        with self.assertRaises(ValueError):
            result.build_cards_zip("cinefan", (cards[1], cards[0], *cards[2:]))

        duplicate = list(cards)
        duplicate[-1] = RenderedCard(
            "timeline", "Viewing Timeline", cards[0].filename, b"duplicate"
        )
        with self.assertRaises(ValueError):
            result.build_cards_zip("cinefan", duplicate)

        unsafe = list(cards)
        unsafe[0] = RenderedCard(
            "overview", "Overview", "../spoileralert-overview.png", b"unsafe"
        )
        with self.assertRaises(ValueError):
            result.build_cards_zip("cinefan", unsafe)

        drive_qualified = list(cards)
        drive_qualified[0] = RenderedCard(
            "overview", "Overview", "C:spoileralert-overview.png", b"unsafe"
        )
        with self.assertRaises(ValueError):
            result.build_cards_zip("cinefan", drive_qualified)

        with self.assertRaises(ValueError):
            result.build_cards_zip("cinefan", cards[:-1])

    def test_archive_filename_sanitizes_untrusted_username(self):
        """Would fail if the UI exposed path characters from a username."""
        self.assertEqual(
            result.cards_zip_filename("  @Ciné/../Fan  "),
            "spoileralert-cine-fan-cards.zip",
        )
        self.assertEqual(
            result.cards_zip_filename("../../"),
            "spoileralert-user-cards.zip",
        )

    def test_gallery_renders_selector_preview_and_exact_download_metadata(self):
        """Would fail if selected/all-card downloads altered bytes or filenames."""
        cards = card_fixture()
        st = _GalleryStreamlitDouble(selected=2)

        with patch.object(result, "st", st):
            reset_requested = result.render_result(gallery_stats(), cards)

        self.assertFalse(reset_requested)
        self.assertEqual(
            st.container_keys,
            [
                "result-header",
                "stats-grid",
                "card-selector",
                "card-navigation",
                "story-preview",
                "selected-card-download",
                "card-download-list",
                "zip-download",
                "result-actions",
            ],
        )
        label, options, select_options = st.selectbox_calls[0]
        self.assertEqual(label, "Choose a story card")
        self.assertEqual(options, tuple(range(6)))
        self.assertNotIn("index", select_options)
        self.assertEqual(select_options["key"], "selected_card_index")
        self.assertEqual(select_options["width"], "stretch")
        self.assertEqual(st.image_calls[0][0], cards[2].png_bytes)
        self.assertEqual(
            st.image_calls[0][1],
            {"caption": "03 of 06 · Movie DNA", "width": "stretch"},
        )

        selected = st.download_calls[0]
        self.assertEqual(selected[0], "Download selected card")
        self.assertIs(selected[1], cards[2].png_bytes)
        self.assertEqual(selected[2]["file_name"], cards[2].filename)
        individual = st.download_calls[1:7]
        self.assertEqual([call[1] for call in individual], [c.png_bytes for c in cards])
        self.assertEqual([call[2]["file_name"] for call in individual], [c.filename for c in cards])
        archive = st.download_calls[7]
        self.assertEqual(archive[0], "Download all six cards")
        self.assertEqual(archive[2]["file_name"], "spoileralert-cinefan-cards.zip")
        self.assertEqual(archive[2]["mime"], "application/zip")

    def test_previous_and_next_controls_clamp_state_before_preview(self):
        """Would fail if navigation previewed a stale or out-of-range card."""
        cards = card_fixture()
        next_st = _GalleryStreamlitDouble(selected=4, button_label="Next")
        with patch.object(result, "st", next_st):
            result.render_result(gallery_stats(), cards)
        self.assertEqual(next_st.session_state["selected_card_index"], 5)
        self.assertIs(next_st.image_calls[0][0], cards[5].png_bytes)

        previous_st = _GalleryStreamlitDouble(selected=0, button_label="Previous")
        with patch.object(result, "st", previous_st):
            result.render_result(gallery_stats(), cards)
        self.assertEqual(previous_st.session_state["selected_card_index"], 0)
        self.assertIs(previous_st.image_calls[0][0], cards[0].png_bytes)


if __name__ == "__main__":
    unittest.main()
