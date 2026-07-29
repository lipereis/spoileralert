# Task 5 implementation brief — Six Pillow Story Cards

Implement Task 5 from the approved plan using TDD. Create `spoileralert/card_renderers.py`, modify `spoileralert/render.py`, and create `tests/test_card_renderers.py`. Preserve both existing renderer entry points and their tests.

Produce exactly six ordered `RenderedCard` values: overview, personality, movie-dna, moods, directors, timeline. Every payload must be a deterministic RGB PNG exactly 1080×1920 with stable unique filenames. All six must render honestly even with zero TMDB metadata, sparse values, long labels, or empty optional sections.

Reuse the existing palette/font system where practical. Implement measured wrapping/font fitting/truncation and bounded drawing helpers. No random placement. Director constellation uses a fixed position map and a clear one-director/list fallback. Timeline label density must be measured and highlight the busiest point. Include limited/unavailable copy instead of fabricated values.

Tests must cover order, signatures, dimensions, RGB mode, stable filenames, deterministic identical bytes, missing metadata, empty/sparse sections, long Unicode labels/bounds, and legacy renderer compatibility. Run focused renderer tests, relevant old result/import tests, full discovery, and compileall. Record RED/GREEN evidence and exact results in `task-5-report.md`. No Git commit.
