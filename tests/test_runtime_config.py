import pytest
from application.service import RuntimeConfig
from application.service.rag.v2.Config import load_settings


@pytest.fixture(autouse=True)
def fresh_runtime_config():
    RuntimeConfig.reset_runtime_config_cache()
    yield
    RuntimeConfig.reset_runtime_config_cache()


def document(provider="vllm", model="Qwen/Qwen2.5-7B-Instruct-AWQ"):
    return {"llm": {"provider": provider, "model": model}, "rag_v2": {"device": "cpu"}}


def test_llm_is_only_default_model_authority(monkeypatch):
    payload = document()
    payload["model"] = {"ufc_model_name": "obsolete"}
    monkeypatch.setattr(RuntimeConfig, "_read_config_document", lambda: payload)
    runtime = RuntimeConfig.get_runtime_config()
    llm, config = load_settings()
    assert runtime.llm_model == llm.model == payload["llm"]["model"]
    assert runtime.ufc_model_name == runtime.llm_model
    assert runtime.llm_provider == "vllm"
    assert config.device == "cpu"


def test_local_selector_only_exposes_logical_local_models(monkeypatch):
    monkeypatch.setattr(RuntimeConfig, "_read_config_document",
                        lambda: document("ollama", "phi4:latest"))
    assert [option.model_name for option in RuntimeConfig.get_runtime_config().llm_model_options] == [
        "phi4:latest", "qwen3.5"
    ]


def test_physical_ollama_tag_belongs_in_adapter_config(monkeypatch):
    monkeypatch.setattr(RuntimeConfig, "_read_config_document",
                        lambda: document("ollama", "qwen3.5:9b"))
    with pytest.raises(ValueError, match="logical local model"):
        RuntimeConfig.get_runtime_config()


def test_disabled_v2_does_not_activate_legacy(monkeypatch):
    payload = document()
    payload["rag_v2"]["enabled"] = False
    monkeypatch.setattr(RuntimeConfig, "_read_config_document", lambda: payload)
    with pytest.raises(ValueError, match="only RAG V2"):
        load_settings()


def test_provider_switch_preserves_document_configuration(monkeypatch):
    payload = document()
    monkeypatch.setattr(RuntimeConfig, "_read_config_document", lambda: payload)
    _, original = load_settings()
    payload["llm"] = {"provider": "ollama", "model": "phi4:latest"}
    _, changed = load_settings()
    assert changed == original
