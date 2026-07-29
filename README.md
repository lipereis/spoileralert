# SpoilerAlert 🎬

SpoilerAlert turns a public Letterboxd profile's complete current-calendar-year
diary into a deterministic cinema recap. Every submitted public profile is
analyzed independently, every diary viewing is counted, and rewatches remain
separate viewings. A successful run produces six shareable 1080×1920 PNG cards
and one in-memory ZIP containing those exact files.

## What the analysis means

SpoilerAlert keeps three kinds of information distinct:

- **Observed:** Letterboxd diary facts (title, watch date, rating, and rewatch
  flag) and optional TMDB facts accepted for a high-confidence movie match
  (genres, directors, runtime, language, countries, keywords, overview, and
  release year).
- **Calculated:** counts, shares, monthly activity, streaks, rankings, and the
  diversity score. These are deterministic aggregations of available facts.
- **Inferred:** Cinema Personality, Movie DNA's dominant trait, and Mood
  Analysis. These are playful, deterministic labels about the selected films,
  not psychological conclusions about the viewer.

No random scoring, random card placement, AI inference, or fabricated metadata
is used.

### Cinema Personality

The first available highest score wins. Exact ties use this declared priority:

1. The Explorer
2. The Auteur Hunter
3. The Comfort Watcher
4. The Midnight Critic
5. The Time Traveler
6. The Festival Drifter
7. The Genre Devotee (its visible title may include the observed leading genre)
8. The Blockbuster Navigator
9. The Emotional Archaeologist
10. The Chaos Curator

Each score is normalized from 0 to 1 using only feature families with enough
observations. Unavailable inputs are omitted and the remaining score weights
are renormalized. Results based on fewer than five enriched films are visibly
marked as limited-sample inference; no reliable signal returns an explicit
insufficient-sample card instead of guessing.

### Movie DNA

Genre percentages use:

```text
distinct enriched films containing the genre / all distinct enriched films × 100
```

A film may have several genres, so genre percentages do not need to total 100%.
Decade, country, language, and director diversity use observed coverage only.
The nominal diversity weights are genres 30%, decades 25%, countries 20%,
languages 15%, and directors 10%. Each present component is capped against a
sample-aware target; missing components are removed and the remaining weights
are renormalized before the final 0–100 score is rounded. Fewer than five
distinct enriched films is visibly marked as a limited sample.

### Mood Analysis

The visible categories are exactly Melancholic, Hopeful, Tense, Comforting,
Chaotic, Romantic, Dark, Playful, Reflective, and Adventurous.

Mood scores are sums of published, deterministic metadata mappings. Duplicate
genres or keywords inside one film count once. Scores sort by strength and then
name; largest-remainder rounding makes every non-empty displayed profile total
exactly 100%.

Genre mappings:

| Genre | Mood weights |
| --- | --- |
| Action | Adventurous 1.2; Chaotic 0.6 |
| Adventure | Adventurous 1.2; Hopeful 0.4 |
| Animation | Playful 0.9; Hopeful 0.5 |
| Comedy | Playful 1.2; Comforting 0.4 |
| Crime | Dark 0.8; Tense 0.8; Reflective 0.2 |
| Documentary | Reflective 1.0 |
| Drama | Reflective 0.8; Melancholic 0.6 |
| Family | Comforting 1.0; Playful 0.5 |
| Fantasy | Adventurous 0.8; Hopeful 0.5; Playful 0.3 |
| History | Reflective 0.9; Melancholic 0.3 |
| Horror | Tense 1.2; Dark 1.0; Chaotic 0.7 |
| Music | Playful 0.8; Comforting 0.5 |
| Mystery | Tense 0.8; Reflective 0.5; Dark 0.3 |
| Romance | Romantic 1.2; Hopeful 0.4; Comforting 0.3 |
| Science Fiction | Adventurous 0.8; Reflective 0.6; Chaotic 0.2 |
| Thriller | Tense 1.4; Dark 0.7; Chaotic 0.4 |
| War | Dark 0.8; Tense 0.8; Melancholic 0.5 |
| Western | Adventurous 0.7; Reflective 0.4 |

Keyword mappings:

| Keyword | Mood weights |
| --- | --- |
| adrenaline | Adventurous 1.0; Chaotic 0.3 |
| coming of age | Reflective 0.6; Hopeful 0.5 |
| dance | Playful 1.0 |
| dystopia | Dark 0.9; Tense 0.5 |
| family reunion | Comforting 1.0 |
| friendship | Comforting 1.0; Hopeful 0.5 |
| grief | Melancholic 1.0; Reflective 0.5 |
| haunted house | Dark 1.0; Tense 0.5 |
| serial killer | Tense 1.0; Dark 0.8 |
| space exploration | Adventurous 1.0; Reflective 0.4 |
| surrealism | Chaotic 0.8; Reflective 0.5 |

Conservative overview phrase mappings are limited to `falls in love` → Romantic
0.8, `haunted by the past` → Melancholic 0.6 and Reflective 0.5,
`race against time` → Tense 0.9, `struggles with grief` → Melancholic 0.8, and
`surreal journey` → Chaotic 0.7 and Reflective 0.4. The exact mappings are public constants in
`spoileralert/moods.py`. Unsupported text adds no signal, and no supported
signal produces an honest metadata-unavailable message.

### Directors and timeline

Director Universe credits every listed director for each enriched diary
viewing, including rewatches and co-directors. Its percentage denominator is
all enriched viewings. Titles are deduplicated within a director summary;
runtime and average release year use only available valid values. Ordering is
film count descending, available total runtime descending, then name
alphabetically.

Viewing Timeline uses diary watch dates—not release dates—and groups the
complete current year by month. It inserts only internal zero months between
the first and last represented month. The isolated weekly mode uses ISO weeks
and supports year boundaries. Busiest/least-active and average calculations use
represented nonzero periods; active days use unique watch dates, and the
longest streak requires consecutive calendar dates.

## Cards and downloads

Every successful run emits these ordered RGB PNG files, where `{username}` is a
lowercase, ASCII-safe version of the submitted name:

1. `spoileralert-{username}-overview.png`
2. `spoileralert-{username}-personality.png`
3. `spoileralert-{username}-movie-dna.png`
4. `spoileralert-{username}-moods.png`
5. `spoileralert-{username}-directors.png`
6. `spoileralert-{username}-timeline.png`

The gallery previews one card at a time and provides selected-card, individual,
and all-card downloads. `spoileralert-{username}-cards.zip` is built entirely
in memory, contains exactly the six files above in that order, and preserves
their original PNG bytes. Card generation creates no temporary files.

TMDB enrichment is optional. Without a key, after a timeout or rate limit, or
when a title is missing or ambiguous, the complete Letterboxd overview and
timeline still work and all six cards still exist. Metadata-dependent cards
show limited-data or unavailable-data copy rather than unsupported claims.

## When Letterboxd blocks the server

Letterboxd's anti-bot protection answers some requests with HTTP 403, most
often when they come from a shared cloud IP address such as Streamlit
Community Cloud's. This is a property of the host, not of the submitted
profile or of any account. Those responses become a dedicated `BlockedError`
and a specific error panel naming the hosting provider's address as the cause,
instead of the generic unexpected-failure copy.

Because a retry reruns the same blocked request, a block never offers a bare
retry as its only action. The error panel renders the diary-export upload
directly beneath itself and labels its secondary control **Start Over** rather
than **Try Again**, so the one path that can still succeed is available where
the failure happened.

The **Blocked by Letterboxd? Upload your diary export instead** form is that
path, and it opens expanded on the landing page rather than hidden behind a
collapsed expander. Export your data from Letterboxd's **Settings → Import &
Export → Export Your Data**, then upload the `diary.csv` file from the emailed
ZIP. Parsing is local and makes no network request, so it keeps working while
scraping is blocked, and it produces the same six cards and ZIP. A wrong file is
reported as `InvalidCsvError` and can be replaced in place, since that failure
is also upload-recoverable.

The reader requires the `Name` and `Date` columns and additionally reads
`Watched Date`, `Year`, `Letterboxd URI`, `Rating`, and `Rewatch` when present.
`Watched Date` wins over `Date` for a row that has both, because bulk-imported
rows record the import moment in `Date` rather than the viewing date. A leading
UTF-8 byte-order mark is tolerated. Only rows inside the current
calendar year are counted; rows without a title or with an unparseable date are
skipped. The display name is optional, labels the cards only, and defaults to
`you`. A file without the expected columns raises `InvalidCsvError` and is
reported as a wrong-file error rather than an empty diary.

## Stack and project layout

- **Streamlit 1.60.0+** — UI and per-session workflow
- **letterboxdpy** — public Letterboxd profile and yearly-diary retrieval
- **requests** — optional TMDB REST requests with explicit timeouts
- **pandas** — overview aggregation
- **Pillow** — deterministic 1080×1920 RGB PNG rendering

```text
app.py                     Streamlit coordinator
components/                Landing, loading, error, and result gallery UI
spoileralert/data.py       Full-year Letterboxd diary and diary.csv normalization
spoileralert/metadata.py   Optional TMDB matching and enrichment
spoileralert/analysis.py   Overview, DNA, director, and timeline analysis
spoileralert/personality.py
spoileralert/moods.py
spoileralert/card_renderers.py
spoileralert/render.py     Compatibility renderer and six-card export
spoileralert/ui_state.py   Per-session state and gallery navigation
styles/main.css            Responsive cinematic design system
assets/fonts/              Local Poppins card fonts
tests/                     Unit, integration, renderer, and AppTest coverage
```

## Run locally

Python 3.13 is the tested runtime.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

TMDB is not required. To enable enrichment for the current PowerShell process:

```powershell
$env:TMDB_API_KEY = "your-tmdb-api-key"
.venv\Scripts\python.exe -m streamlit run app.py
```

`.env.example` is a safe template only; the app reads the process environment
and does not automatically load `.env` files. Never commit `.env` or a real
`.streamlit/secrets.toml`.

## Deploy on Streamlit Community Cloud

1. Deploy the repository with `app.py` as the entrypoint.
2. In the app's **Settings → Secrets**, add:

   ```toml
   TMDB_API_KEY = "replace-with-your-tmdb-key"
   ```

3. Save the secret and reboot the app if Cloud does not restart it
   automatically.

The real key belongs only in Community Cloud Secrets (or a local process
environment). It is never requested in the web UI, stored in session state,
rendered, logged, or included in cache arguments. Successful public TMDB
metadata is cached for 24 hours by normalized title, release year, and a
non-secret configuration version, with at most 2,048 entries. Misses and
failures are never cached, so a temporary outage or rejected match is retried
on a later generation. A missing secret is a supported mode. TMDB authorization,
rate-limit, network, malformed-response, low-confidence, and ambiguous-match
failures degrade to unenriched cards instead of failing an otherwise valid
Letterboxd Wrapped.

If deployment fails, confirm the Python dependencies in `requirements.txt`,
that the Letterboxd profile is public and has a current-year diary entry, and
that the optional TMDB secret name is exactly `TMDB_API_KEY`. TMDB coverage can
still be incomplete because some titles are absent or ambiguous; that is an
expected limitation, not a reason to invent data.

A TMDB key does not affect Letterboxd availability. TMDB only enriches films
already read from a diary, so a deployment that Letterboxd is blocking with 403
responses needs the `diary.csv` upload path described above, not a key.

## Privacy and limitations

- Only public Letterboxd profile information is read; profile results and card
  bytes live in the active Streamlit session and are not permanently stored.
- Movie enrichment is deduplicated by normalized title and release year within
  a generation. Only successful public normalized movie metadata is globally
  cached (24-hour TTL, 2,048-entry bound); user results, rendered cards,
  failures, misses, and secrets are not globally cached.
- TMDB metadata completeness controls which metadata-dependent insights are
  available. Low-confidence or tied best matches are rejected.
- The app is not affiliated with Letterboxd or TMDB.
- The legacy single-card renderer intentionally retains its original
  **Cinephile Wrapped** footer for compatibility; enhanced story cards use
  SpoilerAlert branding.
