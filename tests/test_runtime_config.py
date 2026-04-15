import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPLICATION_ROOT = PROJECT_ROOT / "application"
for path in (PROJECT_ROOT, APPLICATION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from application.service import runtime_config as runtime_config_module


def test_runtime_config_reads_toml_sections(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "\n".join(
            [
                "[model]",
                'ufc_model_name = "llama3.1:8b"',
                "",
                "[embeddings]",
                'model_name = "BAAI/bge-m3"',
                'device = "cuda"',
                'quantization = "4bit"',
                "batch_size = 2",
                "max_length = 1024",
                "",
                "[splitter]",
                "chunk_size = 600",
                "chunk_overlap = 120",
                'separators = ["\\n\\n", "\\n", ". ", " "]',
                "",
                "[retrieval]",
                "base_search_k = 7",
                "base_fetch_k = 35",
                "base_lambda_mult = 0.25",
                "focused_search_k = 8",
                "focused_fetch_k = 90",
                "focused_lambda_mult = 0.15",
                "lexical_limit = 14",
                "coverage_limit = 11",
                "context_default_limit = 7",
                "context_diverse_limit = 9",
                "context_summary_limit = 5",
                "",
                "[aggregation]",
                "topics_limit = 11",
                "names_limit = 20",
                "list_extraction_names_limit = 70",
                "dates_limit = 9",
                "money_values_limit = 8",
                "fact_lines_limit = 13",
                "key_points_limit = 6",
                "",
                "[rag]",
                'agent_mode = "crewai"',
                "strict_grounding = true",
                "min_evidence_score = 0.22",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(runtime_config_module, "CONFIG_FILE", config_file)
    runtime_config_module.reset_runtime_config_cache()

    config = runtime_config_module.get_runtime_config()

    assert config.ufc_model_name == "llama3.1:8b"
    assert config.embedding.model_name == "BAAI/bge-m3"
    assert config.embedding.device == "cuda"
    assert config.embedding.quantization == "4bit"
    assert config.embedding.batch_size == 2
    assert config.embedding.max_length == 1024
    assert config.splitter.chunk_size == 600
    assert config.splitter.chunk_overlap == 120
    assert config.splitter.separators == ("\n\n", "\n", ". ", " ")
    assert config.retrieval.base_search_k == 7
    assert config.retrieval.focused_fetch_k == 90
    assert config.retrieval.context_summary_limit == 5
    assert config.aggregation.topics_limit == 11
    assert config.aggregation.list_extraction_names_limit == 70
    assert config.rag.agent_mode == "crewai"
    assert config.rag.strict_grounding is True
    assert config.rag.min_evidence_score == pytest.approx(0.22)

    runtime_config_module.reset_runtime_config_cache()


def test_runtime_config_rejects_unsupported_quantization(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "\n".join(
            [
                "[model]",
                'ufc_model_name = "llama3.1:8b"',
                "",
                "[embeddings]",
                'model_name = "BAAI/bge-m3"',
                'device = "cuda"',
                'quantization = "8bit"',
                "batch_size = 2",
                "max_length = 1024",
                "",
                "[splitter]",
                "chunk_size = 500",
                "chunk_overlap = 100",
                'separators = ["\\n\\n", "\\n", ". ", " "]',
                "",
                "[retrieval]",
                "base_search_k = 6",
                "base_fetch_k = 30",
                "base_lambda_mult = 0.2",
                "focused_search_k = 6",
                "focused_fetch_k = 100",
                "focused_lambda_mult = 0.2",
                "lexical_limit = 12",
                "coverage_limit = 10",
                "context_default_limit = 6",
                "context_diverse_limit = 8",
                "context_summary_limit = 6",
                "",
                "[aggregation]",
                "topics_limit = 10",
                "names_limit = 24",
                "list_extraction_names_limit = 80",
                "dates_limit = 12",
                "money_values_limit = 12",
                "fact_lines_limit = 14",
                "key_points_limit = 10",
                "",
                "[rag]",
                'agent_mode = "crewai"',
                "strict_grounding = true",
                "min_evidence_score = 0.22",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(runtime_config_module, "CONFIG_FILE", config_file)
    runtime_config_module.reset_runtime_config_cache()

    with pytest.raises(RuntimeError, match="Unsupported embedding quantization"):
        runtime_config_module.get_runtime_config()

    runtime_config_module.reset_runtime_config_cache()
