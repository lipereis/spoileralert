"""Native Streamlit controls for starting and presenting generation."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_generator_form() -> str | None:
    """Render the public-profile form and return input only on submission."""
    with st.form("generator_form", clear_on_submit=False):
        st.markdown(
            """
          <section class="generator-panel__intro">
            <p class="generator-panel__eyebrow">YOUR DIARY, DIRECTED</p>
            <h2>Ready for your close-up?</h2>
            <p>Enter a public Letterboxd username to turn this year's complete diary into a cinematic story.</p>
          </section>
            """,
            unsafe_allow_html=True,
        )
        username = st.text_input(
            "Letterboxd username",
            placeholder="e.g. nmcassa",
            autocomplete="username",
        )
        submitted = st.form_submit_button(
            "Generate My Wrapped",
            width="stretch",
        )
        st.markdown(
            """
          <p class="generator-panel__trust">
            <span aria-hidden="true">●</span>
            Only public Letterboxd profile information is analyzed. Your data is not permanently stored.
          </p>
            """,
            unsafe_allow_html=True,
        )
    return username if submitted else None


def render_loading_shell() -> tuple[Any, Any]:
    """Render stable primitives for the real four-operation pipeline."""
    st.markdown(
        """
        <section class="loading-shell" aria-labelledby="loading-title">
          <p class="loading-shell__eyebrow">NOW SCREENING</p>
          <h1 id="loading-title">Your Wrapped is in the editing room.</h1>
          <p>We are reading the complete year, checking optional film details, and shaping six story cards.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    status = st.status("Opening your complete Letterboxd diary…", expanded=True)
    progress = st.progress(0, text="Preparing the complete-year analysis")
    return status, progress
