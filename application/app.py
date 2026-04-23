"""Streamlit bootstrap for the local RAG application."""

import logging
import warnings

# Suppress noisy __path__ alias warnings emitted by transformers' lazy-loader.
logging.getLogger("transformers").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=r"Accessing `__path__`")

from service.RuntimeConfig import load_project_environment


load_project_environment()

from presentation.Page import render_application


def main() -> None:
    render_application()


if __name__ == "__main__":
    main()
