"""Four-stage Streamlit coordinator for SpoilerAlert."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

import streamlit as st

from components.errors import IncompleteStoryError, UiError, map_exception, render_error
from components.generator import (
    render_csv_uploader_form,
    render_generator_form,
    render_loading_shell,
    render_sample_button,
)
from components.layout import (
    load_styles,
    render_features,
    render_footer,
    render_header,
    render_hero,
)
from components.result import CARD_SLUG_ORDER, render_result
from spoileralert.analysis import compute_enhanced_stats
from spoileralert.data import get_rich_diary_entries_from_csv
from spoileralert.metadata import (
    enrich_diary_entries,
    get_tmdb_api_key,
    lookup_movie_metadata,
    normalize_title,
)
from spoileralert.models import EnrichedViewing, MovieMetadata
from spoileralert.render import render_story_cards
from spoileralert.rss import fetch_diary_feed
from spoileralert.sample import SAMPLE_DISPLAY_NAME, sample_diary_csv_bytes
from spoileralert.ui_state import (
    begin_generation,
    initialize_state,
    reset_generation,
    set_error,
    set_result,
)


st.set_page_config(
    page_title="SpoilerAlert",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


BLANK_USERNAME_ERROR = UiError(
    title="A username belongs in the starring role.",
    message="Enter the public Letterboxd username you want to analyze.",
    action="Add a username, then start the story again.",
)

TMDB_METADATA_CACHE_VERSION = "tmdb-public-metadata-v1"
_TMDB_CREDENTIAL_PROVIDER: ContextVar[Callable[[], str | None] | None] = ContextVar(
    "tmdb_credential_provider",
    default=None,
)


class _UncacheableMetadata(Exception):
    """Internal control flow ensuring misses and failures never enter the cache."""


@contextmanager
def tmdb_credential_scope(
    provider: Callable[[], str | None],
) -> Iterator[None]:
    """Make one generation-local credential provider available to cache misses."""
    token = _TMDB_CREDENTIAL_PROVIDER.set(provider)
    try:
        yield
    finally:
        _TMDB_CREDENTIAL_PROVIDER.reset(token)


@st.cache_data(ttl=86400, max_entries=2048, show_spinner=False)
def _cached_lookup_movie_metadata(
    normalized_title: str,
    release_year: int | None,
    configuration_version: str,
) -> MovieMetadata:
    """Cache only successful public metadata using non-secret arguments."""
    del configuration_version
    provider = _TMDB_CREDENTIAL_PROVIDER.get()
    if provider is None:
        raise _UncacheableMetadata
    try:
        api_key = provider()
        if not api_key:
            raise _UncacheableMetadata
        metadata = lookup_movie_metadata(normalized_title, release_year, api_key)
    except _UncacheableMetadata:
        raise
    except Exception:
        raise _UncacheableMetadata from None
    if metadata is None:
        raise _UncacheableMetadata
    return metadata


def lookup_cached_movie_metadata(
    title: str,
    release_year: int | None,
) -> MovieMetadata | None:
    """Return a cached successful lookup while retrying every miss or failure."""
    normalized_title = normalize_title(title)
    if not normalized_title:
        return None
    try:
        return _cached_lookup_movie_metadata(
            normalized_title,
            release_year,
            TMDB_METADATA_CACHE_VERSION,
        )
    except _UncacheableMetadata:
        return None


def lookup_cached_movie_metadata_with_key(
    title: str,
    release_year: int | None,
    _api_key: str,
) -> MovieMetadata | None:
    """Adapt the application cache boundary to the pure enrichment interface."""
    return lookup_cached_movie_metadata(title, release_year)


def _start_csv_generation(csv_submission: tuple[str, bytes]) -> None:
    """Route one uploaded diary export into a fresh generation attempt."""
    display_name, csv_bytes = csv_submission
    normalized_name = display_name.strip().lstrip("@") or "you"
    begin_generation(st.session_state, normalized_name, csv_bytes)
    st.rerun()


def _render_landing() -> None:
    render_hero()
    # The demo and the upload both work on any host, so they come before the
    # live-profile form that a blocked host cannot serve.
    sample_clicked = render_sample_button()
    csv_submission = render_csv_uploader_form()
    submitted_username = render_generator_form()
    render_features()
    render_footer()

    if sample_clicked:
        begin_generation(
            st.session_state,
            SAMPLE_DISPLAY_NAME,
            sample_diary_csv_bytes(),
        )
        st.rerun()
        return

    if csv_submission is not None:
        _start_csv_generation(csv_submission)
        return

    if submitted_username is None:
        return
    if not submitted_username.strip().lstrip("@"):
        set_error(st.session_state, BLANK_USERNAME_ERROR)
        st.rerun()
        return

    begin_generation(st.session_state, submitted_username)
    st.rerun()


def _run_generation() -> None:
    username = st.session_state["username"]
    diary_csv_bytes = st.session_state.get("diary_csv_bytes")
    status = None

    try:
        status, progress = render_loading_shell()
        status.update(
            label="Opening your Letterboxd diary…",
            state="running",
            expanded=True,
        )
        if diary_csv_bytes is not None:
            entries = get_rich_diary_entries_from_csv(diary_csv_bytes)
        else:
            # Letterboxd's public feed is the only username-only route that
            # works from a shared cloud address, at the cost of covering
            # recent activity rather than a guaranteed whole year.
            feed = fetch_diary_feed(username)
            entries = list(feed.entries)
            st.session_state["coverage_note"] = feed.coverage_note
        progress.progress(25, text="Diary loaded")

        status.update(
            label="Adding optional film details…",
            state="running",
            expanded=True,
        )
        try:
            api_key = get_tmdb_api_key(st.secrets)
            if api_key is None:
                enriched = enrich_diary_entries(entries, None)
            else:
                with tmdb_credential_scope(lambda: api_key):
                    enriched = enrich_diary_entries(
                        entries,
                        api_key,
                        lookup=lookup_cached_movie_metadata_with_key,
                    )
        except Exception:  # noqa: BLE001 - enrichment is explicitly optional
            logging.warning(
                "TMDB enrichment unavailable; continuing without movie metadata."
            )
            enriched = tuple(
                EnrichedViewing(diary=entry, metadata=None) for entry in entries
            )
        progress.progress(50, text="Optional film details checked")

        status.update(
            label="Finding the patterns in your movie year…",
            state="running",
            expanded=True,
        )
        stats = compute_enhanced_stats(username, entries, enriched)
        progress.progress(75, text="Viewing patterns analyzed")

        status.update(
            label="Designing all six cinematic story cards…",
            state="running",
            expanded=True,
        )
        cards = tuple(render_story_cards(stats))
        if (
            len(cards) != len(CARD_SLUG_ORDER)
            or tuple(card.slug for card in cards) != CARD_SLUG_ORDER
        ):
            raise IncompleteStoryError("The renderer must return exactly six cards.")

        progress.progress(100, text="Your Wrapped is complete")
        status.update(
            label="Your Wrapped is ready.",
            state="complete",
            expanded=False,
        )
        set_result(st.session_state, stats, cards)
        st.rerun()
        return
    except Exception as exc:  # noqa: BLE001 - all failures become safe UI state
        logging.exception("Wrapped generation failed for username %r", username)
        set_error(st.session_state, map_exception(exc))
        if status is not None:
            try:
                status.update(
                    label="The analysis was interrupted.",
                    state="error",
                    expanded=True,
                )
            except Exception:  # noqa: BLE001 - error state must still rerun safely
                logging.exception("Failed to update the interrupted status UI")
        st.rerun()
        return


def _render_result_stage() -> None:
    try:
        cards = st.session_state["wrapped_cards"]
    except KeyError:
        cards = ()
    result_payload = cards or st.session_state["image_bytes"]
    coverage_note = st.session_state.get("coverage_note")
    if render_result(st.session_state["stats"], result_payload, coverage_note):
        reset_generation(st.session_state)
        st.rerun()


def _render_error_stage() -> None:
    error = st.session_state["ui_error"]
    render_error(error)

    # Offering only a retry would strand anyone whose failure a retry cannot
    # fix, such as a host-level Letterboxd block.
    csv_recovery = bool(getattr(error, "allow_csv_recovery", False))
    if csv_recovery:
        csv_submission = render_csv_uploader_form(form_key="csv_recovery_form")
        if csv_submission is not None:
            _start_csv_generation(csv_submission)
            return

    restart = st.button(
        "Start Over" if csv_recovery else "Try Again",
        width="stretch",
    )
    render_footer()
    if restart:
        reset_generation(st.session_state)
        st.rerun()


def render_current_stage() -> None:
    """Render exactly one stage from the current per-session state."""
    stage = st.session_state["stage"]
    if stage == "landing":
        _render_landing()
    elif stage == "generating":
        _run_generation()
    elif stage == "result":
        _render_result_stage()
    elif stage == "error":
        _render_error_stage()


def main() -> None:
    load_styles()
    initialize_state(st.session_state)
    render_header()
    render_current_stage()


if __name__ == "__main__":
    main()
