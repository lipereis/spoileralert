from __future__ import annotations

import runpy
import unittest
from pathlib import Path


class RenderImportTests(unittest.TestCase):
    def test_render_module_resolves_analysis_when_loaded_by_file_path(self) -> None:
        render_path = Path(__file__).resolve().parents[1] / "spoileralert" / "render.py"

        namespace = runpy.run_path(str(render_path))

        self.assertIn("render_to_bytes", namespace)


if __name__ == "__main__":
    unittest.main()
