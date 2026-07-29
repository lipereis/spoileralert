# SpoilerAlert Enhanced Cinema Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional TMDB enrichment, five deterministic cinema-taste analyses, six downloadable 1080×1920 PNG cards, and an in-memory ZIP while preserving SpoilerAlert's current website and username flow.

**Architecture:** Keep Letterboxd retrieval, enrichment, analysis, Pillow rendering, and Streamlit presentation behind focused typed interfaces. Enrich unique films once, join metadata back to distinct diary viewings, compute an immutable enhanced result, render six ordered cards, and store only the active user's result in session state.

**Tech Stack:** Python 3.13, Streamlit >=1.60.0, pandas >=2.2.0, Pillow >=10.3.0, letterboxdpy >=6.0.0, requests, TMDB REST API, unittest.

## Global Constraints

- Preserve the current SpoilerAlert landing page, username form, loading style, result styling, safe errors, and Create Another flow.
- Analyze every submitted public user's complete current-calendar-year diary, counting rewatches as separate viewings.
- Keep Python and Streamlit, pandas aggregation, Pillow PNG rendering, and Streamlit Community Cloud compatibility.
- Do not use a frontend framework, headless browser, heavy chart library, random scoring, random node placement, or fabricated metadata.
- Treat TMDB enrichment as optional; every successful Letterboxd analysis must still produce six honest cards when enrichment is missing or fails.
- Read `TMDB_API_KEY` only from Streamlit Community Cloud Secrets or the process environment; never commit or log the real key.
- Cache only bounded normalized movie metadata lookups; do not globally cache user results, rendered cards, mutable state, error states, or secrets.
- Use explicit external request timeouts and reject ambiguous or low-confidence TMDB matches.
- Keep untrusted usernames out of unsafe HTML unless escaped.
- Generate exactly six ordered RGB PNG cards, each 1080×1920, plus one in-memory ZIP containing those six files.
- The workspace has no Git metadata. Treat commit steps as intended checkpoints and skip them unless repository metadata becomes available.

---

## File Map

- Create `spoileralert/models.py`: immutable typed diary, metadata, analysis, and rendered-card contracts.
- Modify `spoileralert/data.py`: preserve rich full-year diary fields instead of reducing immediately to title/month.
- Create `spoileralert/metadata.py`: optional TMDB configuration, matching, requests, normalization, and caching boundary.
- Create `spoileralert/personality.py`: deterministic archetype scoring, evidence, and tie-breaking.
- Create `spoileralert/moods.py`: mood constants, score normalization, and sentence templates.
- Modify `spoileralert/analysis.py`: retain `WrappedStats`; add Movie DNA, director, timeline, and enhanced orchestration.
- Create `spoileralert/card_renderers.py`: shared Pillow helpers and six card compositions.
- Modify `spoileralert/render.py`: preserve compatibility entry points and expose six-card byte rendering.
- Modify `spoileralert/ui_state.py`: store enhanced stats, ordered cards, and selected index.
- Modify `components/generator.py`: real four-stage progress copy.
- Modify `components/result.py`: six-card selector, preview, downloads, ZIP, and navigation.
- Modify `app.py`: enrichment/analysis/render orchestration and safe key loading.
- Create `.env.example` and `.streamlit/secrets.toml.example`; modify `.gitignore`, `requirements.txt`, and `README.md`.
- Create focused unittest modules for each new boundary.

---

### Task 1: Rich Diary and Typed Domain Models

**Files:**
- Create: `spoileralert/models.py`
- Modify: `spoileralert/data.py`
- Modify: `spoileralert/analysis.py`
- Test: `tests/test_models.py`
- Test: `tests/test_data.py`

**Interfaces:**
- Produces `DiaryEntry`, `MovieMetadata`, `EnrichedViewing`, `GenreScore`, `MoodScore`, `DirectorStat`, `TimelinePoint`, `CinemaPersonality`, `MovieDNA`, `EnhancedWrappedStats`, and `RenderedCard` frozen dataclasses.
- Produces `get_rich_diary_entries(username: str, year: int | None = None) -> list[DiaryEntry]`.
- Preserves `get_diary_entries(username: str) -> list[dict]` as a compatibility adapter returning `title` and `month`.

- [ ] **Step 1: Write failing model and rich-diary tests**

```python
class RichDiaryTests(unittest.TestCase):
    def test_full_year_preserves_viewings_dates_ratings_and_rewatches(self):
        payload = {
            "entries": {
                "1": {"name": "Arrival", "release": 2016, "slug": "arrival", "date": "2026-01-02", "actions": {"rating": 4.5, "rewatched": False}},
                "2": {"name": "Arrival", "release": 2016, "slug": "arrival", "date": "2026-03-04", "actions": {"rating": 5.0, "rewatched": True}},
            }
        }
        entries = normalize_year_diary(payload, 2026)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].watched_on.isoformat(), "2026-01-02")
        self.assertTrue(entries[1].rewatched)
        self.assertEqual(entries[1].rating, 5.0)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `.venv\Scripts\python.exe -m unittest tests.test_models tests.test_data.RichDiaryTests -v`

Expected: import failure because the dataclasses and `normalize_year_diary` do not exist.

- [ ] **Step 3: Implement exact typed contracts**

```python
@dataclass(frozen=True)
class DiaryEntry:
    viewing_id: str
    title: str
    release_year: int | None
    slug: str | None
    watched_on: date
    rating: float | None
    rewatched: bool | None


@dataclass(frozen=True)
class MovieMetadata:
    tmdb_id: int | None
    title: str
    release_year: int | None
    genres: tuple[str, ...] = ()
    director_names: tuple[str, ...] = ()
    runtime_minutes: int | None = None
    original_language: str | None = None
    production_countries: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    overview: str | None = None
    poster_url: str | None = None
    match_confidence: float | None = None


@dataclass(frozen=True)
class EnrichedViewing:
    diary: DiaryEntry
    metadata: MovieMetadata | None


@dataclass(frozen=True)
class GenreScore:
    name: str
    count: int
    percentage: float


@dataclass(frozen=True)
class MoodScore:
    name: str
    score: float
    percentage: int


@dataclass(frozen=True)
class DirectorStat:
    name: str
    film_count: int
    total_runtime_minutes: int | None
    percentage: float
    titles: tuple[str, ...]
    average_release_year: float | None


@dataclass(frozen=True)
class TimelinePoint:
    label: str
    film_count: int
    total_runtime_minutes: int | None
    average_rating: float | None
    rewatch_count: int | None


@dataclass(frozen=True)
class CinemaPersonality:
    key: str
    title: str
    subtitle: str
    description: str
    evidence: tuple[str, ...]
    accent_color: str
    limited_sample: bool


@dataclass(frozen=True)
class MovieDNA:
    top_genres: tuple[GenreScore, ...]
    top_decades: tuple[GenreScore, ...]
    top_languages: tuple[GenreScore, ...]
    top_countries: tuple[GenreScore, ...]
    represented_decades: int
    country_count: int | None
    language_count: int | None
    diversity_score: int | None
    dominant_trait: str
    limited_sample: bool


@dataclass(frozen=True)
class EnhancedWrappedStats:
    overview: WrappedStats
    personality: CinemaPersonality
    movie_dna: MovieDNA
    moods: tuple[MoodScore, ...]
    mood_sentence: str
    directors: tuple[DirectorStat, ...]
    timeline: tuple[TimelinePoint, ...]
    active_days: int
    longest_streak_days: int | None
    enriched_film_count: int
    total_viewing_count: int


@dataclass(frozen=True)
class RenderedCard:
    slug: str
    title: str
    filename: str
    png_bytes: bytes
```

Import `WrappedStats` into `models.py` only through `TYPE_CHECKING` to avoid a runtime cycle, or move `WrappedStats` into `models.py` and re-export it from `analysis.py` so existing imports remain valid.

- [ ] **Step 4: Implement rich diary normalization and compatibility adapter**

`normalize_year_diary` must parse `entries`, keep duplicate viewings, validate current-year ISO dates, normalize optional rating/rewatch values, and ignore malformed rows. `get_rich_diary_entries` calls `fetch_user(username).get_diary_year(year)`. Existing `get_diary_entries` calls the rich function and returns:

```python
[{"title": entry.title, "month": entry.watched_on.month} for entry in rich_entries]
```

- [ ] **Step 5: Run focused and existing tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_models tests.test_data -v`

Expected: all model and data tests PASS, including the existing 81-entry regression.

- [ ] **Step 6: Record checkpoint**

If Git exists, commit `feat: preserve rich yearly diary data`; otherwise record the checkpoint without a commit.

---

### Task 2: Optional TMDB Enrichment and Cloud Secret Setup

**Files:**
- Create: `spoileralert/metadata.py`
- Create: `tests/test_metadata.py`
- Create: `.env.example`
- Create: `.streamlit/secrets.toml.example`
- Modify: `.gitignore`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes `DiaryEntry` and produces `EnrichedViewing`.
- Produces `get_tmdb_api_key() -> str | None`, `normalize_title(value: str) -> str`, `match_confidence(entry, candidate) -> float`, `lookup_movie_metadata(title, release_year, api_key) -> MovieMetadata | None`, and `enrich_diary_entries(entries, api_key) -> list[EnrichedViewing]`.

- [ ] **Step 1: Write failing enrichment tests**

```python
class MetadataTests(unittest.TestCase):
    def test_enrichment_deduplicates_same_film_but_preserves_viewings(self):
        entries = (make_entry("Arrival", 2016, "2026-01-01"), make_entry("Arrival", 2016, "2026-02-01"))
        with patch("spoileralert.metadata.lookup_movie_metadata", return_value=make_metadata()) as lookup:
            enriched = enrich_diary_entries(entries, "key")
        lookup.assert_called_once_with("Arrival", 2016, "key")
        self.assertEqual(len(enriched), 2)

    def test_missing_key_returns_unenriched_viewings(self):
        entries = (make_entry("Arrival", 2016, "2026-01-01"),)
        self.assertIsNone(enrich_diary_entries(entries, None)[0].metadata)

    def test_low_confidence_candidate_is_rejected(self):
        self.assertLess(match_confidence(make_entry("Heat", 1995), {"title": "The Heat", "release_date": "2013-01-01"}), 0.75)
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m unittest tests.test_metadata -v`

Expected: import failure because `spoileralert.metadata` does not exist.

- [ ] **Step 3: Implement configuration and matching**

Use environment access in `metadata.py`; pass Streamlit secrets into `get_tmdb_api_key` from `app.py` rather than importing Streamlit inside the domain client. Normalize Unicode, punctuation, articles, and whitespace conservatively. Confidence combines exact normalized title and release-year distance; accept only `>= 0.85`. Use TMDB search followed by movie details, credits, and keywords with `(3.05, 10.0)` connect/read timeout and validated JSON structures.

- [ ] **Step 4: Implement deduplication and bounded cache boundary**

Keep the pure client testable. Add a Streamlit-cached wrapper in the application boundary with `ttl=86400` and `max_entries=2048`, keyed only by normalized title, release year, and a non-secret configuration version. Never include or expose the API key in cache displays or logs.

- [ ] **Step 5: Add safe templates**

`.env.example` contains `TMDB_API_KEY=`. `.streamlit/secrets.toml.example` contains `TMDB_API_KEY = "replace-in-streamlit-cloud"`. `.gitignore` ignores `.env` and `.streamlit/secrets.toml` while explicitly retaining `.streamlit/config.toml` and the example.

- [ ] **Step 6: Run metadata tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_metadata -v`

Expected: deduplication, no-key, timeout, rate-limit, malformed-response, confidence, and normalization tests PASS.

- [ ] **Step 7: Record checkpoint**

If Git exists, commit `feat: add optional TMDB enrichment`; otherwise record without a commit.

---

### Task 3: Cinema Personality and Mood Analysis

**Files:**
- Create: `spoileralert/personality.py`
- Create: `spoileralert/moods.py`
- Create: `tests/test_personality.py`
- Create: `tests/test_moods.py`

**Interfaces:**
- Produces `calculate_cinema_personality(viewings: Sequence[EnrichedViewing]) -> CinemaPersonality`.
- Produces `calculate_mood_profile(viewings: Sequence[EnrichedViewing]) -> tuple[MoodScore, ...]` and `mood_profile_sentence(scores) -> str`.

- [ ] **Step 1: Write failing personality tests**

```python
class PersonalityTests(unittest.TestCase):
    def test_explorer_wins_for_broad_genres_countries_and_decades(self):
        personality = calculate_cinema_personality(explorer_fixture())
        self.assertEqual(personality.key, "explorer")
        self.assertGreaterEqual(len(personality.evidence), 2)

    def test_tie_breaking_uses_declared_priority(self):
        scores = {"explorer": 0.5, "time_traveler": 0.5}
        self.assertEqual(select_archetype(scores), "explorer")

    def test_one_unenriched_film_returns_limited_sample(self):
        personality = calculate_cinema_personality(one_unenriched_fixture())
        self.assertTrue(personality.limited_sample)
```

- [ ] **Step 2: Write failing mood tests**

```python
class MoodTests(unittest.TestCase):
    def test_horror_and_thriller_produce_dark_and_tense_scores(self):
        moods = calculate_mood_profile(viewings_with_genres("Horror", "Thriller"))
        self.assertEqual([m.name for m in moods[:2]], ["Tense", "Dark"])
        self.assertEqual(sum(m.percentage for m in moods), 100)

    def test_no_signal_returns_empty_scores(self):
        self.assertEqual(calculate_mood_profile(one_unenriched_fixture()), ())
```

- [ ] **Step 3: Verify RED**

Run: `.venv\Scripts\python.exe -m unittest tests.test_personality tests.test_moods -v`

Expected: module import failures.

- [ ] **Step 4: Implement personality feature extraction and scoring**

Declare ten archetypes and `ARCHETYPE_PRIORITY` in one module. Normalize every available feature to 0–1. Each archetype's score is a weighted sum divided by its available weight total. Genre Devotee adapts its visible title from the dominant genre. Evidence templates consume only observed counts/shares. Empty data returns an explicit limited-sample fallback personality.

- [ ] **Step 5: Implement transparent mood mappings**

Declare `GENRE_MOOD_WEIGHTS`, `KEYWORD_MOOD_WEIGHTS`, and conservative overview phrase constants. Sum weights per enriched film, normalize with largest-remainder rounding so displayed integers total 100, sort by score descending then mood name, and generate fixed templates from the top three.

- [ ] **Step 6: Run focused tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_personality tests.test_moods -v`

Expected: Explorer, Auteur Hunter, Genre Devotee, tie, limited sample, genre mapping, keyword mapping, normalization, and no-signal tests PASS.

- [ ] **Step 7: Record checkpoint**

If Git exists, commit `feat: add personality and mood analysis`; otherwise record without a commit.

---

### Task 4: Movie DNA, Director Universe, Timeline, and Enhanced Orchestration

**Files:**
- Modify: `spoileralert/analysis.py`
- Test: `tests/test_movie_dna.py`
- Test: `tests/test_directors.py`
- Test: `tests/test_timeline.py`
- Test: `tests/test_enhanced_analysis.py`

**Interfaces:**
- Produces `calculate_movie_dna(viewings) -> MovieDNA`, `calculate_director_universe(viewings) -> tuple[DirectorStat, ...]`, `calculate_viewing_timeline(entries, grouping="monthly") -> tuple[TimelinePoint, ...]`, and `compute_enhanced_stats(username, entries, enriched) -> EnhancedWrappedStats`.

- [ ] **Step 1: Write failing aggregation tests**

```python
def test_multi_genre_percentages_use_enriched_film_denominator(self):
    dna = calculate_movie_dna(two_films_genres(("Drama", "Romance"), ("Drama",)))
    self.assertEqual(dna.top_genres[0], GenreScore("Drama", 2, 100.0))
    self.assertEqual(dna.top_genres[1], GenreScore("Romance", 1, 50.0))

def test_director_order_is_count_runtime_then_name(self):
    directors = calculate_director_universe(director_fixture())
    self.assertEqual([item.name for item in directors], ["A Director", "B Director"])

def test_monthly_timeline_keeps_internal_zero_month(self):
    points = calculate_viewing_timeline(entries_on("2026-01-01", "2026-03-01"))
    self.assertEqual([p.film_count for p in points], [1, 0, 1])
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m unittest tests.test_movie_dna tests.test_directors tests.test_timeline tests.test_enhanced_analysis -v`

Expected: missing enhanced-analysis interfaces.

- [ ] **Step 3: Implement Movie DNA**

Count genres per distinct enriched film identity, decades from valid release years, and available languages/countries. Cap component richness relative to sample-size-aware targets. Compute the weighted mean using only present components and round/clamp to 0–100. Select a dominant trait with one declared priority list.

- [ ] **Step 4: Implement director aggregation**

Credit every listed director, deduplicate titles within each director, count diary viewings consistently, sum only available runtimes, calculate percentage and average available release year, then sort by `(-film_count, -(runtime or -1), name.casefold())`.

- [ ] **Step 5: Implement timeline and insights**

Group exact watch dates monthly by default and ISO weekly for short-range fallback. Compute counts, optional runtime/rating/rewatch values, active days, longest consecutive-date streak, busiest/least represented periods, average per active period, and first-to-last change. Insert only internal monthly gaps.

- [ ] **Step 6: Implement enhanced orchestration**

`compute_enhanced_stats` calls the existing overview calculation once and composes personality, DNA, moods, directors, timeline, data-coverage counts, and limited-sample flags into `EnhancedWrappedStats`.

- [ ] **Step 7: Run analysis tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_movie_dna tests.test_directors tests.test_timeline tests.test_enhanced_analysis -v`

Expected: all specified aggregation, missing-value, boundary, and orchestration tests PASS.

- [ ] **Step 8: Record checkpoint**

If Git exists, commit `feat: compute enhanced cinema insights`; otherwise record without a commit.

---

### Task 5: Six Pillow Story Cards

**Files:**
- Create: `spoileralert/card_renderers.py`
- Modify: `spoileralert/render.py`
- Test: `tests/test_card_renderers.py`

**Interfaces:**
- Preserves `render_wrapped_card(stats: WrappedStats) -> Image.Image` and `render_to_bytes(stats: WrappedStats) -> bytes`.
- Produces `render_story_cards(stats: EnhancedWrappedStats) -> tuple[RenderedCard, ...]`.

- [ ] **Step 1: Write failing six-card tests**

```python
class CardRendererTests(unittest.TestCase):
    def test_all_six_cards_are_pngs_with_story_dimensions(self):
        cards = render_story_cards(enhanced_fixture())
        self.assertEqual([c.slug for c in cards], ["overview", "personality", "movie-dna", "moods", "directors", "timeline"])
        for card in cards:
            image = Image.open(io.BytesIO(card.png_bytes))
            self.assertEqual(image.size, (1080, 1920))
            self.assertEqual(image.mode, "RGB")

    def test_missing_metadata_still_returns_six_cards(self):
        self.assertEqual(len(render_story_cards(unenriched_fixture())), 6)
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m unittest tests.test_card_renderers -v`

Expected: `render_story_cards` import failure.

- [ ] **Step 3: Implement shared drawing helpers**

Create measured `draw_wrapped_text`, `fit_font`, `draw_card_header`, `draw_card_footer`, `draw_bar`, `draw_fallback_panel`, and safe truncation helpers using existing local Poppins loading and palette constants. No helper may draw beyond its declared bounding box.

- [ ] **Step 4: Implement six deterministic compositions**

Use fixed card registry order and filenames. Overview reuses current statistics and adds personality preview. DNA uses five horizontal strands. Mood uses top-three editorial bars. Director constellation uses the approved fixed position map and a ranked-list single-director fallback. Timeline uses measured label density and highlights the busiest point. Every renderer includes limited/unavailable copy when needed.

- [ ] **Step 5: Run rendering tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_card_renderers -v`

Expected: dimensions, RGB/PNG, order, fallbacks, deterministic bytes for identical inputs, and long-label bounding tests PASS.

- [ ] **Step 6: Run original renderer regression**

Run: `.venv\Scripts\python.exe -m unittest tests.test_result_component tests.test_render_imports -v`

Expected: existing result and import behavior PASS.

- [ ] **Step 7: Record checkpoint**

If Git exists, commit `feat: render six wrapped story cards`; otherwise record without a commit.

---

### Task 6: Session State, Gallery, Individual Downloads, and ZIP

**Files:**
- Modify: `spoileralert/ui_state.py`
- Modify: `components/result.py`
- Modify: `styles/main.css`
- Test: `tests/test_ui_state.py`
- Test: `tests/test_result_gallery.py`

**Interfaces:**
- Extends `set_result(state, stats, cards)` while retaining a compatibility path for existing callers during migration.
- Produces `select_previous_card(state)`, `select_next_card(state)`, `build_cards_zip(username, cards) -> bytes`, and `render_result(stats, cards) -> bool`.

- [ ] **Step 1: Write failing state/gallery tests**

```python
def test_card_navigation_stays_in_bounds(self):
    state = card_state(index=0, count=6)
    select_previous_card(state)
    self.assertEqual(state["selected_card_index"], 0)
    for _ in range(8):
        select_next_card(state)
    self.assertEqual(state["selected_card_index"], 5)

def test_zip_contains_exactly_six_original_png_payloads(self):
    cards = card_fixture()
    payload = build_cards_zip("cinefan", cards)
    with ZipFile(io.BytesIO(payload)) as archive:
        self.assertEqual(archive.namelist(), [card.filename for card in cards])
        self.assertEqual(archive.read(cards[0].filename), cards[0].png_bytes)
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m unittest tests.test_ui_state tests.test_result_gallery -v`

Expected: missing card-state and gallery interfaces.

- [ ] **Step 3: Implement state migration**

Add `wrapped_cards=()` and `selected_card_index=0` defaults. Result transitions store immutable ordered cards and reset the index. Reset removes enhanced result data. Navigation clamps to valid bounds and is pure except for the selected index.

- [ ] **Step 4: Implement native Streamlit gallery**

Keep the existing result header and statistics. Add a numbered native selector, selected-card preview, Previous/Next buttons, selected-card download, six individual download controls, ZIP download, and Create Another. Use `width="stretch"` for current Streamlit APIs and stable keyed containers for CSS. Build the ZIP in memory without temporary files.

- [ ] **Step 5: Add responsive gallery styling**

Extend existing keyed-container CSS for selector, navigation, download list, and mobile stacking at 768px/480px. Preserve focus rings and reduced-motion behavior.

- [ ] **Step 6: Run gallery tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_ui_state tests.test_result_gallery tests.test_result_component -v`

Expected: selection bounds, preview, exact bytes, filenames, ZIP contents, reset, and existing result tests PASS.

- [ ] **Step 7: Record checkpoint**

If Git exists, commit `feat: add six-card result gallery`; otherwise record without a commit.

---

### Task 7: End-to-End Streamlit Orchestration and Graceful Fallbacks

**Files:**
- Modify: `app.py`
- Modify: `components/generator.py`
- Modify: `components/errors.py`
- Test: `tests/test_app_coordinator.py`
- Test: `tests/test_app_enhanced_flow.py`

**Interfaces:**
- Consumes all prior task interfaces and preserves the four-stage coordinator.
- Produces one complete enhanced result per submitted profile without duplicate rerun work.

- [ ] **Step 1: Write failing orchestration tests**

```python
def test_generating_runs_diary_enrichment_analysis_and_six_card_render_once(self):
    app.render_current_stage()
    app.render_current_stage()
    self.assertEqual(operation_order, ["diary", "enrich", "analyze", "render"])
    self.assertEqual(len(state["wrapped_cards"]), 6)

def test_missing_tmdb_key_still_reaches_result_with_six_cards(self):
    with patch.object(app, "get_tmdb_api_key", return_value=None):
        app.render_current_stage()
    self.assertEqual(state["stage"], "result")
    self.assertEqual(len(state["wrapped_cards"]), 6)
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m unittest tests.test_app_enhanced_flow -v`

Expected: old coordinator lacks enrichment and card collection.

- [ ] **Step 3: Implement real staged orchestration**

Generation order is `get_rich_diary_entries`, `enrich_diary_entries`, `compute_enhanced_stats`, `render_story_cards`. Progress values advance only after real operations. Recoverable metadata errors log safe summaries and continue with unenriched viewings. Letterboxd/profile and irrecoverable analysis/render errors enter the existing safe error stage.

- [ ] **Step 4: Preserve rerun protection and safe secrets**

Resolve `TMDB_API_KEY` once per generation from Streamlit Secrets with environment fallback. Never include it in state or logs. State changes to result before rerun; only the generating stage performs network or rendering work.

- [ ] **Step 5: Run coordinator tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_app_coordinator tests.test_app_enhanced_flow -v`

Expected: full operation order, no-key fallback, metadata failure fallback, safe fatal errors, no duplicate reruns, gallery result, and reset PASS.

- [ ] **Step 6: Record checkpoint**

If Git exists, commit `feat: integrate enhanced wrapped pipeline`; otherwise record without a commit.

---

### Task 8: Documentation, Deployment, and Final Verification

**Files:**
- Modify: `README.md`
- Modify as verified defects require: files from Tasks 1–7
- Test: complete `tests/` suite

**Interfaces:**
- Produces documented Community Cloud secret setup and verified end-to-end delivery.

- [ ] **Step 1: Document analysis and deployment**

README must explain the complete current-year scope, observed/calculated/inferred distinction, ten archetypes and tie-breaking, genre percentage denominator, diversity weights with missing-component renormalization, mood mapping, director ordering, timeline grouping, six filenames, ZIP behavior, optional TMDB fallback, and Community Cloud Secrets configuration:

```toml
TMDB_API_KEY = "the-real-key"
```

- [ ] **Step 2: Run complete automated verification**

Run:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q .
.venv\Scripts\python.exe -c "import app, spoileralert.analysis, spoileralert.metadata, spoileralert.personality, spoileralert.moods, spoileralert.render; print('IMPORT_OK')"
```

Expected: zero failures, compilation exit 0, and `IMPORT_OK`.

- [ ] **Step 3: Validate six cards and ZIP locally**

Construct a deterministic enhanced fixture and assert six ordered PNG signatures, every image size `(1080, 1920)`, unique stable filenames, ZIP entry count six, and byte-for-byte ZIP contents.

- [ ] **Step 4: Start Streamlit and health-check**

Run hidden on port 8501 using `.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.port 8501`. Poll `/_stcore/health` until HTTP 200/`ok`, then stop the recorded PID after verification.

- [ ] **Step 5: Verify user flows**

Use Streamlit AppTest for valid fixtures, invalid username, metadata-limited profile, missing key, TMDB timeout/rate-limit/malformed payload, six-card selection, individual download metadata, ZIP metadata, and Create Another. Attempt one real public profile and configured TMDB lookup only when credentials/network are available; report external blockers honestly.

- [ ] **Step 6: Verify responsive UI when browser tooling exists**

Inspect landing and result gallery at 1440, 1024, 768, and 390px, plus keyboard focus and reduced motion. When browser tooling is unavailable, record the limitation and do not claim pixel-level verification.

- [ ] **Step 7: Final self-review and checkpoint**

Confirm no secrets, raw external errors, temporary card files, random placement, stale recent-diary wording, or unsupported metadata claims. If Git exists, commit `docs: verify enhanced cinema analysis`; otherwise provide the complete local handoff without claiming a commit.
