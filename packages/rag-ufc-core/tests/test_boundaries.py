"""The core depends on nothing above it and never wires experimental strategies in."""
import ast
from pathlib import Path
import re
import subprocess
import sys

import rag_ufc_core
from rag_ufc_core.strategies import STRATEGIES, application_pipeline_modules, experimental_modules

SOURCE = Path(rag_ufc_core.__file__).resolve().parent
FORBIDDEN_IMPORTS = ("streamlit", "fastapi", "presentation", "benchmark", "service", "application", "llm_client")


def python_files():
    return sorted(p for p in SOURCE.rglob("*.py") if "__pycache__" not in p.parts)


def test_core_imports_no_application_research_or_ui_modules():
    offenders = []
    for path in python_files():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            else:
                continue
            offenders += [(path.name, name) for name in names if name.split(".")[0] in FORBIDDEN_IMPORTS]
    assert not offenders


def test_core_never_escapes_its_package_with_relative_imports():
    for path in python_files():
        depth = len(path.relative_to(SOURCE).parts) - 1
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level:
                assert node.level <= depth + 1, (path, node.module)


def test_core_does_not_derive_data_paths_from_its_install_location():
    for path in python_files():
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\.parents\[\d+\]", text), path
        assert "config/config.toml" not in text.replace("``config/config.toml``", ""), path
        assert "data/collections" not in text and "data/cache" not in text, path


def test_experimental_strategies_are_not_reachable_from_the_application_pipeline():
    reachable = application_pipeline_modules()
    assert {"Engine", "Flow", "Retrieval", "Coverage", "Grounding"} <= reachable
    assert not reachable & experimental_modules()
    for name, strategy in STRATEGIES.items():
        assert strategy["status"] in {"baseline", "experimental"}, name
        if strategy["status"] == "experimental":
            assert not strategy["in_application_pipeline"]


def test_importing_the_package_and_facade_loads_no_models_or_agents():
    code = (
        "import sys, rag_ufc_core\n"
        "from rag_ufc_core import RAGService, EngineSettings, pipeline_identity\n"
        "heavy = {'crewai', 'faiss', 'torch', 'FlagEmbedding', 'sentence_transformers', 'streamlit', 'fastapi'}\n"
        "print(sorted(heavy & set(sys.modules)))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "[]"
