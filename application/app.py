"""Streamlit bootstrap for the local RAG application."""

import logging
import warnings

# Suppress noisy __path__ alias warnings emitted by transformers' lazy-loader.
logging.getLogger("transformers").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=r"Accessing `__path__`")

from service.RuntimeConfig import load_project_environment


load_project_environment()

from presentation.Page import render_application
from presentation.auth.LoginGate import require_authenticated_user


def main() -> None:
    user = require_authenticated_user()
    if user is None and _firebase_enabled():
        return  # login gate already called st.stop()
    render_application()


def _firebase_enabled() -> bool:
    try:
        from service.RuntimeConfig import get_runtime_config
        return get_runtime_config().firebase.enabled
    except Exception:
        return False


if __name__ == "__main__":
    main()
