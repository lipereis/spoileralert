# SpoilerAlert Enhanced Cinema Analysis Design

## Objective

Extend the existing SpoilerAlert Streamlit application with five deterministic, explainable features: Cinema Personality, Movie DNA, Mood Analysis, Director Universe, and Viewing Timeline. Preserve the current landing page, username flow, loading experience, result styling, complete current-year diary analysis, and Create Another behavior.

Every public Letterboxd user submitted through the website is analyzed independently. Each successful result produces six 1080×1920 PNG cards: the existing overview plus five new insight cards. Users may download cards individually or download one in-memory ZIP containing all six PNG files.

## Scope and Delivery Sequence

The implementation is divided into four sequential areas within one coordinated feature:

1. Rich current-year diary ingestion and optional TMDB enrichment.
2. Deterministic personality, DNA, mood, director, and timeline analysis.
3. Six consistent Pillow story-card renderers.
4. Streamlit card gallery, session state, individual downloads, and ZIP download.

The app remains Python and Streamlit based, uses pandas for aggregation and Pillow for export, introduces no frontend framework or headless browser, and remains compatible with Streamlit Community Cloud.

## Existing Behavior Preserved

- Public Letterboxd username form and safe username normalization.
- Complete current-calendar-year diary retrieval for every submitted profile.
- Separate counting of every diary viewing, including rewatches.
- Safe user-facing error mapping and server-side diagnostics.
- Four-stage session flow: landing, generating, result, error.
- Existing overview statistics and visual identity.
- 1080×1920 Pillow output and PNG download behavior.
- Per-session storage that prevents ordinary reruns from repeating generation.

## Architecture

Existing modules retain their current responsibilities wherever practical. Focused modules are added rather than creating one large analysis or renderer file:

- `spoileralert/models.py`: typed diary, metadata, analysis, personality, timeline, and rendered-card models.
- `spoileralert/data.py`: complete current-year Letterboxd diary retrieval and normalization.
- `spoileralert/metadata.py`: optional TMDB client, matching, normalization, validation, timeouts, and cached lookup boundary.
- `spoileralert/personality.py`: deterministic archetype feature extraction, scoring, evidence, and tie-breaking.
- `spoileralert/moods.py`: transparent genre and keyword mood mappings, normalization, and wording templates.
- `spoileralert/analysis.py`: existing overview aggregation plus Movie DNA, directors, timeline, and enhanced-analysis orchestration.
- `spoileralert/render.py`: existing overview entry points retained; shared Pillow helpers and card dispatch.
- Focused card-rendering modules may be introduced if `render.py` would otherwise become difficult to review.
- `components/result.py`: existing result view extended with the six-card gallery and download controls.
- `spoileralert/ui_state.py`: card collection and selected-card state added without breaking existing keys.

## Data Model

Each diary viewing remains distinct and contains available observed fields:

- Title
- Release year
- Exact watch date
- Letterboxd film identifier or slug
- Rating
- Rewatch flag

Optional normalized metadata contains:

- Genres
- Director names
- Runtime minutes
- Original language
- Production countries
- Keywords
- Overview
- Poster URL
- TMDB identifier and match confidence

Typed dataclasses represent `DiaryEntry`, `MovieMetadata`, `GenreScore`, `MoodScore`, `DirectorStat`, `TimelinePoint`, `CinemaPersonality`, `MovieDNA`, `EnhancedWrappedStats`, and `RenderedCard`.

The existing `WrappedStats` interface is extended or embedded rather than duplicated. Existing overview consumers remain valid during the transition.

## Optional TMDB Enrichment

TMDB enrichment is optional at runtime but will be configured for the deployed website through Streamlit Community Cloud Secrets.

The code reads `TMDB_API_KEY` from `st.secrets` at the application boundary or from the process environment. The repository contains only:

- `.env.example` with an empty `TMDB_API_KEY` value.
- `.streamlit/secrets.toml.example` with a placeholder.
- `.gitignore` rules protecting `.env` and `.streamlit/secrets.toml` while retaining `.streamlit/config.toml`.
- README deployment instructions for adding `TMDB_API_KEY` through Community Cloud Secrets.

The real key is never committed, logged, rendered, or requested through the website.

Metadata lookup deduplicates films by normalized title and release year before requests. Matching requires compatible normalized titles and, when available, a compatible release year. Low-confidence or ambiguous matches remain unenriched. Requests use explicit connect/read timeouts and handle authorization failures, rate limits, network failures, malformed responses, and missing fields.

Normalized successful lookups are cached by title and release year with bounded Streamlit caching. User-specific analysis objects, rendered cards, mutable session state, errors, and secrets are not globally cached.

When TMDB is absent or unavailable, the core overview and timeline remain functional. Metadata-dependent cards remain present and display honest limited-data or unavailable-data explanations.

## Cinema Personality

The system provides ten playful cinema archetypes:

1. The Explorer
2. The Auteur Hunter
3. The Comfort Watcher
4. The Midnight Critic
5. The Time Traveler
6. The Festival Drifter
7. The Genre Devotee, with a deterministic genre-specific visible title when supported
8. The Blockbuster Navigator
9. The Emotional Archaeologist
10. The Chaos Curator

Normalized features include genre, country, language, and decade diversity; director concentration; dominant genre share; international and older-film shares; recent-release share; dark and emotional genre shares; rewatch share; mainstream signals when available; and average runtime.

Each archetype receives a documented numeric score. Unavailable feature contributions are omitted rather than treated as zero. The highest score wins; ties use a fixed archetype priority declared as a constant. Evidence contains only available observed or calculated signals and never exposes raw formulas.

With no reliable personality signal, the card explains that the sample is insufficient. With one film or fewer than five enriched films, scoring uses safe denominators and visibly labels the result as limited-sample inference.

## Movie DNA

Movie DNA includes:

- Top five genres
- Most-watched decade and represented decade count
- Country and language counts when available
- Director concentration
- Diversity score from 0 to 100
- One deterministic dominant trait

Genre percentages use `films containing the genre / enriched films × 100`. A film may contribute to multiple genres, so percentages may total more than 100%; this is documented in code and UI help text.

Release years map into conventional decade labels. Invalid and missing years are excluded.

The diversity score uses these nominal weights:

- Genres: 30%
- Decades: 25%
- Countries: 20%
- Languages: 15%
- Directors: 10%

Each component is capped and normalized to 0–100 using documented small-sample thresholds. Missing components are removed and the available weights are renormalized. A small diary is not automatically penalized. Fewer than five enriched films produces a visible limited-sample note.

Dominant traits are selected by fixed priority from measurable characteristics such as genre-fluid, director-driven, internationally curious, historically diverse, contemporary focused, emotionally intense, genre-centered, mainstream leaning, or independent leaning.

## Mood Analysis

Mood Analysis describes the emotional profile of the selected movies, never the user's real emotional state.

Categories are Melancholic, Hopeful, Tense, Comforting, Chaotic, Romantic, Dark, Playful, Reflective, and Adventurous.

Scores come from transparent constants:

1. Genre-to-mood weights.
2. Optional keyword-to-mood weights.
3. Conservative overview phrase matches only when explicitly defined.

No AI API is required. Scores are summed, normalized, and displayed as whole percentages. The top three moods and a deterministic sentence template form the visible result. With no reliable mood signal, the card states that metadata was insufficient.

## Director Universe

Directors aggregate across diary viewings. Multiple directors each receive credit for a film. Each director record includes film count, available total runtime, percentage of enriched films, viewed titles, and average available release year.

Ordering is deterministic:

1. Film count descending
2. Available total runtime descending
3. Name alphabetically

The top five appear in the website and card summary. The Pillow constellation supports one to eight directors using a fixed ranked placement map. Node size reflects film count; color cycles through the established green, blue, and orange accents. One director falls back to a centered highlighted profile. Labels are wrapped or shortened safely, and runtime is omitted when unavailable.

## Viewing Timeline

The timeline uses diary watch dates, not film release dates. Monthly aggregation is the default for the complete current year. Internal empty months between the first and last represented month may appear as zero; months outside the represented range are not inserted.

Each period contains film count plus available runtime, average rating, and rewatch count. Insights include busiest period, least active represented period, average films per active period, change from first to last represented period, total active days, and longest exact-date streak.

Monthly labels are all shown for six periods or fewer and alternated for seven to twelve. Long month labels use consistent abbreviations. Weekly aggregation remains an isolated supported function and fallback for genuinely short date ranges, with deterministic ISO-week labels and year-boundary handling.

## Six PNG Cards

All cards are 1080×1920 RGB PNGs using the current charcoal, green, orange, blue, and Poppins design system:

1. Overview: current summary plus personality preview.
2. Cinema Personality: title, subtitle, description, and two or three evidence points.
3. Movie DNA: genre strands, decade, diversity score, trait, and available country/language counts.
4. Mood Analysis: leading mood, top-three percentages, editorial bars or arcs, and profile sentence.
5. Director Universe: leading director, available runtime, deterministic constellation, and secondary directors.
6. Viewing Timeline: activity baseline, bars or rounded nodes, busiest period, active days, and available streak.

Reusable Pillow helpers provide text measurement, wrapping, truncation, section framing, bars, tracks, fallback panels, and shared headers/footers. Long content is measured before drawing; no card relies on random placement.

Each card always exists. Unsupported insights use honest fallback copy rather than fabricated values.

## Streamlit Result Experience

The current landing and generation experience remains visually unchanged except for real progress stages. The result view retains its editorial header and overview statistics, then adds a mobile-friendly numbered selector for the six cards.

Session state adds:

- `wrapped_cards`: ordered immutable card metadata and PNG bytes for the active session.
- `selected_card_index`: integer constrained to the available card range.

Only one card preview is rendered at a time. Previous and Next controls update the selected index. Users can download the selected card, download cards individually, download one ZIP containing all six PNGs, or Create Another.

The ZIP is built in memory with `io.BytesIO` and `zipfile`; no temporary files are created. Filenames use the sanitized username and stable card slugs.

## Progress and Error Handling

Generation progress maps to real work:

1. Opening the complete Letterboxd diary.
2. Matching unique films with available metadata.
3. Calculating the five insight families.
4. Rendering six story cards.

Missing TMDB credentials, individual movie misses, partial metadata, and recoverable TMDB errors do not fail the Wrapped. Profile, Letterboxd transport, irrecoverable parsing, and rendering failures use the existing safe error-state pattern. Raw exceptions, external payloads, and secrets are never shown to users.

## Testing

Tests cover:

- Rich full-year diary normalization, dates, ratings, rewatches, and duplicate viewings.
- TMDB matching with title/year, deduplication, missing credentials, timeouts, rate limits, malformed responses, and low-confidence matches.
- Clearly dominant personality archetypes, deterministic ties, limited samples, empty data, one film, and missing country/director fields.
- Multi-genre percentages, decades, diversity bounds and missing-component reweighting.
- Genre, keyword, and overview mood mappings; normalization and no-signal behavior.
- Repeated/multiple/missing directors, runtime omission, deterministic ordering, and one-director fallback.
- Monthly and weekly timelines, missing dates, gaps, streaks, zero periods, and year boundaries.
- Six valid 1080×1920 Pillow images, PNG serialization, long text, and metadata fallbacks.
- Session selection, Previous/Next bounds, exact-byte downloads, ZIP filenames/content, reset, and rerun protection.
- Existing username, safe error, overview, and original-generation behavior.

Completion requires the full unittest suite, `python -m compileall .`, import smoke checks, local Streamlit health, valid and invalid profile flows, missing-key and TMDB-failure flows, six-card and ZIP validation, and browser viewport checks only when browser tooling is available.

## Deployment

Streamlit Community Cloud deployment uses the existing repository and run command. In the app's Cloud settings, the operator adds:

```toml
TMDB_API_KEY = "the-real-key"
```

The key is stored only in Community Cloud Secrets. Deployment documentation covers secret setup, missing-secret fallback behavior, dependencies, request limits, and troubleshooting. No `.env` or real `secrets.toml` file is committed.

## Known Limitations

- TMDB matching can fail for ambiguous titles, missing release years, or films absent from TMDB; these remain explicitly unenriched.
- Genre, director, language, country, keyword, overview, runtime, popularity, and poster data depend on optional enrichment completeness.
- Personality and mood labels are deterministic entertainment-oriented inferences, not psychological conclusions.
- Rewatches count as separate diary viewings in viewing totals and timeline activity, while metadata lookup is deduplicated by film identity.
- Browser-level visual verification depends on browser tooling availability; static and AppTest evidence do not substitute for pixel-level claims.
