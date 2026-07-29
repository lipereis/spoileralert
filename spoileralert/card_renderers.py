"""Deterministic Pillow compositions for the six SpoilerAlert story cards.

Every optional analysis has a visible, factual fallback.  Drawing helpers clip
content to caller-owned boxes so unexpectedly long labels cannot change the
1080x1920 story-card contract.
"""

from __future__ import annotations

import io
import os
import re
import unicodedata
from collections.abc import Sequence
from typing import Callable

from PIL import Image, ImageColor, ImageDraw, ImageFont

from spoileralert.models import (
    DirectorStat,
    EnhancedWrappedStats,
    GenreScore,
    MovieDNA,
    RenderedCard,
)


CANVAS_W, CANVAS_H = 1080, 1920

COLOR_BG = "#14181c"
COLOR_PANEL = "#1c2228"
COLOR_PANEL_LIGHT = "#242c33"
COLOR_GREEN = "#00e054"
COLOR_ORANGE = "#ff8000"
COLOR_BLUE = "#40bcf4"
COLOR_TEXT = "#ffffff"
COLOR_MUTED = "#9ab"
COLOR_TRACK = "#303941"

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
_FONT_REGULAR = "Poppins-Regular.ttf"
_FONT_SEMIBOLD = "Poppins-SemiBold.ttf"
_FONT_BOLD = "Poppins-Bold.ttf"

Box = tuple[int, int, int, int]
CardRenderer = Callable[[EnhancedWrappedStats, int], Image.Image]


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(_FONT_DIR, name), max(1, int(size)))


def _draw(source: Image.Image | ImageDraw.ImageDraw) -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(source) if isinstance(source, Image.Image) else source


def _text_width(
    source: Image.Image | ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
) -> float:
    drawing = _draw(source)
    lines = str(text).splitlines() or [""]
    return max(float(drawing.textlength(line, font=font)) for line in lines)


def fit_font(
    text: object,
    *,
    max_width: int,
    max_size: int,
    min_size: int = 18,
    font_name: str = _FONT_SEMIBOLD,
) -> ImageFont.FreeTypeFont:
    """Return the largest local Poppins font whose measured text fits."""
    ceiling = max(int(max_size), int(min_size))
    floor = max(1, min(int(min_size), ceiling))
    probe = Image.new("RGB", (1, 1))
    value = str(text)
    for size in range(ceiling, floor - 1, -1):
        font = _font(font_name, size)
        if _text_width(probe, value, font) <= max(0, max_width):
            return font
    return _font(font_name, floor)


def safe_truncate(
    source: Image.Image | ImageDraw.ImageDraw,
    text: object,
    *,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    """Measure and ellipsize a single line without splitting Unicode code points."""
    value = " ".join(str(text).split())
    if max_width <= 0:
        return ""
    if _text_width(source, value, font) <= max_width:
        return value
    ellipsis = "…"
    if _text_width(source, ellipsis, font) > max_width:
        return ""
    low, high = 0, len(value)
    while low < high:
        middle = (low + high + 1) // 2
        candidate = value[:middle].rstrip() + ellipsis
        if _text_width(source, candidate, font) <= max_width:
            low = middle
        else:
            high = middle - 1
    return value[:low].rstrip() + ellipsis


def _wrapped_lines(
    source: Image.Image | ImageDraw.ImageDraw,
    text: object,
    *,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    paragraphs = str(text).replace("\r", "").split("\n")
    lines: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if _text_width(source, candidate, font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = safe_truncate(source, word, font=font, max_width=max_width)
        if current:
            lines.append(current)
    return lines


def draw_wrapped_text(
    image: Image.Image,
    text: object,
    box: Box,
    *,
    font: ImageFont.FreeTypeFont,
    fill: str,
    spacing: int = 8,
    max_lines: int | None = None,
    align: str = "left",
) -> int:
    """Draw measured text on a clipped overlay and return its bounded bottom."""
    left, top, right, bottom = (int(value) for value in box)
    width = max(0, right - left)
    height = max(0, bottom - top)
    if width == 0 or height == 0:
        return top

    bbox = font.getbbox("Ag")
    line_height = max(1, bbox[3] - bbox[1])
    line_step = line_height + max(0, spacing)
    height_limit = max(1, (height + max(0, spacing)) // line_step)
    line_limit = height_limit if max_lines is None else max(1, min(max_lines, height_limit))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    lines = _wrapped_lines(overlay_draw, text, font=font, max_width=width)
    if len(lines) > line_limit:
        lines = lines[:line_limit]
        final = lines[-1].rstrip("…") + "…"
        lines[-1] = safe_truncate(
            overlay_draw,
            final,
            font=font,
            max_width=width,
        )

    y = 0
    for line in lines:
        line_width = _text_width(overlay_draw, line, font)
        if align == "center":
            x = max(0.0, (width - line_width) / 2)
        elif align == "right":
            x = max(0.0, width - line_width)
        else:
            x = 0.0
        overlay_draw.text((x, y - bbox[1]), line, font=font, fill=fill)
        y += line_step
        if y >= height:
            break

    image.paste(overlay, (left, top), overlay)
    used_height = max(0, min(height, y - max(0, spacing)))
    return min(bottom, top + used_height)


def _safe_color(value: str, fallback: str = COLOR_BLUE) -> str:
    try:
        ImageColor.getrgb(value)
    except (TypeError, ValueError):
        return fallback
    return value


def draw_card_header(
    image: Image.Image,
    *,
    index: int,
    eyebrow: str,
    title: str,
    subtitle: str,
    accent: str,
) -> None:
    """Draw the common card identity inside the fixed header region."""
    draw = ImageDraw.Draw(image)
    accent = _safe_color(accent)
    draw.rounded_rectangle((72, 66, 236, 112), radius=20, fill=accent)
    draw_wrapped_text(
        image,
        f"CARD {index:02d} / 06",
        (88, 77, 220, 103),
        font=_font(_FONT_BOLD, 20),
        fill=COLOR_BG,
        align="center",
        spacing=0,
        max_lines=1,
    )
    draw_wrapped_text(
        image,
        eyebrow.upper(),
        (72, 137, 1008, 180),
        font=_font(_FONT_SEMIBOLD, 24),
        fill=accent,
        spacing=0,
        max_lines=1,
    )
    title_font = fit_font(title, max_width=936, max_size=64, min_size=38, font_name=_FONT_BOLD)
    draw_wrapped_text(
        image,
        title,
        (72, 190, 1008, 275),
        font=title_font,
        fill=COLOR_TEXT,
        spacing=0,
        max_lines=1,
    )
    draw_wrapped_text(
        image,
        subtitle,
        (72, 286, 1008, 360),
        font=_font(_FONT_REGULAR, 26),
        fill=COLOR_MUTED,
        spacing=8,
        max_lines=2,
    )
    draw.line((72, 390, 1008, 390), fill=accent, width=4)


def draw_card_footer(image: Image.Image, *, username: str, index: int) -> None:
    """Draw a measured common footer inside the final 104 pixels."""
    draw = ImageDraw.Draw(image)
    draw.line((72, 1790, 1008, 1790), fill=COLOR_TRACK, width=3)
    handle = safe_truncate(
        image,
        f"@{username}",
        font=_font(_FONT_SEMIBOLD, 25),
        max_width=430,
    )
    draw_wrapped_text(
        image,
        handle,
        (72, 1825, 512, 1865),
        font=_font(_FONT_SEMIBOLD, 25),
        fill=COLOR_TEXT,
        max_lines=1,
        spacing=0,
    )
    draw_wrapped_text(
        image,
        f"SPOILERALERT  •  {index:02d}/06",
        (540, 1825, 1008, 1865),
        font=_font(_FONT_SEMIBOLD, 25),
        fill=COLOR_MUTED,
        align="right",
        max_lines=1,
        spacing=0,
    )


def draw_bar(
    image: Image.Image,
    box: Box,
    *,
    label: str,
    value: float | None,
    max_value: float,
    accent: str,
    value_label: str | None = None,
) -> None:
    """Draw one measured label and one bounded horizontal value track."""
    left, top, right, bottom = box
    draw = ImageDraw.Draw(image)
    accent = _safe_color(accent)
    label_font = _font(_FONT_SEMIBOLD, 26)
    value_font = _font(_FONT_BOLD, 24)
    shown_label = safe_truncate(image, label, font=label_font, max_width=max(0, right - left - 190))
    draw_wrapped_text(
        image,
        shown_label,
        (left, top, right - 175, min(bottom, top + 42)),
        font=label_font,
        fill=COLOR_TEXT,
        max_lines=1,
        spacing=0,
    )
    display_value = value_label if value_label is not None else ("—" if value is None else f"{value:g}")
    draw_wrapped_text(
        image,
        display_value,
        (right - 170, top, right, min(bottom, top + 42)),
        font=value_font,
        fill=accent if value is not None else COLOR_MUTED,
        align="right",
        max_lines=1,
        spacing=0,
    )
    track_top = min(bottom - 12, top + 53)
    track_bottom = min(bottom, track_top + 16)
    if track_bottom <= track_top:
        return
    draw.rounded_rectangle((left, track_top, right, track_bottom), radius=8, fill=COLOR_TRACK)
    if value is not None and max_value > 0:
        fraction = max(0.0, min(1.0, float(value) / float(max_value)))
        fill_right = left + max(10, round((right - left) * fraction))
        draw.rounded_rectangle((left, track_top, min(right, fill_right), track_bottom), radius=8, fill=accent)


def draw_fallback_panel(
    image: Image.Image,
    box: Box,
    *,
    heading: str,
    body: str,
) -> None:
    """Draw an honest limited-data explanation inside a bounded panel."""
    left, top, right, bottom = box
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(box, radius=28, fill=COLOR_PANEL, outline=COLOR_TRACK, width=2)
    draw.ellipse((left + 34, top + 36, left + 58, top + 60), fill=COLOR_ORANGE)
    draw_wrapped_text(
        image,
        heading,
        (left + 82, top + 30, right - 32, min(bottom, top + 82)),
        font=_font(_FONT_BOLD, 28),
        fill=COLOR_TEXT,
        max_lines=1,
        spacing=0,
    )
    draw_wrapped_text(
        image,
        body,
        (left + 34, top + 102, right - 34, bottom - 28),
        font=_font(_FONT_REGULAR, 25),
        fill=COLOR_MUTED,
        spacing=9,
    )


def _base(accent: str) -> Image.Image:
    image = Image.new("RGB", (CANVAS_W, CANVAS_H), COLOR_BG)
    draw = ImageDraw.Draw(image)
    accent = _safe_color(accent)
    draw.ellipse((-220, -250, 430, 400), fill="#18262a")
    draw.ellipse((760, 1360, 1280, 2000), fill="#1b242b")
    draw.rectangle((0, 0, 12, CANVAS_H), fill=accent)
    return image


def _metric_panel(
    image: Image.Image,
    box: Box,
    *,
    label: str,
    value: object,
    accent: str = COLOR_GREEN,
) -> None:
    left, top, right, bottom = box
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(box, radius=24, fill=COLOR_PANEL, outline=COLOR_TRACK, width=2)
    draw_wrapped_text(
        image,
        label.upper(),
        (left + 26, top + 24, right - 26, top + 58),
        font=_font(_FONT_SEMIBOLD, 19),
        fill=COLOR_MUTED,
        max_lines=1,
        spacing=0,
    )
    value_text = str(value)
    value_font = fit_font(
        value_text,
        max_width=max(1, right - left - 52),
        max_size=44,
        min_size=24,
        font_name=_FONT_BOLD,
    )
    draw_wrapped_text(
        image,
        value_text,
        (left + 26, top + 72, right - 26, bottom - 18),
        font=value_font,
        fill=_safe_color(accent),
        max_lines=2,
        spacing=5,
    )


def enrichment_fact_copy(stats: EnhancedWrappedStats) -> tuple[str, str]:
    """Describe unlike enrichment/viewing counts as separate, non-ratio facts."""
    matched = max(0, int(stats.enriched_film_count))
    viewings = max(0, int(stats.total_viewing_count))
    matched_noun = "film" if matched == 1 else "films"
    viewing_noun = "viewing" if viewings == 1 else "viewings"
    return (
        f"{matched} distinct {matched_noun} with metadata",
        f"{viewings} diary {viewing_noun} logged",
    )


def dna_availability_copy(dna: MovieDNA) -> str:
    """Render present optional DNA counts and preserve ``None`` as unavailable."""
    decade_count = max(0, int(dna.represented_decades))
    decade_copy = f"{decade_count} release decade{'s' if decade_count != 1 else ''}"
    if dna.country_count is None:
        country_copy = "countries unavailable"
    else:
        country_count = max(0, int(dna.country_count))
        country_copy = f"{country_count} countr{'y' if country_count == 1 else 'ies'}"
    if dna.language_count is None:
        language_copy = "languages unavailable"
    else:
        language_count = max(0, int(dna.language_count))
        language_copy = f"{language_count} language{'s' if language_count != 1 else ''}"
    return f"{decade_copy}  •  {country_copy}  •  {language_copy}"


def _render_overview(stats: EnhancedWrappedStats, index: int) -> Image.Image:
    accent = COLOR_GREEN
    image = _base(accent)
    overview = stats.overview
    draw_card_header(
        image,
        index=index,
        eyebrow="Your year in cinema",
        title="The Overview",
        subtitle="Observed diary activity, with a preview of your cinema personality.",
        accent=accent,
    )
    total_text = str(max(0, overview.total_movies))
    total_font = fit_font(total_text, max_width=500, max_size=190, min_size=96, font_name=_FONT_BOLD)
    draw_wrapped_text(
        image,
        total_text,
        (72, 440, 650, 640),
        font=total_font,
        fill=COLOR_ORANGE,
        max_lines=1,
        spacing=0,
    )
    draw_wrapped_text(
        image,
        "DIARY VIEWINGS",
        (82, 645, 650, 690),
        font=_font(_FONT_SEMIBOLD, 27),
        fill=COLOR_TEXT,
        max_lines=1,
        spacing=0,
    )
    _metric_panel(
        image,
        (680, 450, 1008, 690),
        label="Peak period",
        value=(
            f"{overview.peak_month_label}\n{overview.peak_month_count} films"
            if overview.total_movies
            else "Unavailable"
        ),
        accent=COLOR_ORANGE,
    )
    _metric_panel(image, (72, 745, 370, 965), label="Active days", value=stats.active_days)
    matched_fact, _ = enrichment_fact_copy(stats)
    _metric_panel(
        image,
        (391, 745, 689, 965),
        label="Metadata matches",
        value=matched_fact,
        accent=COLOR_BLUE,
    )
    _metric_panel(
        image,
        (710, 745, 1008, 965),
        label="Longest streak",
        value=(f"{stats.longest_streak_days} days" if stats.longest_streak_days else "Unavailable"),
        accent=COLOR_ORANGE,
    )
    draw_wrapped_text(
        image,
        "YEAR HIGHLIGHTS",
        (72, 1045, 1008, 1090),
        font=_font(_FONT_BOLD, 28),
        fill=COLOR_GREEN,
        max_lines=1,
        spacing=0,
    )
    if overview.top_titles:
        y = 1110
        for position, title in enumerate(overview.top_titles[:4], 1):
            draw_wrapped_text(
                image,
                f"{position:02d}",
                (72, y, 132, y + 45),
                font=_font(_FONT_BOLD, 24),
                fill=COLOR_ORANGE,
                max_lines=1,
                spacing=0,
            )
            draw_wrapped_text(
                image,
                title,
                (150, y, 1008, y + 48),
                font=_font(_FONT_REGULAR, 27),
                fill=COLOR_TEXT,
                max_lines=1,
                spacing=0,
            )
            y += 64
    else:
        draw_fallback_panel(
            image,
            (72, 1105, 1008, 1285),
            heading="No diary highlights available",
            body="No film titles were present in this year's diary, so none are invented here.",
        )
    personality_accent = _safe_color(stats.personality.accent_color, COLOR_BLUE)
    ImageDraw.Draw(image).rounded_rectangle(
        (72, 1410, 1008, 1698),
        radius=30,
        fill=COLOR_PANEL,
        outline=personality_accent,
        width=3,
    )
    draw_wrapped_text(
        image,
        "PERSONALITY PREVIEW",
        (108, 1447, 972, 1485),
        font=_font(_FONT_SEMIBOLD, 21),
        fill=personality_accent,
        max_lines=1,
        spacing=0,
    )
    draw_wrapped_text(
        image,
        stats.personality.title,
        (108, 1505, 972, 1585),
        font=fit_font(stats.personality.title, max_width=864, max_size=44, min_size=28, font_name=_FONT_BOLD),
        fill=COLOR_TEXT,
        max_lines=1,
        spacing=0,
    )
    draw_wrapped_text(
        image,
        stats.personality.subtitle,
        (108, 1600, 972, 1668),
        font=_font(_FONT_REGULAR, 24),
        fill=COLOR_MUTED,
        max_lines=2,
        spacing=7,
    )
    draw_card_footer(image, username=overview.username, index=index)
    return image


def _render_personality(stats: EnhancedWrappedStats, index: int) -> Image.Image:
    personality = stats.personality
    accent = _safe_color(personality.accent_color, COLOR_BLUE)
    image = _base(accent)
    draw_card_header(
        image,
        index=index,
        eyebrow="Cinema personality",
        title="Your Viewing Archetype",
        subtitle="A deterministic portrait based only on available diary and metadata signals.",
        accent=accent,
    )
    ImageDraw.Draw(image).rounded_rectangle(
        (72, 450, 1008, 965), radius=34, fill=COLOR_PANEL, outline=accent, width=4
    )
    draw_wrapped_text(
        image,
        "LIMITED SAMPLE" if personality.limited_sample else "YOUR ARCHETYPE",
        (112, 495, 968, 540),
        font=_font(_FONT_SEMIBOLD, 22),
        fill=accent,
        max_lines=1,
        spacing=0,
    )
    title_font = fit_font(
        personality.title,
        max_width=856,
        max_size=67,
        min_size=32,
        font_name=_FONT_BOLD,
    )
    draw_wrapped_text(
        image,
        personality.title,
        (112, 575, 968, 700),
        font=title_font,
        fill=COLOR_TEXT,
        max_lines=2,
        spacing=7,
    )
    draw_wrapped_text(
        image,
        personality.subtitle,
        (112, 735, 968, 825),
        font=_font(_FONT_SEMIBOLD, 28),
        fill=accent,
        max_lines=2,
        spacing=8,
    )
    draw_wrapped_text(
        image,
        personality.description,
        (112, 845, 968, 925),
        font=_font(_FONT_REGULAR, 24),
        fill=COLOR_MUTED,
        max_lines=2,
        spacing=8,
    )
    draw_wrapped_text(
        image,
        "OBSERVED EVIDENCE",
        (72, 1055, 1008, 1100),
        font=_font(_FONT_BOLD, 28),
        fill=COLOR_TEXT,
        max_lines=1,
        spacing=0,
    )
    if personality.evidence:
        y = 1130
        for evidence_index, evidence in enumerate(personality.evidence[:3], 1):
            ImageDraw.Draw(image).rounded_rectangle(
                (72, y, 1008, y + 145), radius=22, fill=COLOR_PANEL, outline=COLOR_TRACK, width=2
            )
            ImageDraw.Draw(image).ellipse((104, y + 50, 142, y + 88), fill=accent)
            draw_wrapped_text(
                image,
                str(evidence_index),
                (104, y + 55, 142, y + 85),
                font=_font(_FONT_BOLD, 18),
                fill=COLOR_BG,
                align="center",
                max_lines=1,
                spacing=0,
            )
            draw_wrapped_text(
                image,
                evidence,
                (170, y + 35, 970, y + 115),
                font=_font(_FONT_REGULAR, 25),
                fill=COLOR_TEXT,
                max_lines=2,
                spacing=8,
            )
            y += 170
    else:
        draw_fallback_panel(
            image,
            (72, 1130, 1008, 1400),
            heading="Evidence is still limited",
            body="There are not enough supported observations to list evidence without guessing.",
        )
    draw_card_footer(image, username=stats.overview.username, index=index)
    return image


def _score_summary(scores: Sequence[GenreScore]) -> tuple[str, float | None, str]:
    if not scores:
        return "Unavailable", None, "No supported metadata"
    leading = scores[0]
    names = "  •  ".join(score.name for score in scores[:2])
    return names, leading.percentage, f"{leading.percentage:.1f}% lead"


def _render_movie_dna(stats: EnhancedWrappedStats, index: int) -> Image.Image:
    dna = stats.movie_dna
    accent = COLOR_BLUE
    image = _base(accent)
    draw_card_header(
        image,
        index=index,
        eyebrow="Movie DNA",
        title="The Strands of Your Taste",
        subtitle="Calculated from distinct films with available, supported metadata.",
        accent=accent,
    )
    _metric_panel(
        image,
        (72, 450, 518, 690),
        label="Dominant trait",
        value=dna.dominant_trait,
        accent=COLOR_BLUE,
    )
    _metric_panel(
        image,
        (538, 450, 1008, 690),
        label="Diversity score",
        value=f"{dna.diversity_score} / 100" if dna.diversity_score is not None else "Unavailable",
        accent=COLOR_ORANGE,
    )
    draw_wrapped_text(
        image,
        "FIVE OBSERVED STRANDS",
        (72, 770, 1008, 815),
        font=_font(_FONT_BOLD, 28),
        fill=COLOR_TEXT,
        max_lines=1,
        spacing=0,
    )
    strand_specs = (
        ("Genres", dna.top_genres, COLOR_GREEN),
        ("Release decades", dna.top_decades, COLOR_ORANGE),
        ("Languages", dna.top_languages, COLOR_BLUE),
        ("Countries", dna.top_countries, "#9b5de5"),
    )
    y = 855
    for strand_label, values, strand_accent in strand_specs:
        summary, value, value_label = _score_summary(values)
        draw_wrapped_text(
            image,
            strand_label.upper(),
            (72, y, 250, y + 34),
            font=_font(_FONT_SEMIBOLD, 19),
            fill=COLOR_MUTED,
            max_lines=1,
            spacing=0,
        )
        draw_bar(
            image,
            (260, y, 1008, y + 80),
            label=summary,
            value=value,
            max_value=100,
            accent=strand_accent,
            value_label=value_label,
        )
        y += 135
    matched_fact, viewing_fact = enrichment_fact_copy(stats)
    draw_wrapped_text(
        image,
        "METADATA BASIS",
        (72, y, 250, y + 34),
        font=_font(_FONT_SEMIBOLD, 19),
        fill=COLOR_MUTED,
        max_lines=1,
        spacing=0,
    )
    ImageDraw.Draw(image).rounded_rectangle(
        (260, y, 1008, y + 92),
        radius=18,
        fill=COLOR_PANEL,
        outline=COLOR_TRACK,
        width=2,
    )
    draw_wrapped_text(
        image,
        matched_fact,
        (286, y + 16, 982, y + 48),
        font=_font(_FONT_SEMIBOLD, 22),
        fill=COLOR_GREEN,
        max_lines=1,
        spacing=0,
    )
    draw_wrapped_text(
        image,
        viewing_fact,
        (286, y + 52, 982, y + 82),
        font=_font(_FONT_REGULAR, 20),
        fill=COLOR_MUTED,
        max_lines=1,
        spacing=0,
    )
    draw_wrapped_text(
        image,
        dna_availability_copy(dna),
        (72, 1560, 1008, 1610),
        font=_font(_FONT_SEMIBOLD, 23),
        fill=COLOR_MUTED,
        max_lines=1,
        spacing=0,
    )
    if dna.limited_sample or dna.diversity_score is None:
        draw_wrapped_text(
            image,
            "Limited metadata: absent strands remain unavailable and do not become zero-valued taste signals.",
            (72, 1630, 1008, 1710),
            font=_font(_FONT_REGULAR, 23),
            fill=COLOR_MUTED,
            max_lines=2,
            spacing=8,
        )
    draw_card_footer(image, username=stats.overview.username, index=index)
    return image


def _render_moods(stats: EnhancedWrappedStats, index: int) -> Image.Image:
    accent = COLOR_ORANGE
    image = _base(accent)
    draw_card_header(
        image,
        index=index,
        eyebrow="Mood analysis",
        title="The Feeling of Your Films",
        subtitle="Inferred only from the declared genre, keyword, and overview signal map.",
        accent=accent,
    )
    if not stats.moods:
        draw_fallback_panel(
            image,
            (72, 480, 1008, 850),
            heading="No supported mood signals found",
            body=(
                "Available metadata did not match the documented mood map. "
                "This card stays present without assigning a feeling that was not observed."
            ),
        )
        draw_wrapped_text(
            image,
            stats.mood_sentence,
            (72, 980, 1008, 1130),
            font=_font(_FONT_SEMIBOLD, 31),
            fill=COLOR_TEXT,
            max_lines=3,
            spacing=10,
        )
    else:
        lead = stats.moods[0]
        draw_wrapped_text(
            image,
            "LEADING MOOD",
            (72, 465, 1008, 510),
            font=_font(_FONT_SEMIBOLD, 22),
            fill=COLOR_MUTED,
            max_lines=1,
            spacing=0,
        )
        lead_font = fit_font(lead.name, max_width=740, max_size=82, min_size=40, font_name=_FONT_BOLD)
        draw_wrapped_text(
            image,
            lead.name,
            (72, 535, 800, 640),
            font=lead_font,
            fill=COLOR_ORANGE,
            max_lines=1,
            spacing=0,
        )
        draw_wrapped_text(
            image,
            f"{lead.percentage}%",
            (800, 535, 1008, 640),
            font=_font(_FONT_BOLD, 62),
            fill=COLOR_TEXT,
            align="right",
            max_lines=1,
            spacing=0,
        )
        y = 735
        bar_colors = (COLOR_ORANGE, COLOR_BLUE, COLOR_GREEN)
        for mood, mood_accent in zip(stats.moods[:3], bar_colors):
            draw_bar(
                image,
                (72, y, 1008, y + 105),
                label=mood.name,
                value=float(mood.percentage),
                max_value=100,
                accent=mood_accent,
                value_label=f"{mood.percentage}%",
            )
            y += 155
        ImageDraw.Draw(image).rounded_rectangle(
            (72, 1270, 1008, 1535), radius=28, fill=COLOR_PANEL, outline=COLOR_TRACK, width=2
        )
        draw_wrapped_text(
            image,
            "EDITORIAL READ",
            (108, 1310, 972, 1350),
            font=_font(_FONT_SEMIBOLD, 21),
            fill=COLOR_ORANGE,
            max_lines=1,
            spacing=0,
        )
        draw_wrapped_text(
            image,
            stats.mood_sentence,
            (108, 1380, 972, 1495),
            font=_font(_FONT_SEMIBOLD, 29),
            fill=COLOR_TEXT,
            max_lines=3,
            spacing=9,
        )
    draw_card_footer(image, username=stats.overview.username, index=index)
    return image


DIRECTOR_POSITION_MAP: tuple[tuple[int, int], ...] = (
    (540, 820),
    (260, 680),
    (820, 690),
    (340, 955),
    (735, 960),
    (190, 1190),
    (525, 1240),
    (870, 1175),
)
DIRECTOR_ACCENTS: tuple[str, ...] = (COLOR_GREEN, COLOR_BLUE, COLOR_ORANGE)


def director_constellation_layout(count: int) -> tuple[tuple[int, int, str], ...]:
    """Return the fixed ranked 1–8 node layout with deterministic accent cycling."""
    visible_count = max(0, min(8, int(count)))
    return tuple(
        (x, y, DIRECTOR_ACCENTS[index % len(DIRECTOR_ACCENTS)])
        for index, (x, y) in enumerate(DIRECTOR_POSITION_MAP[:visible_count])
    )


def directors_for_card(directors: Sequence[DirectorStat]) -> tuple[DirectorStat, ...]:
    """Keep the first eight already-ranked director records for the card."""
    return tuple(directors[:8])


def _director_runtime(minutes: int | None) -> str:
    if minutes is None:
        return "Runtime unavailable"
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder:02d}m known runtime"


def _draw_director_list(
    image: Image.Image,
    directors: Sequence[DirectorStat],
    *,
    top: int,
    bottom: int,
) -> None:
    y = top
    for rank, director in enumerate(directors, 1):
        if y + 82 > bottom:
            break
        name = director.name
        count = director.film_count
        draw_wrapped_text(
            image,
            f"{rank:02d}",
            (72, y, 126, y + 42),
            font=_font(_FONT_BOLD, 24),
            fill=COLOR_ORANGE,
            max_lines=1,
            spacing=0,
        )
        draw_wrapped_text(
            image,
            name,
            (145, y, 800, y + 44),
            font=_font(_FONT_SEMIBOLD, 26),
            fill=COLOR_TEXT,
            max_lines=1,
            spacing=0,
        )
        draw_wrapped_text(
            image,
            f"{count} credited viewing{'s' if count != 1 else ''}",
            (810, y, 1008, y + 44),
            font=_font(_FONT_REGULAR, 21),
            fill=COLOR_MUTED,
            align="right",
            max_lines=1,
            spacing=0,
        )
        y += 78


def _render_directors(stats: EnhancedWrappedStats, index: int) -> Image.Image:
    accent = COLOR_GREEN
    image = _base(accent)
    draw_card_header(
        image,
        index=index,
        eyebrow="Director universe",
        title="The Filmmakers in Your Orbit",
        subtitle="Credits are counted per diary viewing, including rewatches and co-directors.",
        accent=accent,
    )
    directors = directors_for_card(stats.directors)
    if not directors:
        draw_fallback_panel(
            image,
            (72, 480, 1008, 850),
            heading="Director credits unavailable",
            body=(
                "No supported director metadata was matched for these films. "
                "No anonymous filmmaker or zero runtime is fabricated."
            ),
        )
    elif len(directors) == 1:
        lead = directors[0]
        center_x, center_y, node_color = director_constellation_layout(1)[0]
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (140, 475, 940, 1285),
            radius=38,
            fill=COLOR_PANEL,
            outline=node_color,
            width=4,
        )
        draw_wrapped_text(
            image,
            "YOUR DIRECTOR PROFILE",
            (190, 520, 890, 565),
            font=_font(_FONT_SEMIBOLD, 22),
            fill=node_color,
            align="center",
            max_lines=1,
            spacing=0,
        )
        radius = 142
        draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            fill=node_color,
            outline=COLOR_TEXT,
            width=5,
        )
        draw_wrapped_text(
            image,
            str(lead.film_count),
            (center_x - 80, center_y - 52, center_x + 80, center_y + 36),
            font=_font(_FONT_BOLD, 66),
            fill=COLOR_BG,
            align="center",
            max_lines=1,
            spacing=0,
        )
        draw_wrapped_text(
            image,
            "CREDITED VIEWINGS",
            (center_x - 125, center_y + 44, center_x + 125, center_y + 80),
            font=_font(_FONT_BOLD, 17),
            fill=COLOR_BG,
            align="center",
            max_lines=1,
            spacing=0,
        )
        draw_wrapped_text(
            image,
            lead.name,
            (190, 1010, 890, 1095),
            font=fit_font(lead.name, max_width=700, max_size=48, min_size=28, font_name=_FONT_BOLD),
            fill=COLOR_TEXT,
            align="center",
            max_lines=2,
            spacing=6,
        )
        draw_wrapped_text(
            image,
            _director_runtime(lead.total_runtime_minutes),
            (190, 1120, 890, 1170),
            font=_font(_FONT_REGULAR, 23),
            fill=COLOR_MUTED,
            align="center",
            max_lines=1,
            spacing=0,
        )
        _metric_panel(
            image,
            (170, 1370, 520, 1620),
            label="Share of credited viewings",
            value=f"{lead.percentage:.1f}%",
            accent=COLOR_ORANGE,
        )
        _metric_panel(
            image,
            (560, 1370, 910, 1620),
            label="Unique titles",
            value=len(lead.titles),
            accent=COLOR_BLUE,
        )
    else:
        lead = directors[0]
        draw_wrapped_text(
            image,
            "LEADING DIRECTOR",
            (72, 455, 1008, 495),
            font=_font(_FONT_SEMIBOLD, 21),
            fill=COLOR_MUTED,
            max_lines=1,
            spacing=0,
        )
        draw_wrapped_text(
            image,
            lead.name,
            (72, 515, 1008, 590),
            font=fit_font(lead.name, max_width=936, max_size=52, min_size=28, font_name=_FONT_BOLD),
            fill=COLOR_GREEN,
            max_lines=1,
            spacing=0,
        )
        draw_wrapped_text(
            image,
            f"{lead.film_count} credited viewings  •  {_director_runtime(lead.total_runtime_minutes)}",
            (72, 600, 1008, 650),
            font=_font(_FONT_REGULAR, 23),
            fill=COLOR_MUTED,
            max_lines=1,
            spacing=0,
        )
        draw = ImageDraw.Draw(image)
        layout = director_constellation_layout(len(directors))
        lead_x, lead_y, _ = layout[0]
        for x, y, _ in layout[1:]:
            draw.line((lead_x, lead_y, x, y), fill=COLOR_TRACK, width=5)
        max_count = max(director.film_count for director in directors)
        for director, (x, y, node_color) in zip(directors, layout):
            radius = 42 + round(35 * director.film_count / max(1, max_count))
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=node_color, outline=COLOR_TEXT, width=3)
            draw_wrapped_text(
                image,
                str(director.film_count),
                (x - 35, y - 18, x + 35, y + 20),
                font=_font(_FONT_BOLD, 27),
                fill=COLOR_BG,
                align="center",
                max_lines=1,
                spacing=0,
            )
            draw_wrapped_text(
                image,
                director.name,
                (max(72, x - 145), y + radius + 15, min(1008, x + 145), y + radius + 78),
                font=_font(_FONT_SEMIBOLD, 20),
                fill=COLOR_TEXT,
                align="center",
                max_lines=2,
                spacing=5,
            )
        draw_wrapped_text(
            image,
            "RANKED ORBIT",
            (72, 1440, 1008, 1480),
            font=_font(_FONT_BOLD, 25),
            fill=COLOR_MUTED,
            max_lines=1,
            spacing=0,
        )
        _draw_director_list(image, directors, top=1505, bottom=1735)
    draw_card_footer(image, username=stats.overview.username, index=index)
    return image


def _timeline_label_step(points: Sequence[object], *, width: int, font: ImageFont.FreeTypeFont) -> int:
    if not points:
        return 1
    probe = Image.new("RGB", (1, 1))
    labels = [str(getattr(point, "label", "")) for point in points]
    for step in range(1, len(labels) + 1):
        visible = labels[::step]
        occupied = sum(min(140.0, _text_width(probe, label, font)) + 18 for label in visible)
        if occupied <= width:
            return step
    return len(labels)


def _render_timeline(stats: EnhancedWrappedStats, index: int) -> Image.Image:
    accent = COLOR_BLUE
    image = _base(accent)
    draw_card_header(
        image,
        index=index,
        eyebrow="Viewing timeline",
        title="The Rhythm of Your Year",
        subtitle="Diary activity by represented period; internal gaps stay visible as zero periods.",
        accent=accent,
    )
    points = stats.timeline
    if not points:
        draw_fallback_panel(
            image,
            (72, 480, 1008, 850),
            heading="No timeline available",
            body="No dated diary activity was available, so no period or busiest point is invented.",
        )
    else:
        draw = ImageDraw.Draw(image)
        chart_left, chart_right = 92, 988
        chart_top, chart_bottom = 535, 1130
        draw.line((chart_left, chart_bottom, chart_right, chart_bottom), fill=COLOR_TRACK, width=4)
        max_count = max(1, max(point.film_count for point in points))
        slot_width = (chart_right - chart_left) / len(points)
        bar_width = max(8, min(60, slot_width * 0.58))
        label_font = _font(_FONT_REGULAR, 18)
        label_step = _timeline_label_step(points, width=chart_right - chart_left, font=label_font)
        busiest = stats.busiest_period
        for point_index, point in enumerate(points):
            center_x = chart_left + slot_width * (point_index + 0.5)
            bar_height = (point.film_count / max_count) * (chart_bottom - chart_top - 80)
            top = chart_bottom - max(8, bar_height)
            is_busiest = busiest is not None and point == busiest
            fill = COLOR_ORANGE if is_busiest else COLOR_GREEN
            draw.rounded_rectangle(
                (center_x - bar_width / 2, top, center_x + bar_width / 2, chart_bottom),
                radius=max(3, round(bar_width / 5)),
                fill=fill,
            )
            if point.film_count > 0:
                draw_wrapped_text(
                    image,
                    str(point.film_count),
                    (round(center_x - slot_width / 2), round(top - 40), round(center_x + slot_width / 2), round(top - 5)),
                    font=_font(_FONT_BOLD, 18),
                    fill=fill,
                    align="center",
                    max_lines=1,
                    spacing=0,
                )
            if point_index % label_step == 0:
                draw_wrapped_text(
                    image,
                    point.label,
                    (
                        round(center_x - slot_width * label_step / 2),
                        chart_bottom + 28,
                        round(center_x + slot_width * label_step / 2),
                        chart_bottom + 88,
                    ),
                    font=label_font,
                    fill=COLOR_TEXT if is_busiest else COLOR_MUTED,
                    align="center",
                    max_lines=2,
                    spacing=3,
                )
        if busiest is not None:
            draw_wrapped_text(
                image,
                f"Busiest point: {busiest.label} with {busiest.film_count} films",
                (72, 1240, 1008, 1300),
                font=_font(_FONT_BOLD, 30),
                fill=COLOR_ORANGE,
                max_lines=1,
                spacing=0,
            )
    streak_value = f"{stats.longest_streak_days} days" if stats.longest_streak_days else "Unavailable"
    average_value = (
        f"{stats.average_films_per_active_period:g} films"
        if stats.average_films_per_active_period is not None
        else "Unavailable"
    )
    _metric_panel(image, (72, 1390, 370, 1640), label="Active days", value=stats.active_days)
    _metric_panel(image, (391, 1390, 689, 1640), label="Longest streak", value=streak_value, accent=COLOR_ORANGE)
    _metric_panel(image, (710, 1390, 1008, 1640), label="Active-period average", value=average_value, accent=COLOR_BLUE)
    draw_card_footer(image, username=stats.overview.username, index=index)
    return image


_CARD_REGISTRY: tuple[tuple[str, str, CardRenderer], ...] = (
    ("overview", "Overview", _render_overview),
    ("personality", "Cinema Personality", _render_personality),
    ("movie-dna", "Movie DNA", _render_movie_dna),
    ("moods", "Mood Analysis", _render_moods),
    ("directors", "Director Universe", _render_directors),
    ("timeline", "Viewing Timeline", _render_timeline),
)


def _filename_username(username: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(username)).encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^a-z0-9]+", "-", normalized.casefold().lstrip("@")).strip("-")
    return (safe[:40].rstrip("-") or "user")


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=False, compress_level=9)
    return buffer.getvalue()


def render_story_cards(stats: EnhancedWrappedStats) -> tuple[RenderedCard, ...]:
    """Render the fixed six-card registry to immutable, deterministic PNG payloads."""
    username = _filename_username(stats.overview.username)
    cards: list[RenderedCard] = []
    for index, (slug, title, renderer) in enumerate(_CARD_REGISTRY, 1):
        image = renderer(stats, index)
        cards.append(
            RenderedCard(
                slug=slug,
                title=title,
                filename=f"spoileralert-{username}-{slug}.png",
                png_bytes=_png_bytes(image),
            )
        )
    return tuple(cards)


__all__ = [
    "CANVAS_H",
    "CANVAS_W",
    "DIRECTOR_ACCENTS",
    "DIRECTOR_POSITION_MAP",
    "dna_availability_copy",
    "director_constellation_layout",
    "directors_for_card",
    "draw_bar",
    "draw_card_footer",
    "draw_card_header",
    "draw_fallback_panel",
    "draw_wrapped_text",
    "enrichment_fact_copy",
    "fit_font",
    "render_story_cards",
    "safe_truncate",
]
