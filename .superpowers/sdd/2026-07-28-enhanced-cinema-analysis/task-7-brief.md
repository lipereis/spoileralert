# Task 7 implementation brief — End-to-End Streamlit Orchestration

Implement Task 7 from the approved plan using TDD. Modify `app.py`, `components/generator.py`, and `components/errors.py`; create/extend coordinator tests including `tests/test_app_enhanced_flow.py`. Preserve the landing page, form, loading/result styling, Create Another, safe errors, and rerun protection.

Generation order must be exactly: complete current-year `get_rich_diary_entries`, optional `enrich_diary_entries`, `compute_enhanced_stats`, `render_story_cards`, then store result/cards and rerun. Count all diary viewings including rewatches. Real progress only advances after operations.

Resolve TMDB key once per generation from Streamlit Secrets with environment fallback, never store/log/expose it. Implement the bounded Streamlit cache boundary (`ttl=86400`, `max_entries=2048`) without putting the secret in cache keys/state/logs; use a non-secret configuration version and pure client boundary. If safe cache semantics cannot avoid secret coupling, keep domain dedup and document conservative no-cache behavior rather than leak/misroute credentials.

Missing key and all recoverable TMDB failures must still reach result with exactly six honest cards. Letterboxd/profile failures and irrecoverable analysis/render failures enter existing safe error stage without raw external details. Only generating stage performs work; repeated reruns do not duplicate network/render calls.

Tests cover exact once/order, full-year rich diary, no key, metadata timeout/rate-limit/malformed fallback, safe secrets, fatal errors, six-card state, rerun idempotence, and reset. Include real AppTest where useful. Run focused coordinator/enhanced flow, full discovery, compileall, and imports. Record RED/GREEN evidence in `task-7-report.md`. No Git commit.
