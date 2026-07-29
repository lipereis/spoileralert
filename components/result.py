"""Native Streamlit result presentation and in-memory card downloads."""

from __future__ import annotations

import io
import re
import unicodedata
from pathlib import PurePosixPath
from typing import Sequence
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import streamlit as st

from spoileralert.analysis import WrappedStats
from spoileralert.models import EnhancedWrappedStats, RenderedCard
from spoileralert.ui_state import reset_generation, select_next_card, select_previous_card


MONTH_LABELS_EN = {
    "Janeiro": "January",
    "Fevereiro": "February",
    "Março": "March",
    "Abril": "April",
    "Maio": "May",
    "Junho": "June",
    "Julho": "July",
    "Agosto": "August",
    "Setembro": "September",
    "Outubro": "October",
    "Novembro": "November",
    "Dezembro": "December",
}

CARD_SLUG_ORDER = (
    "overview",
    "personality",
    "movie-dna",
    "moods",
    "directors",
    "timeline",
)


def _filename_username(username: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", str(username))
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
        .strip()
        .lstrip("@")
    )
    safe_name = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")[:64]
    return safe_name or "user"


def cards_zip_filename(username: str) -> str:
    """Return a safe username-derived filename for the browser download."""
    return f"spoileralert-{_filename_username(username)}-cards.zip"


def _validated_cards(cards: Sequence[RenderedCard]) -> tuple[RenderedCard, ...]:
    ordered = tuple(cards)
    if len(ordered) != len(CARD_SLUG_ORDER):
        raise ValueError("A complete story must contain exactly six cards.")
    if tuple(card.slug for card in ordered) != CARD_SLUG_ORDER:
        raise ValueError("Story cards must follow the stable registry order.")

    seen_names: set[str] = set()
    for card in ordered:
        filename = card.filename
        if (
            not filename
            or PurePosixPath(filename).name != filename
            or "/" in filename
            or "\\" in filename
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.png", filename) is None
        ):
            raise ValueError("Card filenames must be safe PNG basenames.")
        normalized_name = filename.casefold()
        if normalized_name in seen_names:
            raise ValueError("Card filenames must be unique.")
        seen_names.add(normalized_name)
        if not isinstance(card.png_bytes, bytes):
            raise TypeError("Card payloads must be immutable bytes.")
    return ordered


def build_cards_zip(username: str, cards: Sequence[RenderedCard]) -> bytes:
    """Build a deterministic six-card ZIP entirely in memory."""
    cards_zip_filename(username)
    ordered = _validated_cards(cards)
    buffer = io.BytesIO()
    with ZipFile(buffer, mode="w") as archive:
        for card in ordered:
            entry = ZipInfo(card.filename, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o600 << 16
            archive.writestr(entry, card.png_bytes)
    return buffer.getvalue()


def _overview(stats: WrappedStats | EnhancedWrappedStats) -> WrappedStats:
    return getattr(stats, "overview", stats)


def _render_header_and_metrics(stats: WrappedStats) -> None:
    """Render the legacy editorial summary shared by both result modes."""
    with st.container(key="result-header"):
        st.caption("THE FINAL CUT")
        st.title(f"This was @{stats.username}'s year in cinema.")
        st.write("A story told through movies, months and memories.")

    active_months = sum(int(value) > 0 for value in stats.monthly_counts.tolist())
    peak_month_label = MONTH_LABELS_EN.get(stats.peak_month_label, stats.peak_month_label)
    with st.container(key="stats-grid"):
        columns = st.columns(4)
        columns[0].metric("Total films", stats.total_movies)
        columns[1].metric("Peak month", peak_month_label)
        columns[2].metric("Peak-month films", stats.peak_month_count)
        columns[3].metric("Active months", active_months)


def _render_legacy_result(stats: WrappedStats, image_bytes: bytes) -> bool:
    """Retain the original single-card component contract during migration."""
    _render_header_and_metrics(stats)
    with st.container(key="story-preview"):
        st.image(
            image_bytes,
            caption=f"@{stats.username}'s SpoilerAlert",
            width="stretch",
        )

    with st.container(key="result-actions"):
        st.download_button(
            "Download Story",
            image_bytes,
            file_name=f"wrapped_{_filename_username(stats.username)}.png",
            mime="image/png",
            width="stretch",
        )
        return st.button("Create Another", width="stretch")


def _read_card_index(card_count: int) -> int:
    try:
        selected = int(st.session_state["selected_card_index"])
    except (KeyError, TypeError, ValueError):
        selected = 0
    return max(0, min(selected, card_count - 1))


def _prepare_card_index(card_count: int) -> int:
    selected = _read_card_index(card_count)
    st.session_state["selected_card_index"] = selected
    return selected


def render_result(
    stats: WrappedStats | EnhancedWrappedStats,
    cards: bytes | Sequence[RenderedCard],
    coverage_note: str | None = None,
) -> bool:
    """Render the completed story and report whether a reset was requested.

    `coverage_note` states that the source could not supply the whole year, so
    a partial recap is never presented as a complete one.
    """
    overview = _overview(stats)
    if isinstance(cards, bytes):
        return _render_legacy_result(overview, cards)

    ordered = _validated_cards(cards)
    st.session_state["wrapped_cards"] = ordered
    _render_header_and_metrics(overview)
    if coverage_note:
        st.info(coverage_note, icon=":material/info:")
    _prepare_card_index(len(ordered))

    with st.container(key="card-selector"):
        st.selectbox(
            "Choose a story card",
            range(len(ordered)),
            format_func=lambda index: f"{index + 1:02d} · {ordered[index].title}",
            key="selected_card_index",
            width="stretch",
        )

    selected_index = _read_card_index(len(ordered))
    with st.container(
        key="card-navigation",
        horizontal=True,
        horizontal_alignment="distribute",
    ):
        st.button(
            "Previous",
            key="previous-card",
            icon=":material/arrow_back:",
            disabled=selected_index == 0,
            on_click=select_previous_card,
            args=(st.session_state,),
            width="stretch",
        )
        st.button(
            "Next",
            key="next-card",
            icon=":material/arrow_forward:",
            icon_position="right",
            disabled=selected_index == len(ordered) - 1,
            on_click=select_next_card,
            args=(st.session_state,),
            width="stretch",
        )

    selected_index = _read_card_index(len(ordered))
    selected_card = ordered[selected_index]
    with st.container(key="story-preview"):
        st.image(
            selected_card.png_bytes,
            caption=f"{selected_index + 1:02d} of {len(ordered):02d} · {selected_card.title}",
            width="stretch",
        )

    with st.container(key="selected-card-download"):
        st.download_button(
            "Download selected card",
            selected_card.png_bytes,
            file_name=selected_card.filename,
            mime="image/png",
            key="download-selected-card",
            on_click="ignore",
            icon=":material/download:",
            width="stretch",
        )

    with st.container(key="card-download-list"):
        st.subheader("Download each card")
        for index, card in enumerate(ordered, 1):
            st.download_button(
                f"{index:02d} · {card.title}",
                card.png_bytes,
                file_name=card.filename,
                mime="image/png",
                key=f"download-card-{card.slug}",
                on_click="ignore",
                icon=":material/download:",
                width="stretch",
            )

    with st.container(key="zip-download"):
        st.download_button(
            "Download all six cards",
            build_cards_zip(overview.username, ordered),
            file_name=cards_zip_filename(overview.username),
            mime="application/zip",
            key="download-all-cards",
            on_click="ignore",
            icon=":material/folder_zip:",
            width="stretch",
        )

    with st.container(key="result-actions"):
        st.button(
            "Create Another",
            key="create-another",
            on_click=reset_generation,
            args=(st.session_state,),
            width="stretch",
        )
    return False
