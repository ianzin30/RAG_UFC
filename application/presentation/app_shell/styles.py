"""Style loader for the Streamlit shell."""

from pathlib import Path

import streamlit as st

from .theme import build_theme_variables_css

APP_CSS_PATH = Path(__file__).resolve().parents[2] / "assets" / "app.css"


def apply_global_styles(theme_name: str) -> None:
    css = APP_CSS_PATH.read_text(encoding="utf-8")
    theme_css = build_theme_variables_css(theme_name)
    st.markdown(f"<style>{theme_css}\n{css}</style>", unsafe_allow_html=True)
