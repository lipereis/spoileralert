# Task 2: Optional TMDB Enrichment and Cloud Secret Setup

## Constraints

Use the approved Task 1 models. Enrichment is optional and must never prevent six-card generation later. Do not log/store the real key. Deduplicate metadata requests while preserving all diary viewings. Use explicit timeouts, deterministic title/year confidence, and no silent ambiguous match. No Git commits.

## Files

- Create `spoileralert/metadata.py`
- Create `tests/test_metadata.py`
- Create `.env.example`
- Create `.streamlit/secrets.toml.example`
- Modify `.gitignore`
- Modify `requirements.txt` only to add an explicit lightweight HTTP dependency if needed

## Interfaces

- `get_tmdb_api_key(secrets: Mapping[str, object] | None = None, environ: Mapping[str, str] | None = None) -> str | None`
- `normalize_title(value: str) -> str`
- `match_confidence(entry: DiaryEntry, candidate: Mapping[str, object]) -> float`
- `lookup_movie_metadata(title: str, release_year: int | None, api_key: str, *, session=None) -> MovieMetadata | None`
- `enrich_diary_entries(entries: Sequence[DiaryEntry], api_key: str | None, *, lookup=lookup_movie_metadata) -> list[EnrichedViewing]`

Matching accepts only confidence >=0.85. Exact normalized title is required; release year improves confidence and incompatible years reject the match. Search, detail, credits, and keyword payloads must be validated. Use timeout `(3.05, 10.0)`. Validate poster paths before composing an `https://image.tmdb.org/` URL. Handle missing key, 401/403, 429, timeout, network failure, malformed JSON, missing results, and ambiguous candidates by returning unenriched viewings or a typed recoverable metadata result without exposing raw payloads.

Deduplicate by `(normalize_title(title), release_year)`, call lookup once per unique key, and join the same immutable metadata back to every viewing. The pure domain module must not import Streamlit. A bounded cached wrapper belongs at the later application boundary with `ttl=86400`, `max_entries=2048`; do not cache the API key in displayed/logged material.

## TDD

Write tests first for normalization, exact/year-compatible matching, low-confidence rejection, missing key, request timeout/rate limit/malformed response, detail normalization, deduplication, and duplicate viewing preservation. Capture RED before production code.

Templates:

```text
.env.example: TMDB_API_KEY=
.streamlit/secrets.toml.example: TMDB_API_KEY = "replace-in-streamlit-cloud"
```

`.gitignore` must ignore `.env` and `.streamlit/secrets.toml` while retaining `.streamlit/config.toml` and the secrets example.

Run:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_metadata -v
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q spoileralert tests
```

Write report to `.superpowers/sdd/2026-07-28-enhanced-cinema-analysis/task-2-report.md` with RED/GREEN evidence, files, test totals, security review, and concerns. Return short status contract.
