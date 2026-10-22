"""Research checkout on top of rag_ufc_core: legacy names, legacy paths, promotion tooling."""
import hashlib
import importlib
from pathlib import Path

import pytest

from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path

PACKAGE_SOURCE = PROJECT_ROOT / "packages/rag-ufc-core/src/rag_ufc_core"
# Track B load_source compares these legacy paths with archived code.zip members.
FROZEN_SOURCE_PATHS = [f"application/service/rag/v2/{name}.py" for name in
                       ("EvidenceSelection", "Dense", "Retrieval", "Models", "OllamaEmbeddings")]


def test_legacy_module_names_are_the_core_modules():
    bootstrap_python_path()
    for name in ("Engine", "Flow", "Config", "Retrieval", "EvidenceSelection"):
        core = importlib.import_module(f"rag_ufc_core.rag.v2.{name}")
        assert importlib.import_module(f"service.rag.v2.{name}") is core
        assert importlib.import_module(f"application.service.rag.v2.{name}") is core
        assert core.__spec__.name == f"rag_ufc_core.rag.v2.{name}"
    assert importlib.import_module("service.UfcOllama") is importlib.import_module("rag_ufc_core.UfcOllama")
    assert importlib.import_module("service.spreadsheet.Loading") is importlib.import_module("rag_ufc_core.spreadsheet.Loading")
    assert importlib.import_module("service.RuntimeConfig") is importlib.import_module("application.service.RuntimeConfig")
    import llm_client
    assert llm_client is importlib.import_module("rag_ufc_core.llm_client")
    assert llm_client.DEFAULT_ENV == PROJECT_ROOT / ".env"


def test_legacy_paths_read_the_bytes_that_run():
    for relative in FROZEN_SOURCE_PATHS:
        legacy = PROJECT_ROOT / relative
        assert legacy.is_symlink()
        assert legacy.resolve() == (PACKAGE_SOURCE / "rag/v2" / legacy.name).resolve()
    hashed = {p.relative_to(PROJECT_ROOT).as_posix() for p in (PROJECT_ROOT / "application/service").rglob("*.py")}
    assert set(FROZEN_SOURCE_PATHS) <= hashed  # reproducibility.code_files() still sees them


def test_checkout_config_is_the_default_settings_document(monkeypatch):
    from application.service import RuntimeConfig
    from rag_ufc_core.rag.v2.Config import load_settings
    from rag_ufc_core.secret_source import read_secret

    document = {"llm": {"provider": "vllm", "model": "checkout-model"}, "rag_v2": {"device": "cpu"}}
    monkeypatch.setattr(RuntimeConfig, "_read_config_document", lambda: document)
    assert load_settings()[0].model == "checkout-model"
    monkeypatch.setenv("PROMOTION_TEST_SECRET", "value")
    assert read_secret("PROMOTION_TEST_SECRET") == "value"


def test_research_facade_uses_checkout_paths(monkeypatch):
    facade = importlib.import_module("application.service.rag.RagService")

    class Engine:
        def __init__(self, owner, llm, config):
            self.owner, self.retriever = owner, None

    monkeypatch.setattr(facade, "RAGEngine", Engine)
    service = facade.RAGService()
    assert service.collections_root == PROJECT_ROOT / "data/collections"
    assert service.index_cache_root == PROJECT_ROOT / "data/cache/rag_v2"
    assert service.project_root == PROJECT_ROOT


def test_promotion_registry_manifest_and_boundaries_are_consistent():
    from benchmark.promotion import tool

    assert tool.check() == []


def test_config_identity_works_for_historical_configs(tmp_path):
    import zipfile

    from benchmark.promotion import tool

    archive = tmp_path / "code.zip"
    config = (PROJECT_ROOT / "config/config.toml").read_text().replace("context_tokens = 6000", "context_tokens = 3000")
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("config/config.toml", config)
    historical = tool.config_identity(tool.archived_config_document(archive))
    assert historical["pipeline_config"]["retrieval"]["context_tokens"] == 3000
    assert historical["pipeline_config_hash"] != tool.config_identity(tool.config_document())["pipeline_config_hash"]


def test_release_manifest_refuses_unapproved_candidates_and_unsigned_approval():
    from benchmark.promotion import tool

    common = dict(version="9.9.9", kind="improvement", decision="test", evidence=[],
                  document=tool.config_document(), evaluation_scope="pipeline", evaluation_statement="test")
    with pytest.raises(ValueError, match="not approved"):
        tool.build_manifest(status="approved", approved_by="maintainer", approved_at="2026-10-21",
                            candidates=["core.evidence_selection"], **common)
    with pytest.raises(ValueError, match="approving maintainer"):
        tool.build_manifest(status="approved", **common)


def test_source_lineage_reports_unchanged_engine_files():
    from benchmark.promotion import tool

    lineage = {row["legacy_path"]: row for row in tool.read_json(
        PROJECT_ROOT / "releases/rag-ufc-core/1.0.0.lineage.json")["files"]}
    for relative in FROZEN_SOURCE_PATHS:
        row = lineage[relative]
        assert row["identical"]
        assert row["current_sha256"] == hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()


def test_signoff_is_recorded_once_and_only_for_the_package_in_this_checkout(tmp_path, monkeypatch):
    import json
    import shutil

    from benchmark.promotion import tool

    monkeypatch.setattr(tool, "RELEASES", tmp_path)
    shutil.copy(PROJECT_ROOT / "releases/rag-ufc-core/1.0.0.json", tmp_path / "1.0.0.json")
    with pytest.raises(ValueError, match="name and a statement"):
        tool.signoff(version="1.0.0", by=" ", statement="ok")
    signed = tool.signoff(version="1.0.0", by="Maintainer", statement="Reviewed lineage and manifest.", at="2026-10-22")
    assert signed["maintainer_signoff"]["by"] == "Maintainer"
    assert signed["maintainer_signoff"]["core_source_fingerprint"] == signed["core_source_fingerprint"]
    with pytest.raises(ValueError, match="already signed"):
        tool.signoff(version="1.0.0", by="Other", statement="again")
    record = json.loads((tmp_path / "1.0.0.json").read_text())
    record.update(maintainer_signoff=None, core_source_fingerprint="0" * 64)
    (tmp_path / "1.0.0.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="differs from the release record"):
        tool.signoff(version="1.0.0", by="Maintainer", statement="ok")
