"""A bundled demo diary so the app can present itself in one click.

The sample is emitted as a Letterboxd `diary.csv` export rather than as
``DiaryEntry`` objects, so a demo run exercises exactly the same parsing,
analysis, and rendering path a real upload takes. Watch dates are anchored
to the running year because every analysis is scoped to the current
calendar year.
"""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

SAMPLE_DISPLAY_NAME = "cinephile"

_CSV_COLUMNS = (
    "Date",
    "Name",
    "Year",
    "Letterboxd URI",
    "Rating",
    "Rewatch",
    "Watched Date",
)

# Deliberately spread across decades, countries, languages, and genres so the
# Movie DNA, Mood, and Director cards all have something real to show. The
# repeated titles are rewatches, which stay separate viewings.
_SAMPLE_VIEWINGS: tuple[tuple[str, int, str, str, bool], ...] = (
    ("Parasite", 2019, "parasite-2019", "5", False),
    ("Whiplash", 2014, "whiplash-2014", "4.5", False),
    ("In the Mood for Love", 2000, "in-the-mood-for-love", "4.5", False),
    ("Mad Max: Fury Road", 2015, "mad-max-fury-road", "4", False),
    ("Spirited Away", 2001, "spirited-away", "5", False),
    ("Pulp Fiction", 1994, "pulp-fiction", "4.5", True),
    ("Portrait of a Lady on Fire", 2019, "portrait-of-a-lady-on-fire", "5", False),
    ("Seven Samurai", 1954, "seven-samurai", "4.5", False),
    ("Get Out", 2017, "get-out-2017", "4", False),
    ("Arrival", 2016, "arrival-2016", "4.5", False),
    ("The Grand Budapest Hotel", 2014, "the-grand-budapest-hotel", "4", False),
    ("City of God", 2002, "city-of-god", "5", False),
    ("Aftersun", 2022, "aftersun", "4.5", False),
    ("Blade Runner 2049", 2017, "blade-runner-2049", "4.5", False),
    ("Chungking Express", 1994, "chungking-express", "4.5", False),
    ("Everything Everywhere All at Once", 2022, "everything-everywhere-all-at-once", "4.5", False),
    ("Moonlight", 2016, "moonlight-2016", "4.5", False),
    ("Stalker", 1979, "stalker", "4", False),
    ("Past Lives", 2023, "past-lives", "4.5", False),
    ("Paddington 2", 2017, "paddington-2", "4", False),
    ("Do the Right Thing", 1989, "do-the-right-thing", "4.5", False),
    ("Perfect Days", 2023, "perfect-days-2023", "4.5", False),
    ("Oldboy", 2003, "oldboy", "4", False),
    ("Lost in Translation", 2003, "lost-in-translation", "4", False),
    ("The Social Network", 2010, "the-social-network", "4", False),
    ("Amélie", 2001, "amelie", "4", False),
    ("Parasite", 2019, "parasite-2019", "5", True),
    ("Arrival", 2016, "arrival-2016", "4.5", True),
)

SAMPLE_VIEWING_COUNT = len(_SAMPLE_VIEWINGS)

# Uneven on purpose: an evenly spaced diary renders a flat timeline with no
# busiest month and no streak longer than a single day, which is not what a
# real viewing year looks like. Positions are fractions of the elapsed year so
# the shape survives whatever day the demo runs on.
_SAMPLE_YEAR_POSITIONS: tuple[float, ...] = (
    0.00, 0.02, 0.03, 0.09, 0.11, 0.12, 0.13,
    0.19, 0.24, 0.26, 0.27,
    0.34, 0.38, 0.41, 0.42,
    0.43, 0.51, 0.55,
    0.58, 0.62, 0.63, 0.71,
    0.78, 0.80, 0.81,
)

# A genuine three-day run ending today, so the streak and "most recent" figures
# describe something real.
_SAMPLE_TRAILING_OFFSETS: tuple[int, ...] = (2, 1, 0)


def sample_watch_dates(today: date | None = None) -> tuple[date, ...]:
    """Place the sample viewings inside the elapsed part of the running year.

    Dates are chronological and never land in the future, so the demo reads
    like a diary someone has actually been keeping.
    """
    reference = today or date.today()
    start = date(reference.year, 1, 1)
    elapsed_days = (reference - start).days
    if elapsed_days <= 0:
        return tuple(start for _ in _SAMPLE_VIEWINGS)

    spread = [
        start + timedelta(days=round(position * elapsed_days))
        for position in _SAMPLE_YEAR_POSITIONS
    ]
    # Clamped so an early-January demo cannot reach into last year.
    trailing = [
        max(reference - timedelta(days=offset), start)
        for offset in _SAMPLE_TRAILING_OFFSETS
    ]
    return tuple(sorted(spread + trailing))


def sample_diary_csv_bytes(today: date | None = None) -> bytes:
    """Return the demo diary as Letterboxd export bytes."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_COLUMNS)

    for (title, release_year, slug, rating, rewatched), watched_on in zip(
        _SAMPLE_VIEWINGS, sample_watch_dates(today), strict=True
    ):
        watched_text = watched_on.isoformat()
        writer.writerow(
            (
                watched_text,
                title,
                release_year,
                f"https://letterboxd.com/film/{slug}/",
                rating,
                "Yes" if rewatched else "",
                watched_text,
            )
        )

    return buffer.getvalue().encode("utf-8")
