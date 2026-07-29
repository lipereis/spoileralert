# Task 4 Report — Movie DNA, Director Universe, Timeline, and Orchestration

## Files changed

- Modified `spoileralert/analysis.py`.
- Modified `spoileralert/models.py` with the minimal frozen timeline-insight
  extension requested by review.
- Created `tests/test_movie_dna.py`.
- Created `tests/test_directors.py`.
- Created `tests/test_timeline.py`.
- Created `tests/test_enhanced_analysis.py`.
- Created this report.
- No UI, renderer, metadata, personality, or mood file was changed.

## RED evidence

Initial RED command:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_movie_dna tests.test_directors tests.test_timeline tests.test_enhanced_analysis -v
```

Result: exit 1. All four modules failed to import for the intended reason:
`calculate_movie_dna`/`DNA_TRAIT_PRIORITY`, `calculate_director_universe`,
`calculate_viewing_timeline`, and `compute_enhanced_stats` did not yet exist.

Review-fix RED command:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_enhanced_analysis -v
```

Result: exit 1; four tests errored because the requested insight fields did
not exist, and the empty-overview regression failed because `compute_stats`
returned `Janeiro` for an empty diary.

## Implementation decisions

- Movie DNA deduplicates metadata by stable movie identity: valid TMDB id first,
  then normalized slug plus release year, then normalized title plus release year.
  Rewatches therefore do not inflate metadata richness or coverage.
- Genre percentages use all distinct enriched films as the denominator. Genre,
  decade, language, and country rankings are capped at five and break ties by
  case-insensitive name.
- Diversity uses the approved 30/25/20/15/10 component weights, bounded
  sample-aware targets, and renormalizes over present components only. A score
  is `None` when no component is observed, always 0–100 otherwise, and fewer
  than five distinct enriched films sets the DNA limited-sample flag.
- `DNA_TRAIT_PRIORITY` declares deterministic dominant-trait precedence.
  Traits are selected only from measurable metadata, with `Balanced mix` as
  the observed-data fallback and `Insufficient metadata` when no component is
  available.
- Director aggregation credits every director once per diary viewing,
  including rewatches and co-directed films. Displayed titles are deduplicated;
  runtime and release-year averages use available values only. Percentages use
  enriched diary viewings so numerator and denominator retain the same viewing
  semantics. Sorting follows count, known runtime, and case-insensitive name.
- Timeline aggregation accepts diary records directly and enriched records when
  runtime is available. Monthly output is the default and inserts only internal
  gaps; explicit weekly output uses ISO-week years and handles year boundaries.
  Missing runtime, rating, and rewatch data remain `None`. Fixed English month
  abbreviations avoid locale-dependent output.
- `EnhancedWrappedStats` now exposes four typed timeline insights:
  `busiest_period`, `least_active_period`,
  `average_films_per_active_period`, and `first_to_last_change`. Extrema ties
  resolve to the earliest chronological period. Least-active selection and the
  average exclude inserted zero gaps. Change is documented and calculated as
  last represented period count minus first represented period count. All four
  fields are `None` for empty data; a single period has zero change.
- Enhanced orchestration projects rich entries to the legacy overview format,
  calls `compute_stats` exactly once, composes all existing analyzers, preserves
  every diary entry in the timeline, counts distinct enriched films, and derives
  active days plus the longest exact-date streak (including cross-month runs).
- Empty legacy overview aggregation now uses the honest peak label
  `Unavailable`, retains a peak count of zero, and leaves all twelve monthly
  counts at zero; non-empty compatibility behavior is unchanged.

## Independent spec audit

- Confirmed distinct-film Movie DNA and distinct-viewing director/timeline
  denominators are intentionally different and tested.
- Confirmed multi-genre totals may exceed 100%, while each individual
  percentage remains bounded.
- Confirmed missing metadata never creates zero-valued runtime, rating,
  rewatch, country/language counts, diversity, or streak claims.
- Confirmed deterministic tie-breaks for DNA traits, ranked metadata,
  directors, months, and ISO weeks.
- Confirmed empty, single-entry, rewatch, co-director, internal-gap,
  cross-month streak, and ISO year-boundary cases are covered.
- Confirmed the frozen enhanced record exposes all required timeline insights
  without adding a second timeline result type.
- Audit found one locale-determinism risk in `calendar.month_abbr`; it was
  replaced with a fixed abbreviation tuple and the focused/full suites were
  rerun.

## GREEN and final verification

```powershell
.venv\Scripts\python.exe -m unittest tests.test_movie_dna tests.test_directors tests.test_timeline tests.test_enhanced_analysis -v
```

Result: exit 0; 18 tests ran, all passed.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Result: exit 0; 95 tests ran, all passed.

```powershell
.venv\Scripts\python.exe -m compileall -q spoileralert tests app.py components
.venv\Scripts\python.exe -m compileall -q .
```

Result: both commands exited 0 with no compiler output.

## Caveats

- The full suite emits existing Streamlit `missing ScriptRunContext` warnings
  in bare unittest mode; they do not cause failures.
- The tests use deterministic local fixtures and make no Letterboxd or TMDB
  requests.
- The workspace has no Git metadata, so no commit was created.
