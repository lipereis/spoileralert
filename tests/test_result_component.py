from __future__ import annotations

import inspect
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import streamlit

from components import result
from spoileralert.analysis import WrappedStats


class _Container:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _MetricColumn:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []

    def metric(self, label: str, value: object):
        self.calls.append((label, value))


class _ResultStreamlitDouble:
    def __init__(self, *, create_another: bool):
        self.create_another = create_another
        self.container_keys: list[str] = []
        self.captions: list[str] = []
        self.titles: list[str] = []
        self.writes: list[str] = []
        self.metric_columns = [_MetricColumn() for _ in range(4)]
        self.image_calls: list[tuple[object, dict[str, object]]] = []
        self.download_calls: list[tuple[str, object, dict[str, object]]] = []
        self.button_calls: list[tuple[str, dict[str, object]]] = []

    def container(self, *, key: str):
        self.container_keys.append(key)
        return _Container()

    def caption(self, body: str):
        self.captions.append(body)

    def title(self, body: str):
        self.titles.append(body)

    def write(self, body: str):
        self.writes.append(body)

    def columns(self, count: int):
        assert count == 4
        return self.metric_columns

    def image(self, image: object, **kwargs):
        self.image_calls.append((image, kwargs))

    def download_button(self, label: str, data: object, **kwargs):
        self.download_calls.append((label, data, kwargs))

    def button(self, label: str, **kwargs):
        self.button_calls.append((label, kwargs))
        return self.create_another


class ResultComponentTests(unittest.TestCase):
    def test_installed_streamlit_exposes_result_component_apis(self):
        self.assertIn("key", inspect.signature(streamlit.container).parameters)
        self.assertIn(
            "use_container_width",
            inspect.signature(streamlit.image).parameters,
        )

    def test_result_css_uses_keyed_container_anchors_and_stable_test_ids(self):
        css_path = Path(__file__).resolve().parents[1] / "styles" / "main.css"
        css = css_path.read_text(encoding="utf-8")

        for key in (
            "result-header",
            "stats-grid",
            "story-preview",
            "result-actions",
        ):
            self.assertIn(f".st-key-{key}", css)

        legacy_selector = re.compile(
            r"(?<![\w-])\.(?:result-header|stats-grid|story-preview|result-actions)\b"
        )
        self.assertIsNone(legacy_selector.search(css))
        self.assertIn(
            '.st-key-stats-grid div[data-testid="stHorizontalBlock"]',
            css,
        )
        self.assertIn(
            '.st-key-stats-grid div[data-testid="stMetric"]',
            css,
        )
        self.assertIn(
            '.st-key-story-preview div[data-testid="stImage"] img',
            css,
        )
        self.assertIn(
            '.st-key-result-actions div[data-testid="stDownloadButton"] > button',
            css,
        )

    def test_result_css_keeps_download_primary_and_create_another_secondary(self):
        css_path = Path(__file__).resolve().parents[1] / "styles" / "main.css"
        css = css_path.read_text(encoding="utf-8")
        selector = (
            '.st-key-result-actions div[data-testid="stButton"] > button'
        )
        match = re.search(re.escape(selector) + r"\s*\{([^}]+)\}", css)

        self.assertIsNotNone(match)
        assert match is not None
        declarations = match.group(1)
        self.assertIn("background: transparent", declarations)
        self.assertIn("color: var(--cw-text)", declarations)
        self.assertIn("box-shadow: none", declarations)
        self.assertNotIn(".stDownloadButton", selector)

    def test_result_grid_responsive_rules_use_the_keyed_anchor(self):
        css_path = Path(__file__).resolve().parents[1] / "styles" / "main.css"
        css = css_path.read_text(encoding="utf-8")
        grid_selector = (
            '.st-key-stats-grid div[data-testid="stHorizontalBlock"]'
        )

        self.assertGreaterEqual(css.count(grid_selector), 3)
        self.assertIn("@media (max-width: 1024px)", css)
        self.assertIn("@media (max-width: 768px)", css)

    def test_result_preserves_png_bytes_and_derives_all_four_statistics(self):
        image_bytes = b"\x89PNG\r\n\x1a\nexact-original"
        stats = SimpleNamespace(
            username="cinefan",
            total_movies=17,
            peak_month_label="Maio",
            peak_month_count=6,
            monthly_counts=SimpleNamespace(
                tolist=lambda: [0, 2, 0, 1, 4, 0, 0, 0, 3, 0, 0, 0]
            ),
        )
        st = _ResultStreamlitDouble(create_another=False)

        with patch.object(result, "st", st):
            reset_requested = result.render_result(cast(WrappedStats, stats), image_bytes)

        self.assertFalse(reset_requested)
        self.assertEqual(st.container_keys, ["result-header", "stats-grid", "story-preview", "result-actions"])
        self.assertEqual(st.captions, ["THE FINAL CUT"])
        self.assertEqual(
            st.titles,
            ["This was @cinefan's year in cinema."],
        )
        self.assertEqual(
            st.writes,
            ["A story told through movies, months and memories."],
        )
        self.assertEqual(
            [column.calls for column in st.metric_columns],
            [
                [("Total films", 17)],
                [("Peak month", "May")],
                [("Peak-month films", 6)],
                [("Active months", 4)],
            ],
        )
        self.assertIs(st.image_calls[0][0], image_bytes)
        self.assertEqual(
            st.image_calls[0][1],
            {
                "caption": "@cinefan's SpoilerAlert",
                "width": "stretch",
            },
        )
        label, download_data, download_options = st.download_calls[0]
        self.assertEqual(label, "Download Story")
        self.assertIs(download_data, image_bytes)
        self.assertEqual(
            download_options,
            {
                "file_name": "wrapped_cinefan.png",
                "mime": "image/png",
                "width": "stretch",
            },
        )
        self.assertEqual(
            st.button_calls,
            [("Create Another", {"width": "stretch"})],
        )

    def test_result_returns_create_another_button_boolean(self):
        stats = SimpleNamespace(
            username="cinefan",
            total_movies=1,
            peak_month_label="Julho",
            peak_month_count=1,
            monthly_counts=SimpleNamespace(tolist=lambda: [1]),
        )
        st = _ResultStreamlitDouble(create_another=True)

        with patch.object(result, "st", st):
            reset_requested = result.render_result(cast(WrappedStats, stats), b"png")

        self.assertTrue(reset_requested)

    def test_legacy_download_filename_sanitizes_untrusted_username(self):
        """Would fail if path-like username characters reached download metadata."""
        stats = SimpleNamespace(
            username="  @Ciné/../Fan  ",
            total_movies=1,
            peak_month_label="Julho",
            peak_month_count=1,
            monthly_counts=SimpleNamespace(tolist=lambda: [1]),
        )
        st = _ResultStreamlitDouble(create_another=False)

        with patch.object(result, "st", st):
            result.render_result(cast(WrappedStats, stats), b"png")

        self.assertEqual(st.download_calls[0][2]["file_name"], "wrapped_cine-fan.png")

    def test_result_preserves_unknown_peak_month_label_as_safe_fallback(self):
        stats = SimpleNamespace(
            username="cinefan",
            total_movies=1,
            peak_month_label="Festival month",
            peak_month_count=1,
            monthly_counts=SimpleNamespace(tolist=lambda: [1]),
        )
        st = _ResultStreamlitDouble(create_another=False)

        with patch.object(result, "st", st):
            result.render_result(cast(WrappedStats, stats), b"png")

        self.assertEqual(
            st.metric_columns[1].calls,
            [("Peak month", "Festival month")],
        )


if __name__ == "__main__":
    unittest.main()
