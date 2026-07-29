# Task 4 implementation brief — Movie DNA, Director Universe, Timeline, Orchestration

Implement Task 4 from the approved plan with TDD. Modify only `spoileralert/analysis.py` and create `tests/test_movie_dna.py`, `tests/test_directors.py`, `tests/test_timeline.py`, `tests/test_enhanced_analysis.py` unless a minimal model correction is demonstrably required.

Required public functions: `calculate_movie_dna`, `calculate_director_universe`, `calculate_viewing_timeline`, `compute_enhanced_stats` with the plan's exact return records.

Movie DNA must use distinct enriched film identity for metadata richness (rewatches do not inflate genre/language/country diversity), multi-genre percentages use enriched distinct-film denominator, decades use valid release years, missing component weights are omitted and renormalized, diversity is deterministic 0–100, and dominant trait uses declared priority. Honest limited-sample behavior is mandatory.

Director stats credit every listed director, preserve consistent diary-viewing counts, deduplicate displayed titles, sum only available runtimes, compute percentages and average valid release year, and sort by `(-film_count, -(runtime or -1), name.casefold())`.

Timeline defaults monthly, includes internal zero months only, and provides optional runtime/rating/rewatch fields honestly. ISO-week fallback may be used for short ranges. Compute active days and longest consecutive calendar-date streak. Make all labels/order deterministic.

`compute_enhanced_stats` must call existing overview calculation once and compose personality, DNA, moods, directors, timeline, coverage, active days, streak, and total viewings. Preserve existing `WrappedStats` compatibility and every old test.

Start with failing boundary tests, including rewatch identity, multi-genre denominator, missing values, director sort ties, internal gaps, cross-month streaks, empty/single-entry data, and orchestration mocks. Run focused Task 4 tests, full discovery suite, and compileall. Record RED/GREEN evidence, changed files, exact results, and caveats in `task-4-report.md`. No Git commit because the workspace has no Git metadata.
