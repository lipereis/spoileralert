"""Native Streamlit controls for starting and presenting generation."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_sample_button() -> bool:
    """Render the zero-input demo entry point and report a click.

    Nobody should need a Letterboxd account, an export, or an unblocked host
    to see what this app produces.
    """
    st.markdown(
        """
      <section class="generator-panel__intro">
        <p class="generator-panel__eyebrow">START HERE</p>
        <h2>See it in one click.</h2>
        <p>Generate the complete six-card story from a sample diary. No account,
        no export, nothing to install.</p>
      </section>
        """,
        unsafe_allow_html=True,
    )
    return st.button(
        "See a sample Wrapped",
        width="stretch",
    )


def render_generator_form() -> str | None:
    """Render the public-profile form and return input only on submission."""
    with st.form("generator_form", clear_on_submit=False):
        st.markdown(
            """
          <section class="generator-panel__intro">
            <p class="generator-panel__eyebrow">YOUR DIARY, DIRECTED</p>
            <h2>Ready for your close-up?</h2>
            <p>Enter a public Letterboxd username to turn this year's complete diary into a cinematic story.</p>
            <p>Reading a live profile needs a host Letterboxd is willing to answer.
            It works when you run SpoilerAlert on your own machine, but shared cloud
            addresses are often refused — use the diary export above there.</p>
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


def render_csv_uploader_form(
    *,
    expanded: bool = True,
    form_key: str = "csv_generator_form",
) -> tuple[str, bytes] | None:
    """Render the diary-export form and return (username, csv bytes) only
    once a file has been submitted.

    This path never talks to Letterboxd, so it keeps working even when a
    hosting provider's shared IP is blocked by Letterboxd's anti-bot
    protection. `form_key` keeps the landing and error copies of this form
    distinct.
    """
    with st.expander(
        "Use your own diary — upload your Letterboxd export",
        expanded=expanded,
    ):
        with st.form(form_key, clear_on_submit=False):
            st.markdown(
                """
              <section class="generator-panel__intro">
                <p>Export your data from Letterboxd's
                <strong>Settings → Import &amp; Export</strong> page, then upload
                the <code>diary.csv</code> file from the downloaded ZIP here.</p>
                <p>This reads the file here and never contacts Letterboxd, so it
                is the dependable route — it works even when Letterboxd refuses
                requests from this server.</p>
              </section>
                """,
                unsafe_allow_html=True,
            )
            display_name = st.text_input(
                "Display name (optional)",
                placeholder="e.g. nmcassa",
            )
            uploaded_file = st.file_uploader(
                "diary.csv",
                type=["csv"],
            )
            submitted = st.form_submit_button(
                "Generate My Wrapped from CSV",
                width="stretch",
            )
        if submitted and uploaded_file is None:
            st.warning("Choose a diary.csv file before submitting.")

    if not submitted or uploaded_file is None:
        return None
    return display_name, uploaded_file.getvalue()


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
