# Task 1 Report: Rich Diary and Typed Domain Models

## Files changed

- Created `spoileralert/models.py` with frozen typed contracts: `DiaryEntry`, `MovieMetadata`, `EnrichedViewing`, `GenreScore`, `MoodScore`, `DirectorStat`, `TimelinePoint`, `CinemaPersonality`, `MovieDNA`, `EnhancedWrappedStats`, and `RenderedCard`.
- Updated `spoileralert/data.py` with rich yearly-diary normalization, `get_rich_diary_entries`, and the legacy adapter projection.
- Updated `spoileralert/analysis.py` to expose the enhanced stats type without introducing a runtime `WrappedStats` import cycle.
- Created `tests/test_models.py` and extended `tests/test_data.py` with rich-diary contract tests.

## TDD evidence

### RED

Command:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_models tests.test_data.RichDiaryTests -v
```

Result: exit code 1, as expected before production edits.

- `ModuleNotFoundError: No module named 'spoileralert.models'`
- `ImportError: cannot import name 'normalize_year_diary' from 'spoileralert.data'`

### GREEN

Focused command:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_models tests.test_data -v
```

Result: exit code 0; `Ran 12 tests ... OK`.

Full command:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Result: exit code 0; `Ran 37 tests ... OK`.

Compilation command:

```powershell
.venv\Scripts\python.exe -m compileall -q spoileralert tests
```

Result: exit code 0 with no compilation output.

## Compatibility confirmation

- `get_diary_entries(username)` now obtains the complete current-year rich diary and returns only `{"title", "month"}` dictionaries.
- The existing complete-year 81-entry regression remains green; duplicate titles/viewings are not deduplicated.
- `NetworkError`, `ProfileNotFoundError`, and `EmptyDiaryError` remain on the same retrieval path.
- Existing overview consumers continue receiving the list-of-dictionaries shape.

## Self-review

- Rich normalization preserves viewing IDs, title, optional release year/slug/rating/rewatch values, and exact valid watch dates.
- Two `Arrival` viewings remain separate records with their own dates, ratings, and rewatch flag.
- Invalid rows and dates outside the requested calendar year are excluded.
- All new immutable collection fields default to tuples; unavailable scalar values are `None`.
- `models.py` uses `TYPE_CHECKING` for `WrappedStats`, avoiding a runtime import cycle while `analysis.py` preserves its existing `WrappedStats` public import.

## Concerns

No functional concerns. Full discovery emits existing Streamlit bare-mode `ScriptRunContext` warnings during app-coordinator tests, but all 37 tests pass and no new warnings/errors are attributable to this task.

## Checkpoint

No commit created because this workspace has no Git metadata, per task constraint.
