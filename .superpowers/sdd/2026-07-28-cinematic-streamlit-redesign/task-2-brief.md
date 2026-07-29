# Task 2: Build the cinematic design system and landing components

## Context and constraints

Build only the reusable landing/design-system layer. Task 1 already provides `components/errors.py` and `cinephile_wrapped/ui_state.py`; do not change them. Keep Streamlit Cloud compatibility, no new runtime dependency, English-only copy, no changes to data/analysis/render, no user-specific cache, and no remote font loading. This workspace has no Git metadata, so skip commits.

## Files

- Create `.streamlit/config.toml`
- Create `styles/main.css`
- Create `components/layout.py`
- Create `components/generator.py`

## Required interfaces

- `load_styles() -> None`
- `render_header() -> None`
- `render_hero() -> None`
- `render_features() -> None`
- `render_footer() -> None`
- `render_generator_form() -> str | None`
- `render_loading_shell()` returning the status and progress handles used by Task 3

`load_styles` must resolve `styles/main.css` from the repository root using `Path`, read UTF-8, and inject it once. Static layout HTML may contain only fixed application copy.

Header: Cinephile Wrapped wordmark and `Your year in cinema` label. Hero copy exactly: `YOUR YEAR IN CINEMA`, `Discover the story behind your movie taste.`, and `Turn your Letterboxd diary into a personal, cinematic and shareable visual experience.` Include three fixed green/orange/blue decorative marks.

Features must use numbers `01`, `02`, `03`; titles `Movie DNA`, `Cinema Personality`, `Story-Ready Design`; and exact descriptions from the design spec. Footer must contain `Built for people who see every movie as part of a bigger story.` and `Not affiliated with Letterboxd.`

The native form uses `st.form("generator_form")`, visible `Letterboxd username` label, placeholder `e.g. nmcassa`, autocomplete username, native submit button `Generate My Wrapped`, public-profile explanation, and trust note `Only public Letterboxd profile information is analyzed. Your data is not permanently stored.` It returns the entered string only on submit.

Loading shell creates a centered presentation, `st.status("Opening your Letterboxd diary…", expanded=True)`, and `st.progress(0, text="Preparing the analysis")`, returning both handles.

Theme values: base dark, primary `#00e054`, background `#0b0d0f`, secondary background `#171b20`, text `#f5f7f8`, sans serif; disable usage statistics.

## CSS requirements

Define variables for the approved background/surface/text/border and Letterboxd colors. Maximum content width 1180px. Static radial green plus blue/orange atmosphere; no moving background. Use Poppins preference with system fallback and no remote requests; local `@font-face` only if browser resolution is demonstrably reliable. Provide editorial `clamp()` headings, negative heading tracking, generous spacing, controlled borders/shadows, 16–28px radii, 54px minimum input/buttons, visible focus ring, subtle green-gradient primary action hover/active feedback, equal-height feature cards, and restrained entrance/hover animation.

Cover application selectors including `.site-header`, `.brand-lockup`, `.film-marks`, `.hero`, `.hero-title`, `.hero-copy`, `.generator-panel`, `.features-grid`, `.feature-card`, `.error-panel`, `.result-header`, `.story-preview`, `.stats-grid`, `.stat-card`, `.site-footer`, plus stable native widget selectors. Do not use generated Emotion classes.

Add breakpoints at 1024px, 768px, and 480px. At 390px there must be no horizontal overflow; stack layouts, reduce padding/type, keep margins, and use full-width controls. End with `@media (prefers-reduced-motion: reduce)` that reduces animation/transition near zero, disables smooth scrolling, and removes nonessential transforms.

## Verification and report

Compile components with `.venv\Scripts\python.exe -m compileall components`. Confirm the stylesheet and three Poppins assets exist with `Test-Path`. Add focused dependency-free checks if useful, but do not add pytest or another package. Self-review exact copy, selectors, responsive requirements, safe HTML, and scope.

Write full report to `.superpowers/sdd/2026-07-28-cinematic-streamlit-redesign/task-2-report.md` with files, commands/output, self-review, and concerns. Return only the short status contract.
