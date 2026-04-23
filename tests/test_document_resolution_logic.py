from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from application.service.rag.Constants import RAG_INDEX_CACHE_VERSION
from application.service.rag.modules.DocumentResolution import DocumentResolutionMixin
from application.service.rag.modules.TextProcessing import TextProcessingMixin
from application.service.rag.modules.retrieval.Core import RetrievalCoreMixin
from application.service.rag.modules.retrieval.Evidence import RetrievalEvidenceMixin
from application.service.rag.modules.retrieval.Intents import RetrievalIntentMixin
from application.service.rag.parts.Planning import RAGServicePlanningMixin
from application.service.rag.parts.QuestionAnswering import RAGServiceQuestionAnsweringMixin


def make_registry_document(
    name: str,
    *,
    search_text: str,
    keyword_terms: list[str] | None = None,
    section_terms: list[str] | None = None,
    entity_terms: list[str] | None = None,
    fact_terms: list[str] | None = None,
    acronyms: list[str] | None = None,
    meeting_year: str | None = None,
    meeting_month: str | None = None,
) -> dict[str, object]:
    normalized = normalize_text(search_text)
    return {
        "name": name,
        "document_name": name,
        "aliases": [],
        "keyword_terms": list(keyword_terms or tokenize_text(search_text)),
        "search_text_normalized": normalized,
        "high_value_excerpt": search_text,
        "keyword_summary": search_text,
        "signal_phrases": [search_text],
        "section_terms": list(section_terms or []),
        "entity_terms": list(entity_terms or []),
        "fact_terms": list(fact_terms or []),
        "acronyms": list(acronyms or []),
        "meeting_year": meeting_year,
        "meeting_month": meeting_month,
        "meeting_kind": None,
    }


def make_doc(
    document_name: str,
    *,
    text: str,
    chunk_kind: str,
    chunk_order: int = 0,
    section_title: str | None = None,
    entity_names: list[str] | None = None,
    labeled_facts: list[str] | None = None,
    date_values: list[str] | None = None,
    money_values: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        page_content=text,
        metadata={
            "document_name": document_name,
            "chunk_kind": chunk_kind,
            "chunk_order": chunk_order,
            "section_title": section_title,
            "search_text_normalized": normalize_text(text),
            "entity_names": list(entity_names or []),
            "labeled_facts": list(labeled_facts or []),
            "date_values": list(date_values or []),
            "money_values": list(money_values or []),
        },
    )


def normalize_text(text: str) -> str:
    return " ".join(tokenize_text(text))


def tokenize_text(text: str) -> list[str]:
    harness = TextProcessingMixin()
    return harness._tokenize_search_text(text)


class ResolverHarness(DocumentResolutionMixin, RetrievalIntentMixin, TextProcessingMixin):
    def __init__(self, documents: list[dict[str, object]]) -> None:
        self.document_registry = documents
        self.document_catalog = documents


class RegistryHarness(DocumentResolutionMixin, TextProcessingMixin):
    def __init__(self) -> None:
        self.document_registry = []
        self.document_catalog = []


class RetrievalHarness(
    RetrievalCoreMixin,
    RetrievalEvidenceMixin,
    RetrievalIntentMixin,
    DocumentResolutionMixin,
    TextProcessingMixin,
):
    def __init__(self, docs: list[SimpleNamespace]) -> None:
        self._docs = list(docs)

    def _get_vector_store_documents(self) -> list[SimpleNamespace]:
        return list(self._docs)


class AnswerRepairHarness(
    RetrievalEvidenceMixin,
    RAGServiceQuestionAnsweringMixin,
    RetrievalCoreMixin,
    RetrievalIntentMixin,
    DocumentResolutionMixin,
    TextProcessingMixin,
):
    pass


class PlanningHarness(RAGServicePlanningMixin, RetrievalIntentMixin, DocumentResolutionMixin, TextProcessingMixin):
    def __init__(self, resolver_result: dict[str, object]) -> None:
        self._resolver_result = resolver_result
        self.crewai_document_selection_agent = None

    def _question_requests_collection_scope(self, question: str, resolved_question: str) -> bool:
        return False

    def _decide_focus_scope(
        self,
        question: str,
        resolved_question: str,
        locked_document_name: str | None,
    ) -> dict[str, object]:
        return {
            "focus_decision": "release_to_discovery",
            "focus_release_reason": "test_scope",
        }

    def _resolve_documents_with_agent(
        self,
        question: str,
        resolved_question: str,
        chat_history=None,
    ) -> dict[str, object]:
        return dict(self._resolver_result)

    def _build_candidate_documents_payload(self, candidate_names, score_lookup):
        return []

    def _format_chat_history(self, chat_history) -> str:
        return "Sem conversa anterior."

    def _invoke_json_crewai_agent(self, agent, description: str, expected_output: str):
        return None


@dataclass
class FakeChunk:
    page_content: str
    metadata: dict[str, object] = field(default_factory=dict)


def test_resolver_ranks_specific_project_document_above_surface_keyword_match() -> None:
    harness = ResolverHarness(
        [
            make_registry_document(
                "01-2022_Ata_de_Reuniao.pdf",
                search_text='Ata da reuniao de janeiro de 2022. Projeto "AI for Customer Support" em parceria com a Dell.',
                keyword_terms=["ai", "for", "customer", "support", "dell", "parceria", "janeiro", "2022"],
                fact_terms=["ai", "customer", "support", "dell"],
                acronyms=["AI"],
                meeting_year="2022",
                meeting_month="janeiro",
            ),
            make_registry_document(
                "RACK.pdf",
                search_text="Projeto de rack para servidores Dell e infraestrutura do laboratorio.",
                keyword_terms=["dell", "rack", "infraestrutura", "servidores", "projeto", "empresa"],
                fact_terms=["dell", "rack"],
            ),
            make_registry_document(
                "SAAR.pdf",
                search_text="Sistema SAAR com informacoes institucionais e relatorios gerais.",
                keyword_terms=["saar", "sistema", "relatorios"],
            ),
        ]
    )

    matches = harness._collect_resolver_matches(
        'Qual empresa e a parceira do projeto "AI for Customer Support"?',
        'Qual empresa e a parceira do projeto "AI for Customer Support"?',
        retrieval_intent="specific_fact",
    )

    assert matches[0]["document_name"] == "01-2022_Ata_de_Reuniao.pdf"
    assert matches[0]["score"] > matches[1]["score"]
    assert "ai for customer support" in list(matches[0].get("matched_phrases") or [])

    resolution = harness._resolve_documents_with_agent(
        'Qual empresa e a parceira do projeto "AI for Customer Support"?',
        'Qual empresa e a parceira do projeto "AI for Customer Support"?',
    )
    assert resolution["document_shortlist"] == ["01-2022_Ata_de_Reuniao.pdf"]
    assert float(resolution["resolver_confidence"] or 0.0) >= 0.8


def test_resolver_ranks_company_junior_document_above_generic_department_atas() -> None:
    harness = ResolverHarness(
        [
            make_registry_document(
                "04-2023_Ata_de_Reuniao.pdf",
                search_text="Ata de abril de 2023 sobre a empresa junior CEOS do curso de ciencia da computacao da UFC.",
                keyword_terms=["empresa", "junior", "ceos", "curso", "ciencia", "computacao", "ufc"],
                fact_terms=["empresa", "junior", "ceos"],
            ),
            make_registry_document(
                "09-2025_Ata_de_Reuniao.pdf",
                search_text="Ata do departamento com discussoes sobre o curso de ciencia da computacao da UFC.",
                keyword_terms=["departamento", "curso", "ciencia", "computacao", "ufc"],
            ),
            make_registry_document(
                "10-2025_Ata_de_Reuniao.pdf",
                search_text="Ata extraordinaria do departamento da UFC com temas administrativos do curso.",
                keyword_terms=["departamento", "curso", "ufc", "administrativo"],
            ),
        ]
    )

    matches = harness._collect_resolver_matches(
        "Qual o nome da empresa junior do curso de Ciencia da Computacao da UFC?",
        "Qual o nome da empresa junior do curso de Ciencia da Computacao da UFC?",
        retrieval_intent="entity_lookup",
    )

    assert matches[0]["document_name"] == "04-2023_Ata_de_Reuniao.pdf"
    assert matches[0]["score"] > matches[1]["score"]


def test_registry_extracts_late_project_phrase_from_section_detail() -> None:
    harness = RegistryHarness()
    entry = harness._build_document_registry_entry(
        document_name="01-2022_Ata_de_Reuniao.pdf",
        document_type="document",
        text="# 01-2022_Ata_de_Reuniao\nDocumento Type: document\nAta do departamento.\n",
        chunks=[
            FakeChunk(
                page_content=(
                    "Trecho:\n"
                    'O Prof. Pablo apresentou o projeto "AI for Customer Support" '
                    "em parceria com a empresa Dell para o atendimento."
                ),
                metadata={
                    "document_name": "01-2022_Ata_de_Reuniao.pdf",
                    "chunk_kind": "section_detail",
                    "chunk_order": 7,
                    "section_title": "Projetos",
                },
            )
        ],
    )

    assert any(
        "ai for customer support" in normalize_text(phrase)
        for phrase in list(entry.get("signal_phrases") or [])
    )
    assert "customer" in list(entry.get("keyword_terms") or [])
    assert "support" in str(entry.get("search_text_normalized") or "")


def test_planning_auto_selects_top_document_for_specific_fact_ambiguity() -> None:
    harness = PlanningHarness(
        {
            "status": "multiple_matches",
            "matched_documents": ["01-2022_Ata_de_Reuniao.pdf", "RACK.pdf"],
            "document_shortlist": ["01-2022_Ata_de_Reuniao.pdf", "RACK.pdf"],
            "resolver_candidates": ["01-2022_Ata_de_Reuniao.pdf", "RACK.pdf"],
            "matched_aliases": [],
            "document_scores": [],
            "resolver_confidence": 0.74,
        }
    )

    result = harness._plan_document_selection(
        'Qual empresa e a parceira do projeto "AI for Customer Support"?',
        'Qual empresa e a parceira do projeto "AI for Customer Support"?',
        [],
        {"scope_type": "discovery", "matched_documents": []},
        None,
    )

    assert result["status"] == "single_match"
    assert result["matched_documents"] == ["01-2022_Ata_de_Reuniao.pdf"]
    assert result["resolver_selection_mode"] == "auto_top_document"


def test_planning_keeps_explicit_multi_document_refinement() -> None:
    harness = PlanningHarness({})

    result = harness._plan_document_selection(
        "Compare os arquivos 01-2022_Ata_de_Reuniao.pdf e 04-2023_Ata_de_Reuniao.pdf",
        "Compare os arquivos 01-2022_Ata_de_Reuniao.pdf e 04-2023_Ata_de_Reuniao.pdf",
        [],
        {
            "scope_type": "explicit_document",
            "matched_documents": ["01-2022_Ata_de_Reuniao.pdf", "04-2023_Ata_de_Reuniao.pdf"],
        },
        None,
    )

    assert result["status"] == "multiple_matches"
    assert result["resolver_selection_mode"] == "explicit_reference"


def test_specific_fact_priority_favors_section_detail_with_exact_phrase_hit() -> None:
    detail_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text=(
            "O Chefe do Departamento convocou a reuniao de 14 de janeiro de 2022. "
            "Fernando Antonio Mota Trinta presidiu a abertura."
        ),
        chunk_kind="section_detail",
        chunk_order=5,
        section_title="Abertura",
    )
    entity_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text=(
            "Pessoas ou entidades: Fernando Antonio Mota Trinta; docentes do departamento; "
            "chefia do departamento."
        ),
        chunk_kind="entity_index",
        chunk_order=1,
        section_title="Entidades",
    )
    harness = RetrievalHarness([detail_doc, entity_doc])

    ranked = harness._retrieve_lexical_docs(
        "Quem era o Chefe do Departamento que convocou a reuniao de 14 de janeiro de 2022?",
        target_document_name="01-2022_Ata_de_Reuniao.pdf",
        document_shortlist=["01-2022_Ata_de_Reuniao.pdf"],
        retrieval_intent="specific_fact",
        limit=2,
    )

    assert ranked[0].metadata["chunk_kind"] == "section_detail"
    assert RAG_INDEX_CACHE_VERSION == 7


def test_document_expansion_priority_can_promote_explicit_section_detail() -> None:
    detail_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text=(
            "O Chefe do Departamento convocou a reuniao de 14 de janeiro de 2022. "
            "Fernando Antonio Mota Trinta presidiu a abertura da sessao."
        ),
        chunk_kind="section_detail",
        chunk_order=4,
        section_title="Abertura",
    )
    profile_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text="Perfil do documento. Ata da reuniao realizada em 14 de janeiro de 2022.",
        chunk_kind="document_profile",
        chunk_order=0,
        section_title="Perfil",
    )
    entity_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text="Pessoas ou entidades: Fernando Antonio Mota Trinta; chefia do departamento.",
        chunk_kind="entity_index",
        chunk_order=1,
        section_title="Entidades",
    )
    harness = RetrievalHarness([profile_doc, entity_doc, detail_doc])

    ranked = harness._prioritize_retrieved_docs(
        [profile_doc, entity_doc, detail_doc],
        target_document_name="01-2022_Ata_de_Reuniao.pdf",
        retrieval_intent="document_expansion",
        resolved_question="Quem era o Chefe do Departamento que convocou a reuniao de 14 de janeiro de 2022?",
        document_shortlist=["01-2022_Ata_de_Reuniao.pdf"],
    )

    assert ranked[0].metadata["chunk_kind"] == "section_detail"


def test_context_selection_reserves_explicit_section_detail_for_document_expansion() -> None:
    docs = [
        make_doc(
            "01-2022_Ata_de_Reuniao.pdf",
            text="Perfil do documento. Ata da reuniao realizada em 14 de janeiro de 2022.",
            chunk_kind="document_profile",
            chunk_order=0,
            section_title="Perfil",
        ),
        make_doc(
            "01-2022_Ata_de_Reuniao.pdf",
            text="Resumo da secao: abertura da reuniao e informes iniciais.",
            chunk_kind="section_overview",
            chunk_order=1,
            section_title="Abertura",
        ),
        make_doc(
            "01-2022_Ata_de_Reuniao.pdf",
            text="Pessoas ou entidades: Fernando Antonio Mota Trinta; chefia do departamento.",
            chunk_kind="entity_index",
            chunk_order=2,
            section_title="Entidades",
        ),
        make_doc(
            "01-2022_Ata_de_Reuniao.pdf",
            text=(
                "O Chefe do Departamento convocou a reuniao de 14 de janeiro de 2022. "
                "Fernando Antonio Mota Trinta presidiu a abertura da sessao."
            ),
            chunk_kind="section_detail",
            chunk_order=5,
            section_title="Abertura",
        ),
    ]
    harness = RetrievalHarness(docs)

    selected = harness._select_docs_for_context(
        docs,
        target_document_name="01-2022_Ata_de_Reuniao.pdf",
        retrieval_intent="document_expansion",
        resolved_question="Quem era o Chefe do Departamento que convocou a reuniao de 14 de janeiro de 2022?",
        document_shortlist=["01-2022_Ata_de_Reuniao.pdf"],
    )

    assert any(doc.metadata["chunk_kind"] == "section_detail" for doc in selected)


def test_fragment_only_lexical_match_does_not_beat_full_detail_hit() -> None:
    detail_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text=(
            'O projeto "AI for Customer Support" foi apresentado em parceria com a empresa Dell.'
        ),
        chunk_kind="section_detail",
        chunk_order=3,
        section_title="Projetos",
    )
    distractor_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text="Resumo da secao: projeto de atendimento ao cliente com empresa parceira.",
        chunk_kind="section_overview",
        chunk_order=1,
        section_title="Resumo",
    )
    harness = RetrievalHarness([detail_doc, distractor_doc])

    ranked = harness._retrieve_lexical_docs(
        'Qual empresa e a parceira do projeto "AI for Customer Support"?',
        target_document_name="01-2022_Ata_de_Reuniao.pdf",
        document_shortlist=["01-2022_Ata_de_Reuniao.pdf"],
        retrieval_intent="specific_fact",
        limit=2,
    )

    assert ranked[0].metadata["chunk_kind"] == "section_detail"


def test_grounded_short_answer_repair_replaces_truncated_company_name() -> None:
    harness = AnswerRepairHarness()
    detail_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text='O projeto "AI for Customer Support" ocorreu em parceria com a empresa Dell.',
        chunk_kind="section_detail",
        chunk_order=3,
        section_title="Projetos",
    )

    repaired, answer_shape, candidates, dominant, applied, reason, origin = harness._repair_grounded_short_answer(
        "Del",
        selected_docs=[detail_doc],
        retrieval_intent="specific_fact",
        resolved_question='Qual empresa e a parceira do projeto "AI for Customer Support"?',
    )

    assert repaired == "Dell"
    assert answer_shape == "person_or_org"
    assert applied is True
    assert reason == "lower_consensus_prefix_variant"
    assert origin == "grounded_repair"
    assert dominant is not None
    assert dominant["text"] == "Dell"
    assert any(candidate["text"] == "Dell" for candidate in candidates)


def test_grounded_short_answer_repair_skips_ambiguous_company_candidates() -> None:
    harness = AnswerRepairHarness()
    detail_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text=(
            "Foram discutidas parcerias com a empresa Dell e com a empresa Lenovo para iniciativas distintas."
        ),
        chunk_kind="section_detail",
        chunk_order=3,
        section_title="Projetos",
    )

    repaired, _, _, _, applied, reason, origin = harness._repair_grounded_short_answer(
        "Empresa parceira",
        selected_docs=[detail_doc],
        retrieval_intent="specific_fact",
        resolved_question="Qual empresa e a parceira do projeto?",
    )

    assert repaired == "Empresa parceira"
    assert applied is False
    assert reason is None
    assert origin == "llm"


def test_grounded_short_answer_repair_prefers_consensus_company_candidate_over_noisy_acronym() -> None:
    harness = AnswerRepairHarness()
    noisy_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text=(
            "Lista ou enumeracao detectada: SEI 23067.031021/2020-50. "
            "SEI 23067.031021/2020-50. Codigo verificador e CRC."
        ),
        chunk_kind="list_block",
        chunk_order=1,
        section_title="Abertura",
    )
    detail_doc = make_doc(
        "01-2022_Ata_de_Reuniao.pdf",
        text=(
            'O projeto "AI for Customer Support" ocorreu em parceria com a empresa Dell. '
            "A empresa Dell financiou as bolsas previstas no projeto."
        ),
        chunk_kind="section_detail",
        chunk_order=3,
        section_title="Projetos",
    )

    repaired, answer_shape, candidates, dominant, applied, reason, origin = harness._repair_grounded_short_answer(
        "A Del",
        selected_docs=[noisy_doc, detail_doc],
        retrieval_intent="specific_fact",
        resolved_question='Qual empresa e a parceira do projeto "AI for Customer Support"?',
    )

    assert repaired == "Dell"
    assert answer_shape == "person_or_org"
    assert applied is True
    assert reason == "lower_consensus_prefix_variant"
    assert origin == "grounded_repair"
    assert dominant is not None
    assert dominant["text"] == "Dell"
    assert candidates[0]["text"] == "Dell"
    assert all(candidate["text"] != "SEI" or candidate["consensus_score"] < candidates[0]["consensus_score"] for candidate in candidates)


def test_grounded_short_answer_repair_prefers_repeated_date_evidence_over_noisy_short_token() -> None:
    harness = AnswerRepairHarness()
    noisy_doc = make_doc(
        "ACL23.pdf",
        text="SEI 99999. Documento assinado eletronicamente. Codigo CRC.",
        chunk_kind="list_block",
        chunk_order=1,
        section_title="Rodape",
    )
    detail_doc = make_doc(
        "ACL23.pdf",
        text=(
            "O afastamento ocorreu em 16 de julho de 2023 para participacao no evento. "
            "A data do evento permaneceu registrada como 16 de julho de 2023."
        ),
        chunk_kind="section_detail",
        chunk_order=2,
        section_title="Evento",
        date_values=["16 de julho de 2023"],
    )

    repaired, answer_shape, candidates, dominant, applied, reason, origin = harness._repair_grounded_short_answer(
        "SEI",
        selected_docs=[noisy_doc, detail_doc],
        retrieval_intent="specific_fact",
        resolved_question="Em qual data ocorreu o evento ACL23?",
    )

    assert repaired == "16 de julho de 2023"
    assert answer_shape == "date"
    assert applied is True
    assert reason == "dominant_consensus_factoid_answer"
    assert origin == "grounded_repair"
    assert dominant is not None
    assert dominant["text"] == "16 de julho de 2023"
    assert candidates[0]["text"] == "16 de julho de 2023"


def test_grounded_short_answer_repair_prefers_money_fact_over_noisy_short_token() -> None:
    harness = AnswerRepairHarness()
    noisy_doc = make_doc(
        "Projeto.pdf",
        text="SEI 101010. Documento assinado eletronicamente.",
        chunk_kind="document_profile",
        chunk_order=0,
        section_title="Perfil",
    )
    detail_doc = make_doc(
        "Projeto.pdf",
        text=(
            "O valor da bolsa foi de R$ 7.000,00 durante o periodo previsto. "
            "O valor aprovado permaneceu em R$ 7.000,00."
        ),
        chunk_kind="section_detail",
        chunk_order=4,
        section_title="Bolsas",
        money_values=["R$ 7.000,00"],
    )

    repaired, answer_shape, candidates, dominant, applied, reason, origin = harness._repair_grounded_short_answer(
        "SEI",
        selected_docs=[noisy_doc, detail_doc],
        retrieval_intent="specific_fact",
        resolved_question="Qual o valor da bolsa aprovada?",
    )

    assert repaired == "R$ 7.000,00"
    assert answer_shape == "money"
    assert applied is True
    assert reason == "dominant_consensus_factoid_answer"
    assert origin == "grounded_repair"
    assert dominant is not None
    assert dominant["text"] == "R$ 7.000,00"
    assert candidates[0]["text"] == "R$ 7.000,00"


def test_grounded_short_answer_repair_overrides_long_wrong_entity_answer_from_top_span() -> None:
    harness = AnswerRepairHarness()
    detail_doc = make_doc(
        "04-2023_Ata_de_Reuniao.pdf",
        text=(
            "A Profa. Cristina apresentou a Empresa Junior (CEOS) do curso de Ciencia da Computacao da UFC. "
            "A CEOS foi destacada como a empresa junior vinculada ao curso. "
            "Em outra acao, alunos visitaram a EEEP Alan Pinho Tabosa em Pentecoste."
        ),
        chunk_kind="section_detail",
        chunk_order=2,
        section_title="Abertura",
        entity_names=["CEOS", "EEEP Alan Pinho Tabosa"],
    )

    repaired, answer_shape, candidates, dominant, applied, reason, origin = harness._repair_grounded_short_answer(
        "A empresa junior do curso de Ciencia da Computacao da UFC e a EEEP Alan Pinho Tabosa, em Pentecoste.",
        selected_docs=[detail_doc],
        retrieval_intent="entity_lookup",
        resolved_question="Qual o nome da empresa junior do curso de Ciencia da Computacao da UFC?",
        target_document_name="04-2023_Ata_de_Reuniao.pdf",
    )

    assert repaired == "CEOS"
    assert answer_shape == "person_or_org"
    assert applied is True
    assert reason == "ignored_top_evidence_span"
    assert origin == "grounded_repair"
    assert dominant is not None
    assert dominant["text"] == "CEOS"
    assert candidates[0]["text"] == "CEOS"


def test_grounded_short_answer_repair_prefers_location_candidate_from_focused_span() -> None:
    harness = AnswerRepairHarness()
    noisy_doc = make_doc(
        "05-2025_Ata_de_Reuniao.pdf",
        text="Departamento de Computacao. Documento assinado eletronicamente.",
        chunk_kind="document_profile",
        chunk_order=0,
        section_title="Perfil",
    )
    detail_doc = make_doc(
        "05-2025_Ata_de_Reuniao.pdf",
        text=(
            "O Prof. Carlos Fisch de Brito solicitou realizar seu estagio pos-doutoral na COPPE/UFRJ, "
            "no Rio de Janeiro - RJ, durante o periodo aprovado."
        ),
        chunk_kind="section_detail",
        chunk_order=3,
        section_title="Afastamentos",
    )

    repaired, answer_shape, candidates, dominant, applied, reason, origin = harness._repair_grounded_short_answer(
        "Departamento",
        selected_docs=[noisy_doc, detail_doc],
        retrieval_intent="specific_fact",
        resolved_question="Em qual cidade brasileira o Prof. Carlos Fisch de Brito solicitou realizar seu estagio pos-doutoral na COPPE/UFRJ?",
        target_document_name="05-2025_Ata_de_Reuniao.pdf",
    )

    assert repaired == "Rio de Janeiro - RJ"
    assert answer_shape == "location"
    assert applied is True
    assert origin == "grounded_repair"
    assert dominant is not None
    assert dominant["text"] == "Rio de Janeiro - RJ"
    assert candidates[0]["text"] == "Rio de Janeiro - RJ"
