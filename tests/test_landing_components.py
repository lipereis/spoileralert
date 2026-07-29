from __future__ import annotations

import unittest
from unittest.mock import patch

from components import generator, layout


class _Form:
    def __init__(self, streamlit_double):
        self.streamlit_double = streamlit_double

    def __enter__(self):
        self.streamlit_double.in_form = True
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.streamlit_double.in_form = False
        return False


class _StreamlitDouble:
    def __init__(self, *, submitted: bool = False):
        self.submitted = submitted
        self.markdown_calls: list[tuple[str, bool]] = []
        self.text_input_calls: list[tuple[str, dict[str, object]]] = []
        self.form_calls: list[tuple[str, dict[str, object]]] = []
        self.submit_calls: list[tuple[str, dict[str, object]]] = []
        self.status_calls: list[tuple[str, dict[str, object]]] = []
        self.progress_calls: list[tuple[int, dict[str, object]]] = []
        self.form_content_calls: list[tuple[str, bool]] = []
        self.in_form = False
        self.status_handle = object()
        self.progress_handle = object()

    def markdown(self, body: str, *, unsafe_allow_html: bool = False):
        self.markdown_calls.append((body, unsafe_allow_html))
        self.form_content_calls.append(("markdown", self.in_form))

    def caption(self, _body: str):
        return None

    def subheader(self, _body: str):
        return None

    def write(self, _body: str):
        return None

    def form(self, name: str, **kwargs):
        self.form_calls.append((name, kwargs))
        return _Form(self)

    def text_input(self, label: str, **kwargs):
        self.text_input_calls.append((label, kwargs))
        self.form_content_calls.append(("text_input", self.in_form))
        return "  cinefan  "

    def form_submit_button(self, label: str, **kwargs):
        self.submit_calls.append((label, kwargs))
        self.form_content_calls.append(("submit", self.in_form))
        return self.submitted

    def status(self, label: str, **kwargs):
        self.status_calls.append((label, kwargs))
        return self.status_handle

    def progress(self, value: int, **kwargs):
        self.progress_calls.append((value, kwargs))
        return self.progress_handle


class LandingComponentTests(unittest.TestCase):
    def test_stylesheet_is_read_and_injected_as_one_style_block(self):
        st = _StreamlitDouble()
        with patch.object(layout, "st", st):
            layout.load_styles()

        self.assertEqual(len(st.markdown_calls), 1)
        css, unsafe = st.markdown_calls[0]
        self.assertTrue(css.startswith("<style>"))
        self.assertTrue(css.endswith("</style>"))
        self.assertTrue(unsafe)

    def test_static_layout_renders_the_approved_copy(self):
        st = _StreamlitDouble()
        with patch.object(layout, "st", st):
            layout.render_header()
            layout.render_hero()
            layout.render_features()
            layout.render_footer()

        rendered = "".join(body for body, _ in st.markdown_calls)
        expected = (
            "SpoilerAlert",
            "Your year in cinema",
            "YOUR YEAR IN CINEMA",
            "Discover the story behind your movie taste.",
            "Turn your Letterboxd diary into a personal, cinematic and shareable visual experience.",
            "01",
            "Movie DNA",
            "Discover the genres, decades and viewing patterns shaping your movie taste.",
            "02",
            "Cinema Personality",
            "Turn your complete current-year diary into a memorable and shareable cinephile identity.",
            "03",
            "Story-Ready Design",
            "Export a polished 1080×1920 visual made for social media.",
            "Built for people who see every movie as part of a bigger story.",
            "Not affiliated with Letterboxd.",
        )
        for copy in expected:
            self.assertIn(copy, rendered)

    def test_generator_returns_username_only_after_native_form_submission(self):
        not_submitted = _StreamlitDouble(submitted=False)
        with patch.object(generator, "st", not_submitted):
            self.assertIsNone(generator.render_generator_form())

        submitted = _StreamlitDouble(submitted=True)
        with patch.object(generator, "st", submitted):
            self.assertEqual(generator.render_generator_form(), "  cinefan  ")

        self.assertEqual(submitted.form_calls, [("generator_form", {"clear_on_submit": False})])
        self.assertEqual(
            submitted.submit_calls,
            [("Generate My Wrapped", {"width": "stretch"})],
        )
        self.assertEqual(
            submitted.text_input_calls,
            [
                (
                    "Letterboxd username",
                    {"placeholder": "e.g. nmcassa", "autocomplete": "username"},
                )
            ],
        )
        self.assertEqual(
            submitted.form_content_calls,
            [
                ("markdown", True),
                ("text_input", True),
                ("submit", True),
                ("markdown", True),
            ],
        )
        intro, trust = (body for body, _ in submitted.markdown_calls)
        self.assertIn('class="generator-panel__intro"', intro)
        self.assertIn("</section>", intro)
        self.assertNotIn('class="generator-panel"', intro)
        self.assertNotIn("</section>", trust)
        self.assertIn(
            "Only public Letterboxd profile information is analyzed. Your data is not permanently stored.",
            trust,
        )

    def test_loading_shell_returns_status_and_progress_handles(self):
        st = _StreamlitDouble()
        with patch.object(generator, "st", st):
            handles = generator.render_loading_shell()

        self.assertEqual(handles, (st.status_handle, st.progress_handle))
        self.assertEqual(
            st.status_calls,
            [("Opening your complete Letterboxd diary…", {"expanded": True})],
        )
        self.assertEqual(
            st.progress_calls,
            [(0, {"text": "Preparing the complete-year analysis"})],
        )


if __name__ == "__main__":
    unittest.main()
