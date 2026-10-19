from types import SimpleNamespace
from application.service.rag.v2.Config import V2Config
from application.service.rag.v2.Flow import RAGFlow
from application.service.rag.v2.Models import Chunk


class Tokenizer:
    def encode(self, text, **kwargs):
        return text.split()


class Retriever:
    def __init__(self):
        self.chunks = [
            Chunk(
                chunk_id="a",
                parent_id="pa",
                document_id="a",
                document_name="A",
                text="Atlas tem código ZX-741",
            ),
            Chunk(
                chunk_id="b",
                parent_id="pb",
                document_id="b",
                document_name="B",
                text="ZX-741 é financiado por Aurora",
            ),
        ]
        self.queries = []

    def search(self, query, scope, hop):
        self.queries.append((query, scope))
        i = 1 if "ZX-741" in query else 0
        return [
            {
                "position": i,
                "chunk_id": self.chunks[i].chunk_id,
                "dense_rank": 1,
                "sparse_rank": 1,
                "rrf_score": 0.02,
                "reranker_score": 2.0,
            }
        ], {"hop_id": hop, "query": query, "stages": {}}


class Team:
    def __init__(self, invalid=False, repeat=False):
        self.roles = []
        self.invalid, self.repeat = invalid, repeat
        self.registry = SimpleNamespace(generate=lambda *args: "oi")

    def run(self, role, instruction, payload, schema):
        self.roles.append(role)
        if role == "planner":
            data = {
                "resolved_question": "Quem financiou Atlas?",
                "requires_multi_hop": True,
                "initial_queries": ["Atlas"],
            }
        elif role == "reasoning":
            data = {
                "sufficient": len(payload["evidence"]) > 1,
                "missing_facts": ["financiador"],
                "established_facts": [
                    {"text": "código ZX-741", "evidence_ids": ["E1"]}
                ],
            }
        elif role == "research":
            data = {"queries": ["Atlas" if self.repeat else "ZX-741 financiador"]}
        elif role == "answer":
            data = {
                "claims": [
                    {
                        "claim_id": "C1",
                        "text": "Aurora financia Atlas.",
                        "evidence_ids": ["E999"] if self.invalid else ["E1", "E2"],
                        "requirement_ids": ["R1"],
                    }
                ]
            }
        else:
            data = {
                "claims": [
                    {
                        "claim_id": item["claim_id"],
                        "status": "SUPPORTED",
                        "reason": "ambos os trechos",
                        "support_quotes": [
                            {
                                "evidence_id": eid,
                                "quote": next(
                                    e["text"]
                                    for e in payload["evidence"]
                                    if e["evidence_id"] == eid
                                ),
                            }
                            for eid in item["evidence_ids"]
                        ],
                    }
                    for item in payload["claims"]
                ],
                "central_question_supported": True,
                "coverage": [
                    {
                        "requirement_id": "R1",
                        "claim_ids": [item["claim_id"] for item in payload["claims"]],
                        "covered": bool(payload["claims"]),
                    }
                ],
            }
        return schema.model_validate(data)


def build(team):
    retriever = Retriever()
    flow = RAGFlow(
        team,
        retriever,
        {"pa": retriever.chunks[0].text, "pb": retriever.chunks[1].text},
        [{"document_id": "a"}, {"document_id": "b"}],
        V2Config(),
        Tokenizer(),
    )
    flow.state.original_question = "Quem financiou Atlas?"
    return flow


def test_shared_state_discovers_second_query_and_evidence():
    team = Team()
    flow = build(team)
    state = flow.kickoff()
    assert state.current_hop == 2
    assert state.stop_reason == "evidence_sufficient"
    assert state.status == "answered"
    assert "[E1] [E2]" in state.final_answer
    assert any(query == "ZX-741 financiador" for query, _ in flow.retriever.queries)
    assert "research" in team.roles and "verification" in team.roles


def test_unknown_evidence_is_never_accepted_even_if_verifier_says_supported():
    state = build(Team(invalid=True)).kickoff()
    assert state.status == "abstained"
    assert state.repair_count == 1
    assert state.claims == []


def test_repeated_query_stops_without_infinite_loop():
    flow = build(Team(repeat=True))
    state = flow.kickoff()
    assert state.stop_reason == "repeated_query"
    assert len(flow.retriever.queries) == 2
    assert len({query for query, _ in flow.retriever.queries}) == 2


def test_inferred_multi_document_plan_does_not_exclude_collection():
    class MultiTeam(Team):
        def run(self, role, instruction, payload, schema):
            value = super().run(role, instruction, payload, schema)
            if role == "planner":
                value.scope.kind = "explicit_multi_document"
                value.scope.document_ids = ["a", "b"]
            return value

    flow = build(MultiTeam())
    state = flow.kickoff()
    assert state.status != "clarification_required"
    assert all(scope is None for _, scope in flow.retriever.queries)


def test_real_ambiguity_stops_before_retrieval():
    class AmbiguousTeam(Team):
        def run(self, role, instruction, payload, schema):
            result = super().run(role, instruction, payload, schema)
            result.scope.kind = "ambiguous_document"
            result.clarification = "Qual ata?"
            return result

    flow = build(AmbiguousTeam())
    state = flow.kickoff()
    assert state.final_answer == "Qual ata?"
    assert state.status == "clarification_required"
    assert flow.retriever.queries == []


def test_source_focus_is_literal_and_does_not_change_verified_answer():
    class FocusTeam(Team):
        def run(self, role, instruction, payload, schema):
            if role == "source_focus":
                return schema.model_validate(
                    {
                        "selections": [
                            {
                                "claim_id": "B0C1",
                                "evidence_id": "E2",
                                "quote": "financiado por Aurora",
                            }
                        ]
                    }
                )
            return super().run(role, instruction, payload, schema)

    state = build(FocusTeam()).kickoff()
    assert state.status == "answered"
    assert state.source_focus_status["E2"] == "focused"
    assert state.source_focus["E2"][0]["quote"] == "financiado por Aurora"


def test_casual_route_uses_provider_without_retrieval():
    class CasualTeam(Team):
        def run(self, role, instruction, payload, schema):
            plan = super().run(role, instruction, payload, schema)
            plan.route = "casual"
            return plan

    flow = build(CasualTeam())
    state = flow.kickoff()
    assert state.status == "casual"
    assert state.final_answer == "oi"
    assert flow.retriever.queries == []
    assert state.evidence == [] and state.claims == []


def test_followup_history_reaches_planner_and_resolves_question():
    captured = {}

    class FollowupTeam(Team):
        def run(self, role, instruction, payload, schema):
            if role == "planner":
                captured.update(payload)
            return super().run(role, instruction, payload, schema)

    flow = build(FollowupTeam())
    flow.state.original_question = "E quem financiou?"
    flow.state.history = [{"role": "user", "content": "Fale sobre Atlas"}]
    state = flow.kickoff()
    assert [dict(item) for item in captured["history"]] == [
        {"role": "user", "content": "Fale sobre Atlas"}
    ]
    assert captured["question"] == "E quem financiou?"
    assert state.plan.resolved_question == "Quem financiou Atlas?"
