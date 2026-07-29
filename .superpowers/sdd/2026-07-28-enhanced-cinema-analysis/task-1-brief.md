# Task 1: Rich Diary and Typed Domain Models

## Global constraints

Preserve the current SpoilerAlert website, full-current-year behavior, safe errors, and existing public imports. Count duplicate diary viewings and rewatches separately. Keep Streamlit Cloud compatibility. Do not alter unrelated UI/rendering. No Git metadata exists, so skip commits.

## Files

- Create `spoileralert/models.py`
- Modify `spoileralert/data.py`
- Modify `spoileralert/analysis.py`
- Create `tests/test_models.py`
- Extend `tests/test_data.py`

## Required interfaces

Create frozen dataclasses exactly matching Task 1 in `docs/superpowers/plans/2026-07-28-enhanced-cinema-analysis.md`: `DiaryEntry`, `MovieMetadata`, `EnrichedViewing`, `GenreScore`, `MoodScore`, `DirectorStat`, `TimelinePoint`, `CinemaPersonality`, `MovieDNA`, `EnhancedWrappedStats`, and `RenderedCard`. Use tuples for immutable collections and `None` for unavailable values. Avoid runtime import cycles with `WrappedStats`; moving/re-exporting it is allowed only if all current imports remain valid.

Produce:

- `normalize_year_diary(year_diary: dict, current_year: int) -> list[DiaryEntry]`
- `get_rich_diary_entries(username: str, year: int | None = None) -> list[DiaryEntry]`
- Preserve `get_diary_entries(username: str) -> list[dict]` as an adapter returning only `title` and `month`.

Rich normalization must preserve viewing ID, title, release year, slug, exact watch date, rating, and rewatch flag; keep duplicate viewings; ignore malformed rows and wrong-year dates; and preserve existing network/profile/empty-diary exception behavior. The compatibility adapter must keep the existing 81-entry regression and downstream overview behavior.

## TDD

First write tests proving two Arrival viewings remain distinct and retain dates/ratings/rewatch data, malformed rows are ignored, wrong-year rows are excluded, and the compatibility adapter returns title/month dictionaries. Run the focused tests and capture the expected RED failure before production edits.

Then implement the minimum contracts and run:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_models tests.test_data -v
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q spoileralert tests
```

## Report

Write `.superpowers/sdd/2026-07-28-enhanced-cinema-analysis/task-1-report.md` with files, RED/GREEN commands and output, total tests, compatibility confirmation, self-review, and concerns. Return only status, no commits, one-line tests, concerns, and report path.
