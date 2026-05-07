"""Import/bootstrap helpers for the standalone benchmark runner."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = PROJECT_ROOT / "application"


def bootstrap_python_path() -> None:
    for path in (PROJECT_ROOT, APPLICATION_ROOT):
        compact = str(path)
        if compact in sys.path:
            continue
        sys.path.insert(0, compact)


def get_runtime_config():
    bootstrap_python_path()
    from service.RuntimeConfig import get_runtime_config as runtime_loader

    return runtime_loader()


def get_rag_service_class():
    bootstrap_python_path()
    from service.rag.RagService import RAGService

    return RAGService


def get_retrieval_mode_command() -> str:
    bootstrap_python_path()
    from service.rag.Constants import MODE_SWITCH_TO_RETRIEVAL_COMMAND

    return MODE_SWITCH_TO_RETRIEVAL_COMMAND
