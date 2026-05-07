from application.service.rag.Constants import MODE_CASUAL, MODE_RETRIEVAL
from application.service.rag.modules.Routing import RoutingMixin
from application.service.rag.modules.TextProcessing import TextProcessingMixin


class RoutingHarness(RoutingMixin, TextProcessingMixin):
    def __init__(self, agent_payload: dict[str, object] | None = None) -> None:
        self.agent_payload = agent_payload
        self.agent_calls = 0
        self.crewai_router_agent = object()
        self.last_retrieval_focus = None
        self.pending_document_refinement = None
        self.pending_retrieval_clarification = None

    def _invoke_json_crewai_agent(self, agent, description: str, expected_output: str):
        self.agent_calls += 1
        return self.agent_payload

    def _get_pending_document_refinement(self, chat_history):
        return self.pending_document_refinement

    def _get_pending_retrieval_clarification(self):
        return self.pending_retrieval_clarification


def test_auto_route_sends_greetings_to_casual() -> None:
    harness = RoutingHarness()

    decision = harness._resolve_auto_route("Oi, tudo bem?", [])

    assert decision["mode"] == MODE_CASUAL
    assert decision["source"] == "heuristic"


def test_auto_route_sends_document_questions_to_retrieval() -> None:
    harness = RoutingHarness()

    decision = harness._resolve_auto_route("Quais documentos estao na base carregada?", [])

    assert decision["mode"] == MODE_RETRIEVAL
    assert decision["source"] == "heuristic"


def test_auto_route_sends_project_fact_questions_to_retrieval() -> None:
    harness = RoutingHarness()

    decision = harness._resolve_auto_route("Qual empresa e parceira do projeto?", [])

    assert decision["mode"] == MODE_RETRIEVAL
    assert decision["source"] == "heuristic"


def test_auto_route_forces_retrieval_for_pending_document_refinement() -> None:
    harness = RoutingHarness(agent_payload={"mode": "casual", "reason": "agent guess"})
    harness.pending_document_refinement = {
        "matched_documents": ["a.pdf", "b.pdf"],
        "resolved_question": "Qual documento?",
        "original_question": "Qual documento?",
    }

    decision = harness._resolve_auto_route("1", [{"role": "assistant", "needs_document_refinement": True}])

    assert decision["mode"] == MODE_RETRIEVAL
    assert decision["source"] == "forced_pending_selection"
    assert harness.agent_calls == 0


def test_auto_route_falls_back_when_crewai_payload_is_invalid() -> None:
    harness = RoutingHarness(agent_payload={"mode": "general", "reason": "invalid mode"})

    decision = harness._resolve_auto_route("Quem coordena o projeto?", [])

    assert decision["mode"] == MODE_RETRIEVAL
    assert decision["source"] == "heuristic"
    assert harness.agent_calls == 1


def test_auto_route_uses_valid_crewai_router_payload() -> None:
    harness = RoutingHarness(
        agent_payload={
            "mode": "casual",
            "reason": "The user asks for a general explanation.",
        }
    )

    decision = harness._resolve_auto_route("Explique de forma simples o que e RAG.", [])

    assert decision == {
        "mode": MODE_CASUAL,
        "reason": "The user asks for a general explanation.",
        "source": "crewai_router",
    }


def test_auto_route_keeps_legacy_commands_compatible_without_agent_call() -> None:
    harness = RoutingHarness(agent_payload={"mode": "casual", "reason": "agent guess"})

    decision = harness._resolve_auto_route("BUSCAR", [])

    assert decision["mode"] == MODE_RETRIEVAL
    assert decision["source"] == "legacy_command"
    assert harness.agent_calls == 0


def test_mode_response_keeps_title_and_removes_manual_footer() -> None:
    harness = RoutingHarness()

    answer = harness._format_mode_response(MODE_RETRIEVAL, "Resposta baseada nos documentos.")

    assert answer == "**RETRIEVAL**\n\nResposta baseada nos documentos."
    assert "BUSCAR" not in answer
    assert "CASUAL" not in answer.split("\n\n", 1)[1]
