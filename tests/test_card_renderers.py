from __future__ import annotations

import io
import unittest
from dataclasses import replace
from datetime import date

import pandas as pd
from PIL import Image, ImageDraw

from spoileralert.analysis import WrappedStats, compute_enhanced_stats
from spoileralert.card_renderers import (
    dna_availability_copy,
    director_constellation_layout,
    directors_for_card,
    draw_wrapped_text,
    enrichment_fact_copy,
    fit_font,
    safe_truncate,
)
from spoileralert.models import (
    CinemaPersonality,
    DirectorStat,
    EnhancedWrappedStats,
    GenreScore,
    MoodScore,
    MovieDNA,
    TimelinePoint,
)
from spoileralert.render import render_story_cards, render_to_bytes, render_wrapped_card


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _overview(username: str = "cinefan") -> WrappedStats:
    return WrappedStats(
        username=username,
        total_movies=12,
        peak_month_label="March",
        peak_month_count=4,
        top_titles=["Arrival", "Moonlight", "Portrait of a Lady on Fire"],
        monthly_counts=pd.Series(
            [1, 2, 4, 0, 1, 0, 2, 0, 1, 0, 1, 0],
            index=[
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
            ],
            dtype="int64",
        ),
    )


def enhanced_fixture(*, username: str = "cinefan") -> EnhancedWrappedStats:
    personality = CinemaPersonality(
        key="explorer",
        title="The Explorer",
        subtitle="Your watchlist crosses borders and categories.",
        description="Variety is the through-line in the films you chose.",
        evidence=(
            "8 observed genres across 10 films",
            "5 observed countries across 9 films",
            "4 release decades across 12 dated films",
        ),
        accent_color="#69D2E7",
        limited_sample=False,
    )
    dna = MovieDNA(
        top_genres=(
            GenreScore("Drama", 7, 58.3),
            GenreScore("Science Fiction", 4, 33.3),
            GenreScore("Thriller", 3, 25.0),
        ),
        top_decades=(GenreScore("2010s", 8, 66.7), GenreScore("1990s", 2, 16.7)),
        top_languages=(GenreScore("en", 8, 66.7), GenreScore("fr", 3, 25.0)),
        top_countries=(
            GenreScore("United States", 7, 58.3),
            GenreScore("France", 3, 25.0),
        ),
        represented_decades=4,
        country_count=5,
        language_count=3,
        diversity_score=78,
        dominant_trait="Internationally curious",
        limited_sample=False,
    )
    moods = (
        MoodScore("Reflective", 5.4, 43),
        MoodScore("Dreamlike", 4.1, 33),
        MoodScore("Tender", 3.0, 24),
    )
    directors = (
        DirectorStat("Denis Villeneuve", 3, 348, 25.0, ("Arrival", "Dune"), 2018.0),
        DirectorStat("Barry Jenkins", 2, 229, 16.7, ("Moonlight",), 2016.0),
        DirectorStat("Céline Sciamma", 2, 242, 16.7, ("Portrait of a Lady on Fire",), 2019.0),
    )
    timeline = (
        TimelinePoint("Jan", 1, 116, 4.0, 0),
        TimelinePoint("Feb", 2, 210, 4.2, 0),
        TimelinePoint("Mar", 4, 460, 4.5, 1),
        TimelinePoint("Apr", 0, None, None, None),
        TimelinePoint("May", 1, 120, 3.5, 0),
        TimelinePoint("Jun", 2, 240, 4.0, 1),
        TimelinePoint("Jul", 2, 230, 4.1, 0),
    )
    return EnhancedWrappedStats(
        overview=_overview(username),
        personality=personality,
        movie_dna=dna,
        moods=moods,
        mood_sentence=(
            "Your movie mood is led by Reflective, followed by Dreamlike and Tender."
        ),
        directors=directors,
        timeline=timeline,
        busiest_period=timeline[2],
        least_active_period=timeline[0],
        average_films_per_active_period=2.0,
        first_to_last_change=1,
        active_days=10,
        longest_streak_days=3,
        enriched_film_count=12,
        total_viewing_count=12,
    )


def unenriched_fixture(*, username: str = "metadata-free") -> EnhancedWrappedStats:
    return compute_enhanced_stats(username, (), ())


def long_label_fixture() -> EnhancedWrappedStats:
    stats = enhanced_fixture(username="cinéphile-à-la-recherche-d-un-très-long-nom")
    long_text = (
        "A extraordinarily long Étude cinématographique — "
        "memória, imaginação, friendship and transformation " * 4
    ).strip()
    long_genre = GenreScore(long_text, 9, 75.0)
    long_director = DirectorStat(
        long_text,
        9,
        999,
        75.0,
        (long_text,),
        2001.0,
    )
    long_timeline = tuple(
        TimelinePoint(f"2026-W{week:02d}-extended-label", week % 5, None, None, None)
        for week in range(1, 14)
    )
    return replace(
        stats,
        overview=replace(stats.overview, top_titles=[long_text] * 5),
        personality=replace(
            stats.personality,
            title=long_text,
            subtitle=long_text,
            description=long_text,
            evidence=(long_text, long_text, long_text),
        ),
        movie_dna=replace(
            stats.movie_dna,
            top_genres=(long_genre,),
            top_decades=(long_genre,),
            top_languages=(long_genre,),
            top_countries=(long_genre,),
            dominant_trait=long_text,
        ),
        moods=(MoodScore(long_text, 5.0, 100),),
        mood_sentence=long_text,
        directors=(long_director,),
        timeline=long_timeline,
        busiest_period=long_timeline[4],
    )


def director_fixture(count: int) -> tuple[DirectorStat, ...]:
    return tuple(
        DirectorStat(
            name=f"Director {index}",
            film_count=10 - index,
            total_runtime_minutes=100 * index,
            percentage=float(10 - index),
            titles=(f"Film {index}",),
            average_release_year=2000.0 + index,
        )
        for index in range(1, count + 1)
    )


class CardRendererTests(unittest.TestCase):
    def test_director_layout_supports_fixed_ranked_positions_one_through_eight(self):
        """Would fail if the constellation truncated at five or used unstable colors."""
        expected_positions = (
            (540, 820),
            (260, 680),
            (820, 690),
            (340, 955),
            (735, 960),
            (190, 1190),
            (525, 1240),
            (870, 1175),
        )
        expected_colors = (
            "#00e054",
            "#40bcf4",
            "#ff8000",
            "#00e054",
            "#40bcf4",
            "#ff8000",
            "#00e054",
            "#40bcf4",
        )

        for count in range(1, 9):
            layout = director_constellation_layout(count)
            self.assertEqual(len(layout), count)
            self.assertEqual(
                tuple((x, y) for x, y, _ in layout),
                expected_positions[:count],
            )
            self.assertEqual(tuple(color for _, _, color in layout), expected_colors[:count])
            for x, y, _ in layout:
                self.assertTrue(150 <= x <= 930)
                self.assertTrue(600 <= y <= 1300)

        self.assertEqual(director_constellation_layout(1)[0][:2], (540, 820))
        self.assertEqual(director_constellation_layout(9), director_constellation_layout(8))

    def test_director_card_selects_and_renders_the_first_eight_ranked_directors(self):
        """Would fail if an eight-node constellation silently dropped ranks six to eight."""
        ranked = director_fixture(9)
        selected = directors_for_card(ranked)

        self.assertEqual([director.name for director in selected], [f"Director {i}" for i in range(1, 9)])
        stats = replace(enhanced_fixture(), directors=ranked)
        first = render_story_cards(stats)[4]
        second = render_story_cards(stats)[4]
        self.assertEqual(first.png_bytes, second.png_bytes)
        with Image.open(io.BytesIO(first.png_bytes)) as image:
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.size, (1080, 1920))

    def test_dna_copy_preserves_unavailable_country_and_language_counts(self):
        """Would fail if missing optional counts were presented as observed zeroes."""
        dna = replace(
            enhanced_fixture().movie_dna,
            country_count=None,
            language_count=None,
            limited_sample=False,
        )

        copy = dna_availability_copy(dna)

        self.assertEqual(
            copy,
            "4 release decades  •  countries unavailable  •  languages unavailable",
        )
        self.assertNotIn("0 countries", copy)
        self.assertNotIn("0 languages", copy)

    def test_enrichment_copy_keeps_distinct_films_and_diary_viewings_separate(self):
        """Would fail if distinct matches became a percentage of rewatch-inclusive viewings."""
        stats = replace(
            enhanced_fixture(),
            enriched_film_count=2,
            total_viewing_count=5,
        )

        matched_fact, viewing_fact = enrichment_fact_copy(stats)

        self.assertEqual(matched_fact, "2 distinct films with metadata")
        self.assertEqual(viewing_fact, "5 diary viewings logged")
        combined = f"{matched_fact} | {viewing_fact}"
        self.assertNotIn("%", combined)
        self.assertNotIn("2 / 5", combined)
        self.assertNotIn("2 of 5", combined)
        self.assertNotIn("diary films", combined)

    def test_all_six_cards_are_ordered_stable_rgb_story_pngs(self):
        """Would fail if registry order, filenames, encoding, mode, or size drifted."""
        cards = render_story_cards(enhanced_fixture())

        self.assertEqual(
            [card.slug for card in cards],
            ["overview", "personality", "movie-dna", "moods", "directors", "timeline"],
        )
        self.assertEqual(
            [card.filename for card in cards],
            [
                "spoileralert-cinefan-overview.png",
                "spoileralert-cinefan-personality.png",
                "spoileralert-cinefan-movie-dna.png",
                "spoileralert-cinefan-moods.png",
                "spoileralert-cinefan-directors.png",
                "spoileralert-cinefan-timeline.png",
            ],
        )
        self.assertEqual(len({card.filename for card in cards}), 6)
        for card in cards:
            self.assertTrue(card.png_bytes.startswith(PNG_SIGNATURE))
            with Image.open(io.BytesIO(card.png_bytes)) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (1080, 1920))
                self.assertEqual(image.mode, "RGB")

    def test_identical_input_produces_identical_card_bytes(self):
        """Would fail if time, randomness, or unordered data leaked into rendering."""
        first = render_story_cards(enhanced_fixture())
        second = render_story_cards(enhanced_fixture())

        self.assertEqual(first, second)

    def test_missing_metadata_and_empty_sections_still_return_six_honest_cards(self):
        """Would fail if any optional analysis were treated as required."""
        cards = render_story_cards(unenriched_fixture())

        self.assertEqual(len(cards), 6)
        self.assertEqual(len({card.png_bytes for card in cards}), 6)
        for card in cards:
            with Image.open(io.BytesIO(card.png_bytes)) as image:
                self.assertEqual(image.size, (1080, 1920))
                colors = image.convert("RGB").getcolors(maxcolors=1080 * 1920)
                self.assertIsNotNone(colors)
                self.assertGreater(len(colors or ()), 2)

    def test_long_unicode_content_renders_without_escaping_story_dimensions(self):
        """Would fail if long labels overflowed, raised, or changed image geometry."""
        cards = render_story_cards(long_label_fixture())

        self.assertEqual(len(cards), 6)
        for card in cards:
            with Image.open(io.BytesIO(card.png_bytes)) as image:
                self.assertEqual(image.size, (1080, 1920))
                self.assertEqual(image.getbbox(), (0, 0, 1080, 1920))

    def test_wrapped_text_is_clipped_to_its_declared_box(self):
        """Would fail if a text helper painted outside its caller-owned bounds."""
        image = Image.new("RGB", (320, 220), "#102030")
        box = (50, 35, 270, 165)
        font = fit_font("Bounded Unicode Étude", max_width=220, max_size=34, min_size=18)

        bottom = draw_wrapped_text(
            image,
            (
                "Bounded Unicode Étude — uma história muito longa "
                "que precisa continuar dentro do painel. " * 5
            ),
            box,
            font=font,
            fill="#ffffff",
            spacing=6,
        )

        self.assertLessEqual(bottom, box[3])
        self.assertTrue(
            any(image.getpixel((x, y)) != (16, 32, 48) for x in range(50, 270) for y in range(35, 165))
        )
        for x in range(image.width):
            for y in range(image.height):
                if not (box[0] <= x < box[2] and box[1] <= y < box[3]):
                    self.assertEqual(image.getpixel((x, y)), (16, 32, 48))

    def test_font_fitting_and_truncation_measure_the_actual_text(self):
        """Would fail if helpers used character counts instead of font measurements."""
        font = fit_font(
            "WWWWWWWWWW",
            max_width=190,
            max_size=48,
            min_size=12,
        )
        probe = Image.new("RGB", (300, 100))
        fitted = safe_truncate(probe, "WWWWWWWWWW", font=font, max_width=190)
        truncated = safe_truncate(
            probe,
            "A very long measured title with accents Éléonore",
            font=font,
            max_width=190,
        )

        self.assertEqual(fitted, "WWWWWWWWWW")
        self.assertTrue(truncated.endswith("…"))
        draw = ImageDraw.Draw(probe)
        self.assertLessEqual(draw.textlength(fitted, font=font), 190)
        self.assertLessEqual(draw.textlength(truncated, font=font), 190)

    def test_legacy_renderer_entry_points_remain_compatible(self):
        """Would fail if six-card support changed the existing image APIs."""
        image = render_wrapped_card(_overview())
        payload = render_to_bytes(_overview())

        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (1080, 1920))
        self.assertTrue(payload.startswith(PNG_SIGNATURE))
        with Image.open(io.BytesIO(payload)) as decoded:
            self.assertEqual(decoded.size, image.size)
            self.assertEqual(decoded.mode, image.mode)


if __name__ == "__main__":
    unittest.main()
