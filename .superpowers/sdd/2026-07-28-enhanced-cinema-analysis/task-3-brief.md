# Task 3 implementation brief — Cinema Personality and Mood Analysis

Implement Task 3 from `docs/superpowers/plans/2026-07-28-enhanced-cinema-analysis.md` using test-driven development.

## Scope

- Create `spoileralert/personality.py`.
- Create `spoileralert/moods.py`.
- Create `tests/test_personality.py`.
- Create `tests/test_moods.py`.
- Do not change Streamlit UI or later-task files.

## Required interfaces

- `calculate_cinema_personality(viewings: Sequence[EnrichedViewing]) -> CinemaPersonality`
- `select_archetype(scores: Mapping[str, float]) -> str`
- `calculate_mood_profile(viewings: Sequence[EnrichedViewing]) -> tuple[MoodScore, ...]`
- `mood_profile_sentence(scores: Sequence[MoodScore]) -> str`

## Personality requirements

- Declare exactly ten stable archetypes plus one explicit limited-sample fallback behavior. Include at minimum Explorer, Auteur Hunter, Genre Devotee, and Time Traveler.
- Put deterministic tie-breaking in a public `ARCHETYPE_PRIORITY` constant; ties select the earliest declared key.
- Extract only genuinely observed signals from diary and optional metadata. Normalize features to 0–1.
- Each archetype score is its weighted observed-feature sum divided by the weights actually available. Missing metadata must be omitted and weights renormalized, never treated as fabricated zeros.
- Genre Devotee's visible title adapts to the observed dominant genre.
- Evidence contains only real counts/shares from the input and must never invent metadata.
- Empty or too-small/unenriched input returns an honest `limited_sample=True` personality with useful fallback copy.
- Results must be deterministic regardless of dict/set iteration order.

## Mood requirements

- Declare transparent public constants `GENRE_MOOD_WEIGHTS`, `KEYWORD_MOOD_WEIGHTS`, and conservative overview phrase mappings.
- Aggregate genre, keyword, and conservative overview phrase signals per enriched viewing. No random or opaque model behavior.
- Horror + Thriller must rank Tense and Dark first in that order for the canonical test fixture.
- If no supported signal exists, return `()` and a clear no-signal sentence.
- Normalize display percentages using deterministic largest-remainder rounding so non-empty percentages total exactly 100.
- Sort by raw score descending, then mood name, except declared mapping strength should naturally produce the expected Tense/Dark order.
- Sentence output uses fixed templates derived from the top three moods.

## Tests and verification

Start with failing tests and cover at least: Explorer, Auteur Hunter, Genre Devotee adaptive title, deterministic tie, one unenriched limited sample, genre mood mapping, keyword mapping, overview phrase conservatism, exact 100% rounding, deterministic ordering, no-signal behavior, and immutable return records.

Run:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_personality tests.test_moods -v
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q spoileralert tests
```

Write evidence to `.superpowers/sdd/2026-07-28-enhanced-cinema-analysis/task-3-report.md`, including files changed, RED evidence, implementation decisions, exact commands/results, and any caveats. There is no Git metadata, so do not commit.
