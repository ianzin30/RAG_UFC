"""Streamlit bootstrap for the local RAG application."""

from service.runtime_config import load_project_environment


load_project_environment()

from presentation.app_shell.page import render_application


def main() -> None:
    render_application()


if __name__ == "__main__":
    main()
