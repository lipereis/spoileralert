"""Safe, user-facing error presentation for the Streamlit app."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

import streamlit as st

from spoileralert.data import (
    BlockedError,
    EmptyDiaryError,
    InvalidCsvError,
    NetworkError,
    ProfileNotFoundError,
)


@dataclass(frozen=True)
class UiError:
    title: str
    message: str
    action: str
    allow_csv_recovery: bool = False
    """Whether uploading a diary export can succeed where this attempt failed.

    Set for failures a live profile retry cannot resolve, so the error stage
    can offer the scraping-free path instead of only a doomed retry.
    """


class IncompleteStoryError(RuntimeError):
    """Raised when rendering does not produce the complete six-card story."""


def map_exception(exc: Exception) -> UiError:
    """Translate internal errors into stable, non-sensitive UI copy."""
    if isinstance(exc, IncompleteStoryError):
        return UiError(
            "The final cut is incomplete.",
            "We could not assemble all six story cards safely.",
            "Try this profile again in a moment.",
        )
    if isinstance(exc, ProfileNotFoundError):
        return UiError(
            "We could not open this diary.",
            "The username may be misspelled, private, or unavailable.",
            "Check the spelling and confirm the Letterboxd profile is public.",
        )
    if isinstance(exc, EmptyDiaryError):
        return UiError(
            "There is not enough diary activity yet.",
            "This profile has no public diary entries for the current year.",
            "Add a diary entry for this year on Letterboxd, then try again.",
        )
    if isinstance(exc, InvalidCsvError):
        return UiError(
            "That file isn't a Letterboxd diary export.",
            "We could not find the expected columns in this CSV file.",
            "Export diary.csv from Letterboxd's Settings \u2192 Import & Export page, then upload it here.",
            allow_csv_recovery=True,
        )
    if isinstance(exc, BlockedError):
        return UiError(
            "Letterboxd blocked this server.",
            "Letterboxd's anti-bot protection is blocking requests from this "
            "hosting provider's shared IP address, not from your account.",
            "Retrying will not help, but uploading your diary export will: "
            "get diary.csv from Letterboxd's Settings \u2192 Import & Export page "
            "and upload it below for your complete Wrapped.",
            allow_csv_recovery=True,
        )
    if isinstance(exc, (NetworkError, ConnectionError, TimeoutError)):
        return UiError(
            "Letterboxd is taking a break.",
            "We could not reach the profile service right now.",
            "Wait a moment and try the same username again.",
        )
    return UiError(
        "The reel stopped unexpectedly.",
        "We could not finish this Wrapped safely.",
        "Try again. If the problem continues, use another public profile.",
    )


def render_error(error: UiError) -> None:
    """Render one application-owned, escaped live error panel."""
    markup = (
        '<section class="error-panel" aria-live="polite">'
        '<p class="error-panel__eyebrow">ANALYSIS INTERRUPTED</p>'
        f"<h1>{escape(error.title)}</h1>"
        f"<p>{escape(error.message)}</p>"
        f'<p class="error-panel__action">{escape(error.action)}</p>'
        "</section>"
    )
    st.markdown(markup, unsafe_allow_html=True)
