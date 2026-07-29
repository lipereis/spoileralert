"""Image rendering engine: draws the shareable Wrapped card with Pillow.

No Plotly / matplotlib / kaleido here on purpose -- pure Pillow keeps the
deployment footprint tiny and avoids headless-browser / native-lib
permission headaches on cloud hosts.
"""

from __future__ import annotations

import io
import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from spoileralert.analysis import WrappedStats
from spoileralert.card_renderers import render_story_cards

# ---- Letterboxd signature dark theme -------------------------------------
COLOR_BG = "#14181c"
COLOR_PANEL = "#1c2228"
COLOR_GREEN = "#00e054"
COLOR_ORANGE = "#ff8000"
COLOR_TEXT = "#ffffff"
COLOR_MUTED = "#9ab"

CANVAS_W, CANVAS_H = 1080, 1920

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(_FONT_DIR, name)
    return ImageFont.truetype(path, size)


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    return draw.textbbox((0, 0), text, font=font)[2]


def _centered_text(draw, cx, y, text, font, fill):
    w = _text_w(draw, text, font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)
    return w


def render_wrapped_card(stats: WrappedStats) -> Image.Image:
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), COLOR_BG)
    draw = ImageDraw.Draw(img)
    cx = CANVAS_W // 2

    font_kicker = _font("Poppins-SemiBold.ttf", 34)
    font_brand = _font("Poppins-Bold.ttf", 58)
    font_username = _font("Poppins-SemiBold.ttf", 46)
    font_huge_number = _font("Poppins-Bold.ttf", 220)
    font_label = _font("Poppins-Regular.ttf", 40)
    font_section = _font("Poppins-Bold.ttf", 44)
    font_month = _font("Poppins-Bold.ttf", 64)
    font_month_count = _font("Poppins-SemiBold.ttf", 34)
    font_title = _font("Poppins-Regular.ttf", 32)
    font_footer = _font("Poppins-Regular.ttf", 28)
    font_bar_label = _font("Poppins-Regular.ttf", 22)

    year = datetime.now().year

    # ---- Header ----
    _centered_text(draw, cx, 90, "CINEPHILE", font_kicker, COLOR_GREEN)
    _centered_text(draw, cx, 130, "WRAPPED", font_brand, COLOR_TEXT)
    _centered_text(draw, cx, 210, f"@{stats.username} · {year}", font_username, COLOR_MUTED)

    draw.line([(90, 300), (CANVAS_W - 90, 300)], fill=COLOR_GREEN, width=4)

    # ---- Headline number ----
    number_text = str(stats.total_movies)
    _centered_text(draw, cx, 340, number_text, font_huge_number, COLOR_ORANGE)
    _centered_text(draw, cx, 590, "FILMES ASSISTIDOS", font_label, COLOR_TEXT)
    _centered_text(draw, cx, 640, f"em {year}", font_label, COLOR_MUTED)

    draw.line([(90, 730), (CANVAS_W - 90, 730)], fill=COLOR_PANEL, width=4)

    # ---- Peak month panel ----
    panel_top, panel_bottom = 770, 1010
    draw.rounded_rectangle(
        [(90, panel_top), (CANVAS_W - 90, panel_bottom)], radius=28, fill=COLOR_PANEL
    )
    _centered_text(draw, cx, panel_top + 30, "MÊS MAIS ATIVO", font_kicker, COLOR_GREEN)
    _centered_text(draw, cx, panel_top + 85, stats.peak_month_label, font_month, COLOR_ORANGE)
    _centered_text(
        draw,
        cx,
        panel_top + 170,
        f"{stats.peak_month_count} filmes assistidos",
        font_month_count,
        COLOR_TEXT,
    )

    # ---- Monthly bar chart ----
    chart_top, chart_bottom = 1110, 1360
    chart_left, chart_right = 110, CANVAS_W - 110
    counts = stats.monthly_counts
    max_count = max(int(counts.max()), 1)

    _centered_text(draw, cx, panel_bottom + 40, "SEU ANO EM FILMES", font_section, COLOR_TEXT)

    n_bars = len(counts)
    gap = 14
    bar_w = (chart_right - chart_left - gap * (n_bars - 1)) / n_bars
    usable_h = chart_bottom - chart_top - 40

    for i, (month_label, count) in enumerate(counts.items()):
        bar_h = (int(count) / max_count) * usable_h if max_count else 0
        x0 = chart_left + i * (bar_w + gap)
        x1 = x0 + bar_w
        y1 = chart_bottom
        y0 = y1 - bar_h
        is_peak = month_label == stats.peak_month_label
        fill = COLOR_ORANGE if is_peak else COLOR_GREEN
        draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=6, fill=fill)
        abbr = str(month_label)[:3].upper()
        w = _text_w(draw, abbr, font_bar_label)
        draw.text((x0 + bar_w / 2 - w / 2, chart_bottom + 14), abbr, font=font_bar_label, fill=COLOR_MUTED)

    divider_y = chart_bottom + 70
    draw.line([(90, divider_y), (CANVAS_W - 90, divider_y)], fill=COLOR_PANEL, width=4)

    # ---- Top titles ----
    _centered_text(draw, cx, divider_y + 35, "DESTAQUES DO ANO", font_section, COLOR_GREEN)
    y = divider_y + 110
    for title in stats.top_titles[:4]:
        display = title if len(title) <= 42 else title[:39] + "..."
        _centered_text(draw, cx, y, display, font_title, COLOR_TEXT)
        y += 52

    # ---- Footer ----
    draw.line([(90, CANVAS_H - 140), (CANVAS_W - 90, CANVAS_H - 140)], fill=COLOR_GREEN, width=4)
    _centered_text(
        draw, cx, CANVAS_H - 100, "made with Cinephile Wrapped · letterboxd.com", font_footer, COLOR_MUTED
    )

    return img


def render_to_bytes(stats: WrappedStats) -> bytes:
    img = render_wrapped_card(stats)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
