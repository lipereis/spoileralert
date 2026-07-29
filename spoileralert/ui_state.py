"""Deterministic per-session UI state helpers."""

from __future__ import annotations

from typing import Any, Literal, Protocol

Stage = Literal["landing", "generating", "result", "error"]


class SessionLike(Protocol):
    """Structural stand-in for `st.session_state`.

    `SessionStateProxy` isn't a `MutableMapping[str, Any]` under strict
    typing (its key type is wider than `str`), so this protocol only
    demands the exact operations these helpers use.
    """

    def __setitem__(self, key: str, value: Any, /) -> None: ...
    def __getitem__(self, key: str, /) -> Any: ...
    def setdefault(self, key: str, default: Any, /) -> Any: ...

DEFAULT_STATE: dict[str, Any] = {
    "stage": "landing",
    "username": "",
    "stats": None,
    "image_bytes": None,
    "ui_error": None,
    "wrapped_cards": (),
    "selected_card_index": 0,
    "diary_csv_bytes": None,
}


def initialize_state(state: SessionLike) -> None:
    """Add missing UI-state values without changing existing session data."""
    for key, value in DEFAULT_STATE.items():
        state.setdefault(key, value)


def begin_generation(
    state: SessionLike, username: str, diary_csv_bytes: bytes | None = None
) -> None:
    """Start a fresh generation attempt for a normalized username.

    `diary_csv_bytes`, when provided, routes generation through an
    uploaded Letterboxd diary export instead of live scraping.
    """
    state["stage"] = "generating"
    state["username"] = username.strip().lstrip("@")
    state["stats"] = None
    state["image_bytes"] = None
    state["ui_error"] = None
    state["wrapped_cards"] = ()
    state["selected_card_index"] = 0
    state["diary_csv_bytes"] = diary_csv_bytes


def set_result(state: SessionLike, stats: Any, cards: Any) -> None:
    """Store a complete legacy image or immutable enhanced card result."""
    state["stage"] = "result"
    state["stats"] = stats
    if isinstance(cards, bytes):
        state["image_bytes"] = cards
        state["wrapped_cards"] = ()
    else:
        state["image_bytes"] = None
        state["wrapped_cards"] = tuple(cards)
    state["selected_card_index"] = 0
    state["ui_error"] = None


def set_error(state: SessionLike, error: Any) -> None:
    """Store a safe UI error and discard any incomplete result."""
    state["stage"] = "error"
    state["stats"] = None
    state["image_bytes"] = None
    state["wrapped_cards"] = ()
    state["selected_card_index"] = 0
    state["ui_error"] = error


def _card_count(state: SessionLike) -> int:
    try:
        return len(state["wrapped_cards"])
    except (KeyError, TypeError):
        return 0


def _selected_index(state: SessionLike) -> int:
    try:
        return int(state["selected_card_index"])
    except (KeyError, TypeError, ValueError):
        return 0


def select_previous_card(state: SessionLike) -> None:
    """Move one card backward without escaping the available range."""
    count = _card_count(state)
    if count == 0:
        state["selected_card_index"] = 0
        return
    state["selected_card_index"] = max(0, min(_selected_index(state) - 1, count - 1))


def select_next_card(state: SessionLike) -> None:
    """Move one card forward without escaping the available range."""
    count = _card_count(state)
    if count == 0:
        state["selected_card_index"] = 0
        return
    state["selected_card_index"] = max(0, min(_selected_index(state) + 1, count - 1))


def reset_generation(state: SessionLike) -> None:
    """Restore the exact initial UI-state defaults."""
    for key, value in DEFAULT_STATE.items():
        state[key] = value
