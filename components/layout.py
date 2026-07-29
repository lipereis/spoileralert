"""Reusable, fixed-copy layout components for SpoilerAlert."""

from pathlib import Path

import streamlit as st


HEADER_HTML = """
<header class="site-header">
  <div class="brand-lockup" aria-label="SpoilerAlert">
    <span class="brand-lockup__mark" aria-hidden="true"></span>
    <span class="brand-lockup__name">SpoilerAlert</span>
  </div>
  <p class="site-header__label">Your year in cinema</p>
</header>
"""

HERO_HTML = """
<section class="hero" aria-labelledby="hero-title">
  <div class="film-marks" aria-hidden="true">
    <span class="film-mark film-mark--green"></span>
    <span class="film-mark film-mark--orange"></span>
    <span class="film-mark film-mark--blue"></span>
  </div>
  <p class="hero-eyebrow">YOUR YEAR IN CINEMA</p>
  <h1 class="hero-title" id="hero-title">Discover the story behind your movie taste.</h1>
  <p class="hero-copy">Turn your Letterboxd diary into a personal, cinematic and shareable visual experience.</p>
</section>
"""

FEATURES_HTML = """
<section class="features" aria-labelledby="features-title">
  <div class="section-heading">
    <p class="section-eyebrow">BEYOND THE WATCHLIST</p>
    <h2 id="features-title">Your viewing history, with a point of view.</h2>
  </div>
  <div class="features-grid">
    <article class="feature-card">
      <span class="feature-card__number">01</span>
      <h3>Movie DNA</h3>
      <p>Discover the genres, decades and viewing patterns shaping your movie taste.</p>
    </article>
    <article class="feature-card">
      <span class="feature-card__number">02</span>
      <h3>Cinema Personality</h3>
      <p>Turn your complete current-year diary into a memorable and shareable cinephile identity.</p>
    </article>
    <article class="feature-card">
      <span class="feature-card__number">03</span>
      <h3>Story-Ready Design</h3>
      <p>Export a polished 1080×1920 visual made for social media.</p>
    </article>
  </div>
</section>
"""

FOOTER_HTML = """
<footer class="site-footer">
  <p>Built for people who see every movie as part of a bigger story.</p>
  <p class="site-footer__note">Not affiliated with Letterboxd.</p>
</footer>
"""


def load_styles() -> None:
    """Read the repository stylesheet as UTF-8 and inject one style block."""
    css_path = Path(__file__).resolve().parents[1] / "styles" / "main.css"
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_header() -> None:
    """Render the site wordmark and context label."""
    st.markdown(HEADER_HTML, unsafe_allow_html=True)


def render_hero() -> None:
    """Render the editorial landing-page hero."""
    st.markdown(HERO_HTML, unsafe_allow_html=True)


def render_features() -> None:
    """Render the three fixed product-value cards."""
    st.markdown(FEATURES_HTML, unsafe_allow_html=True)


def render_footer() -> None:
    """Render the fixed site footer."""
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)
