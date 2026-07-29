# SpoilerAlert Cinematic Streamlit Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a premium, responsive, cinematic Streamlit experience around the existing Letterboxd analysis and unchanged 1080x1920 PNG generator.

**Architecture:** Keep `app.py` as a thin stage coordinator and preserve the existing data, analysis, and Pillow modules. Add focused UI state/error helpers, reusable rendering components, one dedicated stylesheet, and a matching Streamlit theme; store user-specific results only in per-session state.

**Tech Stack:** Python 3, Streamlit >=1.35, pandas >=2.2, Pillow >=10.3, letterboxdpy >=6.0, CSS, pytest for focused helper tests.

## Global Constraints

- Keep Python and Streamlit as the main stack and remain compatible with Streamlit Cloud.
- Do not change `spoileralert/data.py`, `analysis.py`, or `render.py` unless a verified UI integration defect requires it.
- Preserve the current exported PNG design and download bytes.
- Add no runtime dependency unless existing Streamlit and Python APIs cannot meet a requirement.
- Keep the interface English-only for this iteration.
- Never interpolate raw username input into HTML; use Streamlit text APIs or `html.escape` first.
- Keep custom HTML limited to owned presentation fragments; use native Streamlit controls for input, status, image, and download.
- Support 1440px, 1024px, 768px, and 390px widths without horizontal scrolling.
- Provide a `prefers-reduced-motion: reduce` override.
- Do not globally cache user-specific diary, statistics, or image data.
- The workspace currently has no `.git` directory. Treat each commit step as the intended checkpoint and skip the command unless repository metadata becomes available.

---

## File Map

- Modify `app.py`: configure Streamlit, load styles, initialize session state, coordinate generation, and select the active view.
- Create `components/__init__.py`: declare the UI component package.
- Create `components/layout.py`: stylesheet loader, site header, hero, feature cards, and footer.
- Create `components/generator.py`: username form and loading/status presentation.
- Create `components/result.py`: result header, statistics, preview, download, and reset controls.
- Create `components/errors.py`: safe error model, exception mapping, and error rendering.
- Create `spoileralert/ui_state.py`: typed UI stage constants and per-session state helpers without importing Streamlit.
- Create `styles/main.css`: design tokens, layout, native-widget styling, responsive rules, and motion rules.
- Create `.streamlit/config.toml`: matching dark Streamlit theme.
- Create `tests/test_ui_state.py`: state initialization and reset coverage.
- Create `tests/test_ui_errors.py`: safe error mapping coverage.
- Modify `README.md`: document the redesigned flow and unchanged run command.

---

### Task 1: Add deterministic UI state and safe error mapping

**Files:**
- Create: `spoileralert/ui_state.py`
- Create: `components/__init__.py`
- Create: `components/errors.py`
- Create: `tests/test_ui_state.py`
- Create: `tests/test_ui_errors.py`

**Interfaces:**
- Consumes: `ProfileNotFoundError`, `EmptyDiaryError`, and a mutable mapping compatible with `st.session_state`.
- Produces: `Stage = Literal["landing", "generating", "result", "error"]`, `initialize_state(state) -> None`, `begin_generation(state, username) -> None`, `set_result(state, stats, image_bytes) -> None`, `set_error(state, error) -> None`, `reset_generation(state) -> None`, `UiError`, and `map_exception(exc) -> UiError`.

- [ ] **Step 1: Write failing state tests**

```python
# tests/test_ui_state.py
from spoileralert.ui_state import (
    begin_generation,
    initialize_state,
    reset_generation,
    set_result,
)


def test_initialize_state_adds_defaults_without_overwriting_existing_values():
    state = {"stage": "result", "username": "existing"}
    initialize_state(state)
    assert state["stage"] == "result"
    assert state["username"] == "existing"
    assert state["stats"] is None
    assert state["image_bytes"] is None
    assert state["ui_error"] is None


def test_generation_result_and_reset_lifecycle():
    state = {}
    initialize_state(state)
    begin_generation(state, "  @cinefan  ")
    assert state["stage"] == "generating"
    assert state["username"] == "cinefan"

    stats = object()
    set_result(state, stats, b"png")
    assert state["stage"] == "result"
    assert state["stats"] is stats
    assert state["image_bytes"] == b"png"

    reset_generation(state)
    assert state == {
        "stage": "landing",
        "username": "",
        "stats": None,
        "image_bytes": None,
        "ui_error": None,
    }
```

- [ ] **Step 2: Write failing error-mapping tests**

```python
# tests/test_ui_errors.py
from components.errors import map_exception
from spoileralert.data import EmptyDiaryError, ProfileNotFoundError


def test_profile_error_does_not_expose_raw_exception_text():
    error = map_exception(ProfileNotFoundError("secret upstream detail"))
    assert error.title == "We could not open this diary."
    assert "secret upstream detail" not in error.message
    assert "public" in error.action


def test_empty_diary_has_specific_recovery_action():
    error = map_exception(EmptyDiaryError("raw detail"))
    assert error.title == "There is not enough diary activity yet."
    assert "recent" in error.message.lower()


def test_network_and_unexpected_errors_are_safe():
    network = map_exception(ConnectionError("api token and host detail"))
    unexpected = map_exception(RuntimeError("parser internals"))
    assert network.title == "Letterboxd is taking a break."
    assert "api token" not in network.message
    assert unexpected.title == "The reel stopped unexpectedly."
    assert "parser internals" not in unexpected.message
```

- [ ] **Step 3: Run both tests and verify they fail**

Run: `python -m pytest tests/test_ui_state.py tests/test_ui_errors.py -v`

Expected: FAIL during import because `ui_state.py` and `components/errors.py` do not exist.

- [ ] **Step 4: Implement state helpers**

```python
# spoileralert/ui_state.py
from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Literal

Stage = Literal["landing", "generating", "result", "error"]

DEFAULT_STATE: dict[str, Any] = {
    "stage": "landing",
    "username": "",
    "stats": None,
    "image_bytes": None,
    "ui_error": None,
}


def initialize_state(state: MutableMapping[str, Any]) -> None:
    for key, value in DEFAULT_STATE.items():
        state.setdefault(key, value)


def begin_generation(state: MutableMapping[str, Any], username: str) -> None:
    state["stage"] = "generating"
    state["username"] = username.strip().lstrip("@")
    state["stats"] = None
    state["image_bytes"] = None
    state["ui_error"] = None


def set_result(state: MutableMapping[str, Any], stats: Any, image_bytes: bytes) -> None:
    state["stage"] = "result"
    state["stats"] = stats
    state["image_bytes"] = image_bytes
    state["ui_error"] = None


def set_error(state: MutableMapping[str, Any], error: Any) -> None:
    state["stage"] = "error"
    state["stats"] = None
    state["image_bytes"] = None
    state["ui_error"] = error


def reset_generation(state: MutableMapping[str, Any]) -> None:
    for key, value in DEFAULT_STATE.items():
        state[key] = value
```

- [ ] **Step 5: Implement safe error mapping**

```python
# components/errors.py
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from spoileralert.data import EmptyDiaryError, ProfileNotFoundError


@dataclass(frozen=True)
class UiError:
    title: str
    message: str
    action: str


def map_exception(exc: Exception) -> UiError:
    if isinstance(exc, ProfileNotFoundError):
        return UiError(
            "We could not open this diary.",
            "The username may be misspelled, private, or unavailable.",
            "Check the spelling and confirm the Letterboxd profile is public.",
        )
    if isinstance(exc, EmptyDiaryError):
        return UiError(
            "There is not enough diary activity yet.",
            "This profile has no recent public diary entries to analyze.",
            "Add recent diary entries on Letterboxd, then try again.",
        )
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return UiError(
            "Letterboxd is taking a break.",
            "We could not reach the profile service right now.",
            "Wait a moment and try the same username again.",
        )
    return UiError(
        "The reel stopped unexpectedly.",
        "We could not finish this Wrapped safely.",
        "Try again. If the problem continues, use another public profile.",
    )


def render_error(error: UiError) -> None:
    st.markdown('<section class="error-panel" aria-live="polite">', unsafe_allow_html=True)
    st.caption("ANALYSIS INTERRUPTED")
    st.subheader(error.title)
    st.write(error.message)
    st.info(error.action, icon="ℹ️")
    st.markdown("</section>", unsafe_allow_html=True)
```

- [ ] **Step 6: Run focused tests**

Run: `python -m pytest tests/test_ui_state.py tests/test_ui_errors.py -v`

Expected: 5 tests PASS.

- [ ] **Step 7: Record the checkpoint**

If Git metadata is available:

```bash
git add spoileralert/ui_state.py components/__init__.py components/errors.py tests/test_ui_state.py tests/test_ui_errors.py
git commit -m "feat: add wrapped UI state and safe errors"
```

Otherwise, note that the checkpoint is complete without a commit.

---

### Task 2: Build the cinematic design system and landing components

**Files:**
- Create: `styles/main.css`
- Create: `.streamlit/config.toml`
- Create: `components/layout.py`
- Create: `components/generator.py`

**Interfaces:**
- Consumes: native Streamlit rendering APIs and the existing font files under `assets/fonts/`.
- Produces: `load_styles() -> None`, `render_header() -> None`, `render_hero() -> None`, `render_features() -> None`, `render_footer() -> None`, `render_generator_form() -> str | None`, and `render_loading_shell() -> tuple[DeltaGenerator, DeltaGenerator]`.

- [ ] **Step 1: Create the Streamlit theme**

```toml
# .streamlit/config.toml
[theme]
base = "dark"
primaryColor = "#00e054"
backgroundColor = "#0b0d0f"
secondaryBackgroundColor = "#171b20"
textColor = "#f5f7f8"
font = "sans serif"

[browser]
gatherUsageStats = false
```

- [ ] **Step 2: Create the stylesheet loader and static layout components**

Implement `components/layout.py` with `Path`-based CSS loading and owned semantic HTML. Use only fixed application copy in HTML. `load_styles()` reads `styles/main.css` and injects it once with `st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)`. `render_header`, `render_hero`, `render_features`, and `render_footer` render the approved copy and semantic classes from the design spec.

Required signatures and implementations:

```python
def load_styles() -> None:
    css_path = Path(__file__).resolve().parents[1] / "styles" / "main.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(HEADER_HTML, unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown(HERO_HTML, unsafe_allow_html=True)


def render_features() -> None:
    st.markdown(FEATURES_HTML, unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)
```

Define `HEADER_HTML`, `HERO_HTML`, `FEATURES_HTML`, and `FOOTER_HTML` as module constants containing only the fixed copy approved in the design spec.

The feature cards must contain the exact titles `Movie DNA`, `Cinema Personality`, and `Story-Ready Design`, numbers `01`–`03`, and the approved descriptions.

- [ ] **Step 3: Create the native generator form**

Implement `components/generator.py` using `st.form("generator_form")`, `st.text_input`, and `st.form_submit_button`. Keep the input label visible and return the entered string only when submitted.

```python
def render_generator_form() -> str | None:
    st.markdown('<section class="generator-panel">', unsafe_allow_html=True)
    st.caption("YOUR DIARY, DIRECTED")
    st.subheader("Ready for your close-up?")
    st.write("Enter a public Letterboxd username to turn recent diary activity into a cinematic story.")
    with st.form("generator_form", clear_on_submit=False):
        username = st.text_input(
            "Letterboxd username",
            placeholder="e.g. nmcassa",
            autocomplete="username",
        )
        submitted = st.form_submit_button("Generate My Wrapped", use_container_width=True)
    st.caption("Only public Letterboxd profile information is analyzed. Your data is not permanently stored.")
    st.markdown("</section>", unsafe_allow_html=True)
    return username if submitted else None
```

Add `render_loading_shell()` that creates a centered loading heading plus `status = st.status("Opening your Letterboxd diary…", expanded=True)` and `progress = st.progress(0, text="Preparing the analysis")`, returning both handles so `app.py` can update them around real operations.

- [ ] **Step 4: Implement the full CSS design system**

In `styles/main.css`, define the approved variables and local `@font-face` declarations using relative app-served paths only if they render reliably; otherwise use Poppins as a named preference with `system-ui` fallback and do not add remote font requests. Cover these selectors:

```css
:root, .stApp, .block-container, .site-header, .brand-lockup, .film-marks,
.hero, .hero-title, .hero-copy, .generator-panel, .features-grid,
.feature-card, .error-panel, .result-header, .story-preview, .stats-grid,
.stat-card, .site-footer, div[data-testid="stTextInput"] input,
.stButton > button, .stDownloadButton > button
```

Required behavior:

- 1180px maximum content width with generous section spacing.
- Static radial green and blue/orange background accents.
- 54px minimum input and button height; visible `:focus-visible` ring.
- Green-gradient primary buttons with slight upward hover, subtle shadow/brightness change, and small active compression.
- Three equal-height feature cards with low-opacity borders and subtle hover elevation.
- Responsive breakpoints at 1024px, 768px, and 480px; stacked columns and full-width actions on small screens.
- No horizontal overflow at 390px.
- 160–300ms interactions, 500–800ms entrance animations, and the approved easing curve.
- A final `@media (prefers-reduced-motion: reduce)` rule that sets animation duration near zero, disables smooth scrolling, and removes nonessential transforms.
- Avoid generated Emotion class names; use application classes and stable `data-testid` selectors only.

- [ ] **Step 5: Run static validation**

Run: `python -m compileall components spoileralert app.py`

Expected: compilation succeeds. Confirm `styles/main.css` and all three Poppins font assets exist with `Test-Path` on Windows.

- [ ] **Step 6: Record the checkpoint**

If Git metadata is available:

```bash
git add .streamlit/config.toml styles/main.css components/layout.py components/generator.py
git commit -m "feat: build cinematic landing experience"
```

Otherwise, note that the checkpoint is complete without a commit.

---

### Task 3: Build the result experience and stage coordinator

**Files:**
- Create: `components/result.py`
- Modify: `app.py`
- Modify: `components/errors.py`
- Test: `tests/test_ui_state.py`

**Interfaces:**
- Consumes: all Task 1 and Task 2 interfaces, `get_diary_entries(username)`, `compute_stats(username, entries)`, `render_to_bytes(stats)`, and `WrappedStats` fields.
- Produces: `render_result(stats: WrappedStats, image_bytes: bytes) -> bool`, where `True` means “Create Another” was selected; a complete four-stage Streamlit coordinator in `app.py`.

- [ ] **Step 1: Extend the lifecycle test for an explicit error state**

Append to `tests/test_ui_state.py`:

```python
from spoileralert.ui_state import set_error


def test_set_error_clears_partial_results():
    state = {"stage": "generating", "stats": object(), "image_bytes": b"partial"}
    error = object()
    set_error(state, error)
    assert state["stage"] == "error"
    assert state["stats"] is None
    assert state["image_bytes"] is None
    assert state["ui_error"] is error
```

- [ ] **Step 2: Run the lifecycle test**

Run: `python -m pytest tests/test_ui_state.py -v`

Expected: PASS if Task 1's contract is correct; treat any failure as a contract defect and fix `set_error` before continuing.

- [ ] **Step 3: Implement the result component**

Create `components/result.py`. Render the username with `st.caption`, `st.title`, or `st.write`, never through raw HTML. Calculate represented months as `sum(int(value) > 0 for value in stats.monthly_counts.tolist())`. Render four native Streamlit metric containers inside application-owned layout anchors, show the original `image_bytes` with `st.image`, and retain the exact bytes in `st.download_button`.

Required behavior:

```python
def render_result(stats: WrappedStats, image_bytes: bytes) -> bool:
    st.caption("THE FINAL CUT")
    st.title(f"This was @{stats.username}'s recent chapter in cinema.")
    st.write("A story told through movies, months and memories.")
    represented_months = sum(int(value) > 0 for value in stats.monthly_counts.tolist())
    columns = st.columns(4)
    columns[0].metric("Total films", stats.total_movies)
    columns[1].metric("Peak month", stats.peak_month_label)
    columns[2].metric("Peak-month films", stats.peak_month_count)
    columns[3].metric("Active months", represented_months)
    st.image(image_bytes, caption=f"@{stats.username}'s SpoilerAlert")
    st.download_button(
        "Download Story",
        image_bytes,
        file_name=f"wrapped_{stats.username}.png",
        mime="image/png",
        use_container_width=True,
    )
    return st.button("Create Another", use_container_width=True)
```

Use `use_container_width=True` for actions. Keep the PNG caption accessible and do not alter or re-encode `image_bytes`.

- [ ] **Step 4: Replace `app.py` with the thin stage coordinator**

The coordinator must:

1. Call `st.set_page_config(page_title="SpoilerAlert", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")` before other Streamlit calls.
2. Load CSS and initialize session state.
3. Render header globally.
4. On `landing`, render hero, generator form, features, and footer.
5. For blank submitted input, create a `UiError` titled `A username belongs in the starring role.` and move directly to `error` without calling Letterboxd.
6. For a valid submission, call `begin_generation`, rerun, then perform each real generation step once while the stage is `generating`.
7. Update status/progress around `get_diary_entries`, `compute_stats`, and `render_to_bytes` with values 15, 55, 85, and 100.
8. Call `set_result` and rerun on success.
9. Call `set_error(map_exception(exc))` and rerun on failure; log the exception server-side with `logging.exception` but never render it.
10. On `result`, call `render_result`; when it returns `True`, reset and rerun.
11. On `error`, render the safe error plus a `Try Again` button that resets and reruns.

Use `st.rerun()` and ensure no fetch can run in `landing`, `result`, or `error` stages.

- [ ] **Step 5: Run focused tests and compilation**

Run: `python -m pytest tests/test_ui_state.py tests/test_ui_errors.py -v`

Expected: 6 tests PASS.

Run: `python -m compileall .`

Expected: all project Python files compile successfully.

- [ ] **Step 6: Record the checkpoint**

If Git metadata is available:

```bash
git add app.py components/result.py components/errors.py tests/test_ui_state.py
git commit -m "feat: add cinematic generation and result flow"
```

Otherwise, note that the checkpoint is complete without a commit.

---

### Task 4: Verify the live experience and document the redesign

**Files:**
- Modify: `README.md`
- Modify as defects require: `app.py`, `components/*.py`, `styles/main.css`

**Interfaces:**
- Consumes: the completed Streamlit application.
- Produces: verified desktop/mobile behavior and accurate project documentation.

- [ ] **Step 1: Update README documentation**

Add a concise “Experience” section describing the landing, real-operation loading, result, download, and create-another stages. Retain the existing install and `streamlit run app.py` commands. State that no new runtime dependency was introduced and that the Pillow-exported card design remains unchanged.

- [ ] **Step 2: Run the complete local verification suite**

Run:

```bash
python -m pytest tests -v
python -m compileall .
```

Expected: all tests pass and compilation exits with status 0.

- [ ] **Step 3: Start Streamlit and perform a health check**

Run: `python -m streamlit run app.py --server.headless true --server.port 8501`

Expected: the process reports a local URL and stays running without an import or startup exception. Request `http://localhost:8501/_stcore/health` and expect HTTP 200 / `ok`.

- [ ] **Step 4: Inspect the landing page at desktop width**

Using the available in-app browser workflow, open `http://localhost:8501` at approximately 1440px width. Verify the header, hero, three color marks, form, trust note, three feature cards, and footer render; confirm there is no default Streamlit-dashboard appearance, clipped content, raw HTML, or console-visible app exception.

- [ ] **Step 5: Inspect mobile and reduced-motion behavior**

At approximately 390px width, verify no horizontal scrolling, appropriately scaled hero text, stacked feature cards, full-width input/button, and sufficient side margins. Emulate or inspect `prefers-reduced-motion: reduce` and confirm nonessential entrance and hover transforms are disabled.

- [ ] **Step 6: Verify empty and invalid input flows**

Submit whitespace and confirm Letterboxd is not called, the starring-role error appears, and `Try Again` returns to landing. Submit a clearly invalid username and confirm the safe profile error appears without raw library details or a traceback.

- [ ] **Step 7: Verify valid generation when external access permits**

Submit the README's public example username `nmcassa`. Confirm the status advances through real fetch, analysis, and render steps; the result shows the unchanged full PNG, real statistics, a `Download Story` action with `image/png`, and a working `Create Another` reset. Download the file and verify its PNG signature and 1080x1920 dimensions.

If Letterboxd or network access is unavailable, record this exact check as externally blocked and verify the result component with a locally constructed `WrappedStats` and `render_to_bytes` instead; do not claim live scraping succeeded.

- [ ] **Step 8: Fix only verified UI defects and rerun affected checks**

For each defect, record the failing width/action, make the smallest scoped correction in the owning component or stylesheet, then repeat the exact failing check plus `python -m pytest tests -v` and `python -m compileall .`.

- [ ] **Step 9: Record the final checkpoint**

If Git metadata is available:

```bash
git add README.md app.py components styles .streamlit tests spoileralert/ui_state.py
git commit -m "docs: verify cinematic wrapped redesign"
```

Otherwise, provide the user with the files changed, test evidence, external verification limitations, run instructions, preserved functionality, new dependency count, and Streamlit limitations without claiming a commit.
