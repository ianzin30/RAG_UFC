from application.service.rag.modules.retrieval.Agents import RetrievalAgentMixin


class FakeSmallTalkChain:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        return self.response


class CasualCleaningHarness(RetrievalAgentMixin):
    def __init__(self, response: str = "") -> None:
        self.crewai_available = False
        self.crewai_casual_agent = None
        self.small_talk_chain = FakeSmallTalkChain(response)


def test_clean_casual_response_removes_specific_help_footer() -> None:
    harness = CasualCleaningHarness()

    cleaned = harness._clean_casual_response(
        "Oi! Tudo certo por aqui. Se houver algo específico em que possa ser útil, "
        "não hesite em perguntar!"
    )

    assert cleaned == "Oi! Tudo certo por aqui"


def test_clean_casual_response_removes_disposition_footer() -> None:
    harness = CasualCleaningHarness()

    cleaned = harness._clean_casual_response("Claro, posso conversar com voce. Estou à disposição para ajudar.")

    assert cleaned == "Claro, posso conversar com voce"


def test_clean_casual_response_removes_attached_emoji_signoff() -> None:
    harness = CasualCleaningHarness()

    cleaned = harness._clean_casual_response("Tudo bem! Estou a disposicao para ajudar. 🌟")

    assert cleaned == "Tudo bem"


def test_clean_casual_response_preserves_normal_content() -> None:
    harness = CasualCleaningHarness()

    cleaned = harness._clean_casual_response("Posso explicar isso em poucas palavras.")

    assert cleaned == "Posso explicar isso em poucas palavras."


def test_invoke_casual_agent_cleans_small_talk_chain_output() -> None:
    harness = CasualCleaningHarness(
        "Oi! Eu sou o assistente do chat. Se precisar de algo, estou à disposição para ajudar."
    )

    answer = harness._invoke_casual_agent(
        collection_name="colecao",
        history_text="Sem conversa anterior.",
        question="oi",
    )

    assert answer == "Oi! Eu sou o assistente do chat"
    assert harness.small_talk_chain.calls == [
        {
            "collection_name": "colecao",
            "chat_history": "Sem conversa anterior.",
            "question": "oi",
        }
    ]
