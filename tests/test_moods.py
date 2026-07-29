from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from spoileralert.models import DiaryEntry, EnrichedViewing, MovieMetadata
from spoileralert.moods import (
    GENRE_MOOD_WEIGHTS,
    KEYWORD_MOOD_WEIGHTS,
    MOOD_CATEGORIES,
    OVERVIEW_PHRASE_MOOD_WEIGHTS,
    calculate_mood_profile,
    mood_profile_sentence,
)


def _viewing(
    viewing_id: int = 1,
    *,
    genres: tuple[str, ...] = (),
    keywords: tuple[str, ...] = (),
    overview: str | None = None,
    enriched: bool = True,
) -> EnrichedViewing:
    diary = DiaryEntry(
        viewing_id=str(viewing_id),
        title=f"Film {viewing_id}",
        release_year=2020,
        slug=f"film-{viewing_id}",
        watched_on=date(2026, 1, viewing_id),
        rating=None,
        rewatched=False,
    )
    metadata = None
    if enriched:
        metadata = MovieMetadata(
            tmdb_id=viewing_id,
            title=diary.title,
            release_year=2020,
            genres=genres,
            keywords=keywords,
            overview=overview,
        )
    return EnrichedViewing(diary=diary, metadata=metadata)


class MoodTests(unittest.TestCase):
    def test_signal_mappings_are_public_and_transparent(self):
        """Would fail if mood inference became opaque or its constants disappeared."""
        self.assertIn("Horror", GENRE_MOOD_WEIGHTS)
        self.assertIn("friendship", KEYWORD_MOOD_WEIGHTS)
        self.assertIn("race against time", OVERVIEW_PHRASE_MOOD_WEIGHTS)

    def test_visible_taxonomy_is_exactly_the_ten_approved_moods(self):
        """Would fail if an unapproved legacy mood could reach a card."""
        expected = (
            "Melancholic",
            "Hopeful",
            "Tense",
            "Comforting",
            "Chaotic",
            "Romantic",
            "Dark",
            "Playful",
            "Reflective",
            "Adventurous",
        )
        self.assertEqual(MOOD_CATEGORIES, expected)
        emitted = {
            mood
            for mapping in (
                GENRE_MOOD_WEIGHTS,
                KEYWORD_MOOD_WEIGHTS,
                OVERVIEW_PHRASE_MOOD_WEIGHTS,
            )
            for weights in mapping.values()
            for mood in weights
        }
        self.assertLessEqual(emitted, set(expected))

    def test_horror_and_thriller_rank_tense_then_dark(self):
        """Would fail if canonical genre strength or deterministic sorting changed."""
        moods = calculate_mood_profile(
            (_viewing(genres=("Horror", "Thriller")),)
        )

        self.assertEqual([mood.name for mood in moods[:2]], ["Tense", "Dark"])
        self.assertEqual(sum(mood.percentage for mood in moods), 100)

    def test_keyword_mapping_contributes_a_supported_mood(self):
        """Would fail if normalized metadata keywords stopped contributing."""
        moods = calculate_mood_profile((_viewing(keywords=("Friendship",)),))

        self.assertEqual(moods[0].name, "Comforting")
        self.assertGreater(moods[0].score, 0)

    def test_overview_only_matches_declared_conservative_phrases(self):
        """Would fail if generic prose words started producing invented mood signals."""
        unsupported = calculate_mood_profile(
            (_viewing(overview="A dark investigator studies a tense and difficult case."),)
        )
        supported = calculate_mood_profile(
            (_viewing(overview="A courier enters a race against time to reach home."),)
        )

        self.assertEqual(unsupported, ())
        self.assertEqual(supported[0].name, "Tense")

    def test_largest_remainder_percentages_total_exactly_one_hundred(self):
        """Would fail if independent rounding lost or created percentage points."""
        moods = calculate_mood_profile(
            (_viewing(keywords=("dance", "friendship", "space exploration")),)
        )

        self.assertGreaterEqual(len(moods), 3)
        self.assertEqual(sum(mood.percentage for mood in moods), 100)

    def test_equal_raw_scores_sort_by_mood_name_regardless_of_input_order(self):
        """Would fail if set or input iteration order leaked into visible ordering."""
        first = calculate_mood_profile(
            (_viewing(keywords=("dance", "family reunion")),)
        )
        second = calculate_mood_profile(
            (_viewing(keywords=("family reunion", "dance")),)
        )

        self.assertEqual(first, second)
        self.assertEqual([mood.name for mood in first[:2]], ["Comforting", "Playful"])

    def test_no_signal_returns_empty_scores_and_clear_sentence(self):
        """Would fail if absent metadata produced a fabricated mood profile."""
        scores = calculate_mood_profile((_viewing(enriched=False),))

        self.assertEqual(scores, ())
        self.assertIn("No supported mood signals", mood_profile_sentence(scores))

    def test_sentence_uses_the_top_three_in_fixed_order(self):
        """Would fail if prose ignored the deterministic ranked profile."""
        scores = calculate_mood_profile(
            (_viewing(keywords=("dance", "friendship", "space exploration")),)
        )

        sentence = mood_profile_sentence(scores)
        first_three = [mood.name for mood in scores[:3]]
        self.assertLess(sentence.index(first_three[0]), sentence.index(first_three[1]))
        self.assertLess(sentence.index(first_three[1]), sentence.index(first_three[2]))

    def test_returned_mood_records_are_immutable(self):
        """Would fail if callers could mutate scores after normalization."""
        mood = calculate_mood_profile((_viewing(genres=("Horror",)),))[0]

        with self.assertRaises(FrozenInstanceError):
            mood.percentage = 0  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
