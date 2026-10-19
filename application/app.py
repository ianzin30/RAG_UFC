"""Streamlit bootstrap for the local RAG application."""

import logging
import warnings

# Suppress noisy __path__ alias warnings emitted by transformers' lazy-loader.
logging.getLogger("transformers").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=r"Accessing `__path__`")

from service.RuntimeConfig import load_project_environment, _read_config_document


load_project_environment()

import streamlit as st

from presentation.Page import render_application
from presentation.integrations.GoogleDrive import handle_google_drive_oauth_callback
from presentation.shared.Config import LOGO_PATH
from presentation.shared.Styles import apply_global_styles
from presentation.shared.Theme import get_active_theme_name


def main() -> None:
    page = _read_config_document().get("streamlit", {}).get("page", {})
    st.set_page_config(
        page_title=page.get("title", "RAG Treino"),
        page_icon=str(LOGO_PATH),
        layout=page.get("layout", "wide"),
    )
    apply_global_styles(get_active_theme_name())

    if handle_google_drive_oauth_callback():
        return

    try:
        render_application()
    except ValueError as exc:
        from service.RuntimeConfig import RuntimeConfigurationError
        st.error(str(exc) if isinstance(exc, RuntimeConfigurationError) else "Configuração inválida. Confira config/config.toml e reinicie o Streamlit.")


if __name__ == "__main__":
    main()
