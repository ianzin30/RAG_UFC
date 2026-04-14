"""Streamlit bootstrap for the local RAG application."""

from pathlib import Path

from dotenv import load_dotenv

from presentation.app_shell.page import render_application


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def main() -> None:
    render_application()


if __name__ == "__main__":
    main()
