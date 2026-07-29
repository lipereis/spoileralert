# Task 1: Add deterministic UI state and safe error mapping

## Context and constraints

Create only the state/error foundation for the Cinephile Wrapped Streamlit redesign. Keep Streamlit Cloud compatibility, add no runtime dependencies, keep interface copy English, do not touch `cinephile_wrapped/data.py`, `analysis.py`, or `render.py`, do not globally cache user data, and do not expose raw exceptions. This workspace has no Git metadata, so skip commit commands and report that fact.

## Files

- Create `cinephile_wrapped/ui_state.py`
- Create `components/__init__.py`
- Create `components/errors.py`
- Create `tests/test_ui_state.py`
- Create `tests/test_ui_errors.py`

## Required interfaces

- `Stage = Literal["landing", "generating", "result", "error"]`
- `initialize_state(state) -> None`
- `begin_generation(state, username) -> None`
- `set_result(state, stats, image_bytes) -> None`
- `set_error(state, error) -> None`
- `reset_generation(state) -> None`
- frozen dataclass `UiError(title: str, message: str, action: str)`
- `map_exception(exc: Exception) -> UiError`
- `render_error(error: UiError) -> None`

State defaults are exactly `stage="landing"`, `username=""`, `stats=None`, `image_bytes=None`, and `ui_error=None`. Initialization preserves existing values. Generation strips whitespace and a leading `@`, clears result/error values, and enters `generating`. Result enters `result`, stores stats and the original bytes, and clears errors. Error enters `error`, clears partial result data, and stores the safe error. Reset restores the exact defaults.

Map `ProfileNotFoundError` to title `We could not open this diary.`, a message that does not include raw exception text, and an action mentioning a public profile. Map `EmptyDiaryError` to title `There is not enough diary activity yet.` and a message mentioning recent diary activity. Map `ConnectionError` and `TimeoutError` to title `Letterboxd is taking a break.` without raw details. Map all other exceptions to title `The reel stopped unexpectedly.` without raw details. `render_error` must use Streamlit primitives and application-owned `error-panel` markup; do not place untrusted data in HTML.

## TDD requirements

Create tests asserting:

1. Initialization preserves an existing `stage` and `username` while adding every missing default.
2. Begin-generation, result, and reset follow the exact lifecycle above.
3. `set_error` clears partial `stats` and `image_bytes`, stores the error, and enters `error`.
4. Profile error output omits secret raw text and mentions public visibility in its recovery action.
5. Empty-diary output has the required title and mentions recent activity.
6. Network and unexpected outputs use their required titles and omit raw secret/internal text.

Run the tests before implementation and capture the expected import failure. Then implement the minimal code and rerun. Prefer the workspace interpreter if the shell `python` launcher is broken: `.venv\Scripts\python.exe -m pytest ...`. If pytest is unavailable, report the exact blocker before adding any dependency.

## Report

Write the full report to `.superpowers/sdd/2026-07-28-cinematic-streamlit-redesign/task-1-report.md` with files changed, RED and GREEN commands/output, test totals, self-review, and concerns. Return only the short status contract to the controller.
