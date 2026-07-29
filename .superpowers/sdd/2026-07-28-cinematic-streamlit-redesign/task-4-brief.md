# Task 4: Verify the live experience and document SpoilerAlert

## Context and constraints

The user explicitly renamed the project/product to **SpoilerAlert**. The lowercase Python package is `spoileralert`. Preserve all approved behavior and the protected core modules. The exported PNG visual is intentionally unchanged, including its legacy Cinephile Wrapped footer; document that limitation rather than editing the renderer. No new runtime dependency, no Git metadata/commits.

## Files

- Modify `README.md`
- Modify UI/tests/CSS/app only for verified defects found during this task
- Update design/plan documentation references where they describe the current product/package name, without rewriting historical SDD reports

## Documentation

README title/product copy must say SpoilerAlert. Update project layout to `spoileralert/`. Add an Experience section describing landing, real-operation loading, result reveal, download, and Create Another. Retain exact install/run commands. State no new runtime dependency and unchanged Pillow-exported PNG design. Note public profiles only, recent diary snapshot, and the legacy exported-card footer branding caused by intentionally preserving the card visual.

Update the approved design spec and implementation plan where current-state names/paths say Cinephile Wrapped or `cinephile_wrapped`; preserve generic “Wrapped” feature terminology and historical report/ledger content.

## Verification

1. Run all dependency-free focused tests and `.venv\Scripts\python.exe -m compileall -q .`.
2. Start with `.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.port 8501` in the background, hidden on Windows, and confirm `http://localhost:8501/_stcore/health` returns HTTP 200 / `ok`.
3. Use the browser-control skill for live inspection. Desktop around 1440px: verify SpoilerAlert header, hero, film marks, form, privacy note, three features, footer, dark cinematic visual, no raw HTML, no visible exception.
4. Mobile around 390px: verify no horizontal scroll, scaled hero, stacked cards, full-width form/actions, margins, and readable layout. Inspect reduced-motion CSS behavior through browser-visible/DOM evidence where supported; otherwise verify the CSS rule statically and report the browser limitation.
5. Submit whitespace and `@`; neither may call Letterboxd. Both must show the safe starring-role error, and Try Again must reset. The existing deferred `@` normalization issue is in scope to fix now because this check exposes it; add a no-fetch regression test.
6. Submit a clearly invalid username. Confirm a safe profile/network error without raw traceback/details. External library behavior may map network errors broadly; report what is observed.
7. Attempt valid generation with `nmcassa` if network/Letterboxd access works. Confirm progress, result, English month, unchanged full PNG, real stats, Download Story MIME/filename, and Create Another. Download if browser tooling permits; verify PNG signature and 1080x1920 dimensions. If external access fails, record exact limitation and construct a local `WrappedStats` plus `render_to_bytes` to verify result bytes/dimensions without claiming live scraping.
8. Verify at 1024px and 768px at least for absence of layout breakage.
9. Stop the background Streamlit process after checks.

For any verified defect: record the failing width/action, make the smallest owning-file fix, add/update a focused test when logic changes, rerun that check plus the full focused suite and compileall.

## Report

Write `.superpowers/sdd/2026-07-28-cinematic-streamlit-redesign/task-4-report.md` with files, exact commands/output, screenshots or browser observations at each width, error/generation outcomes, download/image verification, external blockers, final test totals, self-review, and preserved functionality. Return short status contract only.
