# Task 3: Build the result experience and stage coordinator

## Context and constraints

Wire the approved Task 1 state/errors and Task 2 components into the real app, and create the result component. Preserve `cinephile_wrapped/data.py`, `analysis.py`, and `render.py` unchanged; preserve original PNG bytes and download behavior; no new dependency or global user cache; English UI; safe username rendering only through native Streamlit text APIs or escaping. Workspace has no Git metadata, so skip commits.

## Files

- Create `components/result.py`
- Modify `app.py`
- Modify `components/errors.py` only if needed to support the retry UI cleanly
- Extend `tests/test_ui_state.py` only if the explicit error-transition test is absent
- Add focused dependency-free coordinator/result tests if needed

## Existing interfaces

- Task 1: `initialize_state`, `begin_generation`, `set_result`, `set_error`, `reset_generation`; `UiError`, `map_exception`, `render_error`.
- Task 2: `load_styles`, `render_header`, `render_hero`, `render_features`, `render_footer`, `render_generator_form`, `render_loading_shell`.
- Core: `get_diary_entries(username)`, `compute_stats(username, entries)`, `render_to_bytes(stats)`, and `WrappedStats`.

## Result interface

Implement `render_result(stats: WrappedStats, image_bytes: bytes) -> bool`. Use native Streamlit text for the dynamic username. Display:

- Caption `THE FINAL CUT`
- Heading `This was @username's recent chapter in cinema.`
- Copy `A story told through movies, months and memories.`
- Four real statistics: total films, peak month, peak-month film count, and active month count calculated as `sum(int(value) > 0 for value in stats.monthly_counts.tolist())`
- The exact original `image_bytes` in `st.image`, fully visible, captioned for the username
- `Download Story` using the exact same bytes, `wrapped_<username>.png`, MIME `image/png`, container width
- `Create Another`, container width; return its boolean

Use native Streamlit containers/columns and semantic application markers/classes without attempting to wrap native widgets across separate HTML calls.

## App coordinator

Replace the current inline dashboard UI with a thin four-stage coordinator.

1. `st.set_page_config` is the first Streamlit call: title `Cinephile Wrapped`, page icon `🎬`, layout `wide`, sidebar `collapsed`.
2. Load CSS, initialize `st.session_state`, render header globally.
3. `landing`: render hero, form, features, footer. A blank submitted value must never call Letterboxd; create a `UiError` titled `A username belongs in the starring role.` with safe explanatory/action copy, call `set_error`, and rerun. A valid submission calls `begin_generation` and reruns.
4. `generating`: render the loading shell, then run each operation once in order. Update progress/status around real operations at 15 (opening diary), 55 (finding patterns), 85 (designing story), and 100 (complete). Call `get_diary_entries`, `compute_stats`, then `render_to_bytes`. Do not add sleeps. On success call `set_result` and rerun.
5. Catch expected and unexpected exceptions around generation, log full details server-side with `logging.exception`, map safely with `map_exception`, call `set_error`, rerun. Never show raw exception text or traceback.
6. `result`: call `render_result`; if it returns true, reset and rerun.
7. `error`: call `render_error`; a native `Try Again` button resets and reruns. Render footer.
8. No fetch/render occurs in landing, result, or error. Stored session stats/bytes prevent rerun duplication.

The status and progress handles returned by Task 2 support `status.update(label=..., state=..., expanded=...)` and `progress.progress(value, text=...)`. Complete/close status only after all steps.

## Testing and verification

Ensure the existing explicit `set_error` lifecycle test passes. Add dependency-free tests with a fake Streamlit module or extracted pure coordinator helpers only where they add real value: verify blank submission cannot reach the fetch path, result passes exact bytes to image/download, active month calculation, and reset booleans. Do not add pytest.

Run all existing focused test functions directly using `.venv\Scripts\python.exe` (or a small unittest runner if tests use unittest), then `.venv\Scripts\python.exe -m compileall .`. Do not attempt live browser verification yet; Task 4 owns it.

Self-review stage transitions, rerun behavior, no duplicate generation, safe dynamic content, exact byte preservation, exception logging, and unchanged core modules.

Write the full report to `.superpowers/sdd/2026-07-28-cinematic-streamlit-redesign/task-3-report.md`, including files, tests/commands/output, self-review, concerns, and confirmation that the three core modules were untouched. Return short status contract only.
