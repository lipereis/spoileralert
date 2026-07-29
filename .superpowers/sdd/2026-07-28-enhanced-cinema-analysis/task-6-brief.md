# Task 6 implementation brief — State, Gallery, Downloads, ZIP

Implement Task 6 from the approved plan with TDD. Modify `spoileralert/ui_state.py`, `components/result.py`, and `styles/main.css`; add `tests/test_result_gallery.py` and extend `tests/test_ui_state.py` while preserving existing result tests and current visual language.

Add immutable ordered card state and a clamped selected index. `set_result(state, stats, cards)` stores cards/resets index while keeping a compatibility path for existing callers during migration. Reset clears all enhanced/card state. Previous/next navigation must clamp safely for empty and six-card collections.

Build ZIP entirely in memory: safe sanitized username-derived archive filename is UI concern; archive entries must be exactly the six stable card filenames in registry order and payloads byte-identical, with no temp files/path traversal/duplicates.

Result UI keeps existing header/statistics/Create Another, adds native numbered card selector, selected preview, Previous/Next, selected-card download, all six individual downloads, and ZIP download. Use current Streamlit 1.60 APIs (`width="stretch"` where appropriate), stable keys/containers, keyboard focus, responsive stacking, and reduced-motion compatibility. Avoid unsafe HTML with username.

Tests cover state defaults/migration/reset, bounds/empty navigation, exact ZIP entry order/bytes, duplicate/unsafe filename defenses, gallery controls/download metadata and legacy compatibility. Run focused UI/gallery, existing result tests, full discovery, and compileall. Write exact RED/GREEN evidence to `task-6-report.md`. No Git commit.
