# Task 5 Report — Six Pillow Story Cards

## Files changed

- Created `spoileralert/card_renderers.py`.
- Modified `spoileralert/render.py` only to re-export `render_story_cards`; the
  existing `render_wrapped_card` and `render_to_bytes` implementations remain
  unchanged.
- Created `tests/test_card_renderers.py`.
- Created this report.
- No UI, state, metadata, analysis, or dependency file was changed.
- No Git commit was made; this workspace has no Git metadata.

## RED evidence

Initial RED command:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_card_renderers -v
```

Result: exit 1. The test module failed to import for the intended reason:
`ModuleNotFoundError: No module named 'spoileralert.card_renderers'`.

The first post-implementation run exercised real rendering and exposed a
multiline measurement defect: three tests errored with Pillow's
`ValueError: can't measure length of multiline text`. The shared width helper
was corrected to measure the widest individual line, then the same focused
command was rerun.

Review-fix RED cycle 1 added a pure-copy regression for unlike denominators.
The focused module exited 1 because `enrichment_fact_copy` did not exist.
After implementation, all 8 focused tests passed.

Review-fix RED cycle 2 added a pure-copy regression for missing optional DNA
counts. The focused module exited 1 because `dna_availability_copy` did not
exist. After implementation, all 9 focused tests passed.

## Implementation decisions

- `render_story_cards(stats)` uses one fixed registry and always returns the
  exact order `overview`, `personality`, `movie-dna`, `moods`, `directors`,
  `timeline` as an immutable tuple of `RenderedCard` values.
- Stable filenames combine the product, a normalized bounded username, and
  the card slug, for example `spoileralert-cinefan-overview.png`. Empty or
  non-ASCII-only handles safely fall back to `user`.
- PNG serialization explicitly converts to RGB and uses fixed Pillow PNG
  settings. No clock, randomness, set iteration, temporary file, remote
  request, or mutable cache participates in rendering.
- Shared local-Poppins helpers measure actual glyph widths, fit fonts,
  ellipsize single lines, wrap paragraphs, and draw text through clipped
  overlays. Bars, shared headers/footers, metrics, and fallback panels own
  fixed boxes.
- Overview preserves the existing headline statistics and adds a personality
  preview. Its rewatch-inclusive total is explicitly labelled `DIARY VIEWINGS`;
  distinct metadata matches are displayed as a separate fact with no ratio.
  Movie DNA contains five horizontal strands (genres, decades, languages,
  countries, and a metadata-basis fact row). The basis row separately states
  distinct films with metadata and diary viewings, without an invalid coverage
  percentage. Mood shows up to three
  editorial bars. Director placement uses one fixed node map; one director
  receives an explicit ranked-list fallback instead of a fabricated
  constellation. Timeline label density is selected from measured label
  widths and the busiest period is highlighted.
- Empty or unsupported metadata still produces every card. Visible copy says
  unavailable/limited and never turns absent diversity, mood, director,
  runtime, streak, or timeline values into invented facts.
- `dna_availability_copy` preserves `None` country/language counts as explicit
  `countries unavailable` / `languages unavailable` copy regardless of the
  limited-sample flag. It never uses truthiness to coerce missing values to
  observed zeroes.

## Tests added

The focused module verifies:

- exact six-card order and unique stable filenames;
- PNG signature and decoded PNG format;
- exact `(1080, 1920)` dimensions and `RGB` mode;
- identical records and byte payloads for identical input;
- zero-metadata and fully empty optional sections;
- long accented Unicode labels across every composition;
- clipped text drawing outside-pixel preservation;
- measured font fitting and ellipsis width;
- legacy `render_wrapped_card` and `render_to_bytes` behavior;
- separate copy semantics for distinct metadata-matched films and diary
  viewings, with no ratio or percentage across those unlike bases;
- explicit unavailable copy for `None` country/language counts in a
  non-limited DNA sample;
- fixed ranked director coordinates for every visible count from one through
  eight, deterministic green/blue/orange accent cycling, a centered
  single-director profile, and selection of exactly the first eight ranked
  directors when more are available.

## GREEN and verification evidence

Focused renderer suite:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_card_renderers -v
```

Result: exit 0; 11 tests ran, all passed.

Legacy result/import regression:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_result_component tests.test_render_imports -v
```

Result: exit 0; 8 tests ran, all passed.

Full discovery:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Result: exit 0; 132 tests ran, all passed in the final integrated workspace.

Full compilation:

```powershell
.venv\Scripts\python.exe -m compileall .
.venv\Scripts\python.exe -m compileall -q .
```

Result: both commands exited 0. The quiet rerun produced no compiler output.

Deterministic fixture smoke output:

```text
count=6
overview|spoileralert-cinefan-overview.png|89415|656b184173e52a9a|RGB|(1080, 1920)
personality|spoileralert-cinefan-personality.png|86875|6196c08b1c31e488|RGB|(1080, 1920)
movie-dna|spoileralert-cinefan-movie-dna.png|98900|f15a009e87a7e081|RGB|(1080, 1920)
moods|spoileralert-cinefan-moods.png|73146|b63750dc9d5b0bfe|RGB|(1080, 1920)
directors|spoileralert-cinefan-directors.png|83525|adb63d64418f02da|RGB|(1080, 1920)
timeline|spoileralert-cinefan-timeline.png|62990|41ef7a834ee1a8f8|RGB|(1080, 1920)
```

The hash column is the first 16 hexadecimal characters of each SHA-256.

## Final director-layout review fix

The review identified that the initial fixed map exposed only five nodes,
assigned most secondary nodes blue, and used a metric/list fallback rather
than the approved centered single-director profile.

RED command:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_card_renderers -v
```

Result: exit 1. The focused module could not import the new required pure
layout helpers `director_constellation_layout` and `directors_for_card`.

Implementation:

- Declared eight fixed ranked coordinates, each bounded inside the story-card
  constellation region.
- Added a pure 1–8 layout helper that cycles green, blue, and orange by rank
  and clamps larger inputs to eight.
- Added a pure ranked selection helper that retains ranks one through eight.
- Updated the constellation to draw and label all selected nodes and connect
  every secondary node to the lead.
- Replaced the one-director list fallback with a large centered highlighted
  profile using the rank-one fixed coordinate.

The first three full-discovery attempts overlapped unrelated shared-workspace
integration edits and converged from seven failures, to two, to one missing
`MOOD_CATEGORIES` import. No unrelated files were changed here. After the
other integration edits settled, the final discovery command ran 132 tests
and passed with exit 0. Quiet full compilation also exited 0.

## Caveat

- The full suite emits the existing Streamlit `missing ScriptRunContext`
  warnings while tests intentionally import/run the app in bare unittest mode.
  They do not cause failures and are unrelated to the Pillow renderer.
