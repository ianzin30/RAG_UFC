from types import SimpleNamespace

import application.service.rag.parts.Bootstrap as BootstrapModule
from application.service.rag.parts.Bootstrap import RAGServiceBootstrapMixin


class FakeOllamaClient:
    def __init__(self, *, api_key, model_name, api_url, generation_options=None):
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = api_url
        self.generation_options = dict(generation_options or {})

    def invoke(self, prompt):
        return "ok"


class BootstrapHarness(RAGServiceBootstrapMixin):
    def _build_prompt_chains(self) -> None:
        self.build_count += 1
        self.answer_chain = object()
        self.small_talk_chain = object()
        self.query_rewrite_chain = object()


def build_harness() -> BootstrapHarness:
    harness = object.__new__(BootstrapHarness)
    harness.api_key = "key"
    harness.api_url = "http://example.test/ollama"
    harness.default_model_name = "phi4:latest"
    harness.model_name = ""
    harness.answer_chain = None
    harness.small_talk_chain = None
    harness.query_rewrite_chain = None
    harness.agent_mode = "crewai"
    harness.crewai_available = False
    harness.crewai_llm = None
    harness.generation_config = SimpleNamespace(
        temperature=0.2,
        top_p=0.9,
        repeat_penalty=1.05,
        seed=None,
        num_ctx=None,
    )
    harness.build_count = 0
    return harness


def test_set_model_updates_ufc_client_model(monkeypatch) -> None:
    monkeypatch.setattr(BootstrapModule, "UFCOllamaClient", FakeOllamaClient)
    harness = build_harness()

    harness.set_model("qwen3:14b", rebuild_crewai_agents=False)

    assert harness.model_name == "qwen3:14b"
    assert harness.llm_client.model_name == "qwen3:14b"
    assert harness.build_count == 1


def test_repeated_set_model_with_same_model_skips_rebuild(monkeypatch) -> None:
    monkeypatch.setattr(BootstrapModule, "UFCOllamaClient", FakeOllamaClient)
    harness = build_harness()

    harness.set_model("qwen3:14b", rebuild_crewai_agents=False)
    harness.set_model("qwen3:14b")

    assert harness.build_count == 1


def test_crewai_agents_use_active_model_not_default(monkeypatch) -> None:
    captured = {}

    def fake_build_crewai_llm(*, api_key, model_name, api_url):
        captured["model_name"] = model_name
        return object()

    def fake_build_crewai_agent_bundle(agent_mode, llm):
        return SimpleNamespace(
            available=True,
            router_agent="router",
            casual_agent="casual",
            retrieval_agent="retrieval",
            scope_agent="scope",
            document_selection_agent="document_selection",
            evidence_planning_agent="evidence_planning",
            benchmark_grading_agent="benchmark_grading",
        )

    monkeypatch.setattr(BootstrapModule, "build_crewai_llm", fake_build_crewai_llm)
    monkeypatch.setattr(BootstrapModule, "build_crewai_agent_bundle", fake_build_crewai_agent_bundle)
    harness = build_harness()
    harness.model_name = "deepseek-r1:14b"

    harness._initialize_crewai_agents()

    assert captured["model_name"] == "deepseek-r1:14b"
    assert harness.crewai_available is True
    assert harness.crewai_router_agent == "router"
