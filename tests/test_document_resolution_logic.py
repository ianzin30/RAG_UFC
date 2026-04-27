from __future__ import annotations

from types import SimpleNamespace

from application.service.rag.Constants import RAG_INDEX_CACHE_VERSION
from application.service.rag.modules.DocumentResolution import DocumentResolutionMixin
from application.service.rag.modules.TextProcessing import TextProcessingMixin
from application.service.rag.modules.retrieval.Core import RetrievalCoreMixin
from application.service.rag.modules.retrieval.Intents import RetrievalIntentMixin
from application.service.rag.parts.Planning import RAGServicePlanningMixin


def normalize_text(text: str) -> str:
    return " ".join(tokenize_text(text))


def tokenize_text(text: str) -> list[str]:
    harness = TextProcessingMixin()
    return harness._tokenize_search_text(text)


def make_doc(
    document_name: str,
    *,
    text: str,
    candidate_id: str = "",
    chunk_kind: str = "section_detail",
    chunk_order: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        page_content=text,
        metadata={
            "candidate_id": candidate_id,
            "document_name": document_name,
            "chunk_kind": chunk_kind,
            "chunk_order": chunk_order,
            "section_title": "Secao",
            "search_text_normalized": normalize_text(text),
        },
    )


class ResolverHarness(DocumentResolutionMixin, TextProcessingMixin):
    def __init__(self) -> None:
        self.document_registry = []
        self.document_catalog = []

    def add_document(self, document_name: str, text: str = "") -> dict[str, object]:
        entry = self._build_document_registry_entry(
            document_name=document_name,
            document_type="document",
            text=text or f"# {document_name}\nDocumento Type: document\nConteudo.",
            source=f"/tmp/{document_name}",
            chunks=[],
        )
        self.document_registry.append(entry)
        self.document_catalog = self.document_registry
        return entry


class PlanningHarness(RAGServicePlanningMixin, RetrievalIntentMixin, DocumentResolutionMixin, TextProcessingMixin):
    def __init__(self, documents: list[dict[str, object]]) -> None:
        self.document_registry = documents
        self.document_catalog = documents

    def _invoke_json_crewai_agent(self, agent, description: str, expected_output: str):
        return None

    def _format_chat_history(self, chat_history) -> str:
        return "Sem conversa anterior."


class FakeLlmClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def invoke(self, prompt_value) -> str:
        self.prompts.append(str(prompt_value))
        return self.response


class FakeVectorStore:
    def __init__(self, docs: list[SimpleNamespace]) -> None:
        self.docs = list(docs)

    def max_marginal_relevance_search(self, question: str, **kwargs) -> list[SimpleNamespace]:
        return self.docs[: int(kwargs.get("k") or len(self.docs))]


class RetrievalHarness(RetrievalCoreMixin, RetrievalIntentMixin, DocumentResolutionMixin, TextProcessingMixin):
    def __init__(self, docs: list[SimpleNamespace], selector_response: str | None = None) -> None:
        self._docs = list(docs)
        self.vector_store = None
        self.retriever = None
        self.llm_client = FakeLlmClient(selector_response or "")
        self.retrieval_config = SimpleNamespace(
            candidate_pool_limit=30,
            llm_selection_limit=8,
            llm_selector_enabled=True,
            lexical_limit=30,
        )
        self.recorded_stages: dict[str, list[SimpleNamespace]] = {}

    def _get_vector_store_documents(self) -> list[SimpleNamespace]:
        return list(self._docs)

    def _record_retrieval_stage(self, stage_name: str, docs, **kwargs) -> None:
        self.recorded_stages[stage_name] = list(docs or [])

    def _get_retrieval_candidate_id(self, doc) -> str:
        return str(doc.metadata.get("candidate_id") or doc.metadata.get("document_name") or "")


def test_explicit_filename_stem_and_title_matching() -> None:
    harness = ResolverHarness()
    harness.add_document("85_AFO.md")
    harness.add_document(
        "01_01-2022_Ata_de_Reuniao.md",
        text="# 01_01-2022_Ata_de_Reuniao\nDocumento Type: document\nProjeto\nAI for Customer Support\n",
    )

    assert harness._match_document_names("O que consta no arquivo 85_AFO.md?") == ["85_AFO.md"]
    assert harness._match_document_names("O que consta no arquivo 85_AFO?") == ["85_AFO.md"]
    assert harness._match_document_names('Qual empresa e parceira do projeto "AI for Customer Support"?') == [
        "01_01-2022_Ata_de_Reuniao.md"
    ]
    assert RAG_INDEX_CACHE_VERSION == 8


def test_content_clues_do_not_resolve_documents() -> None:
    harness = ResolverHarness()
    harness.add_document(
        "01_01-2022_Ata_de_Reuniao.md",
        text=(
            "# 01_01-2022_Ata_de_Reuniao\n"
            "Documento Type: document\n"
            'O projeto "AI for Customer Support" ocorreu em parceria com a empresa Dell.'
        ),
    )

    resolution = harness._resolve_documents_with_agent(
        "Qual empresa e a parceira do projeto AI for Customer Support?",
        "Qual empresa e a parceira do projeto AI for Customer Support?",
    )

    assert resolution["status"] == "no_match"
    assert resolution["document_shortlist"] == []


def test_unique_full_meeting_date_matches_but_month_year_does_not_filter() -> None:
    harness = ResolverHarness()
    harness.add_document(
        "01_01-2022_Ata_de_Reuniao.md",
        text="# Ata\nDocumento Type: document\nReuniao realizada em 14 de janeiro de 2022.",
    )
    harness.add_document(
        "02_02-2022_Ata_de_Reuniao.md",
        text="# Ata\nDocumento Type: document\nReuniao realizada em 18 de fevereiro de 2022.",
    )

    assert harness._extract_normalized_full_dates("14 de janeiro de 2022") == ["2022-01-14"]
    assert harness._match_document_names("Quem convocou a reuniao de 14 de janeiro de 2022?") == [
        "01_01-2022_Ata_de_Reuniao.md"
    ]
    assert harness._match_document_names("Quem convocou a reuniao de janeiro de 2022?") == []


def test_non_explicit_planning_is_collection_wide() -> None:
    resolver = ResolverHarness()
    resolver.add_document("01_01-2022_Ata_de_Reuniao.md")
    harness = PlanningHarness(resolver.document_registry)

    scope = harness._plan_scope(
        "Quem era o Chefe do Departamento que convocou a reuniao de janeiro de 2022?",
        "Quem era o Chefe do Departamento que convocou a reuniao de janeiro de 2022?",
        [],
        locked_document_name="01_01-2022_Ata_de_Reuniao.md",
    )
    selection = harness._plan_document_selection(
        "Quem era o Chefe do Departamento que convocou a reuniao de janeiro de 2022?",
        "Quem era o Chefe do Departamento que convocou a reuniao de janeiro de 2022?",
        [],
        scope,
        locked_document_name="01_01-2022_Ata_de_Reuniao.md",
    )

    assert scope["scope_type"] == "collection_wide"
    assert selection["status"] == "collection_wide"
    assert selection["document_shortlist"] == []


def test_llm_selector_parses_json_and_keeps_selected_candidate_ids() -> None:
    first = make_doc("A.md", text="Trecho sem resposta.", candidate_id="cand_a")
    second = make_doc("B.md", text="A empresa parceira do projeto e a Dell.", candidate_id="cand_b")
    harness = RetrievalHarness(
        [first, second],
        selector_response='```json\n{"selected_candidate_ids":["cand_b"]}\n```',
    )

    selected = harness._select_docs_with_llm(
        "Qual empresa e parceira do projeto?",
        [first, second],
        limit=1,
    )

    assert selected == [second]


def test_llm_selector_parses_maybe_candidate_ids_after_selected_ids() -> None:
    first = make_doc("A.md", text="Trecho sem resposta.", candidate_id="cand_a")
    second = make_doc("B.md", text="A empresa parceira do projeto e a Dell.", candidate_id="cand_b")
    harness = RetrievalHarness(
        [first, second],
        selector_response='{"selected_candidate_ids":["cand_a"],"maybe_candidate_ids":["cand_b"]}',
    )

    selected = harness._select_docs_with_llm(
        "Qual empresa e parceira do projeto?",
        [first, second],
        limit=2,
    )

    assert selected == [first, second]


def test_query_aware_selector_excerpt_includes_matched_evidence_after_long_prefix() -> None:
    long_prefix = "Texto administrativo irrelevante. " * 80
    relevant_text = (
        f"{long_prefix}"
        "O projeto AI for Customer Support foi apresentado em parceria com a empresa Dell."
    )
    doc = make_doc("Ata.md", text=relevant_text, candidate_id="cand_relevant")
    harness = RetrievalHarness([doc])

    payload = harness._build_llm_selector_candidate_payloads(
        [doc],
        question='Qual empresa e parceira do projeto "AI for Customer Support"?',
    )[0]

    assert "AI for Customer Support" in payload["text"]
    assert "Dell" in payload["text"]
    assert len(payload["text"]) < len(relevant_text)


def test_lexical_candidates_are_not_crowded_out_by_dense_candidates() -> None:
    dense_docs = [
        make_doc(f"Dense_{index}.md", text=f"Trecho denso generico {index}.", candidate_id=f"cand_dense_{index}")
        for index in range(30)
    ]
    lexical_relevant = make_doc(
        "Lexical.md",
        text='O projeto "AI for Customer Support" ocorreu em parceria com a empresa Dell.',
        candidate_id="cand_lexical",
    )
    harness = RetrievalHarness([*dense_docs, lexical_relevant])
    harness.vector_store = FakeVectorStore(dense_docs)
    harness.retrieval_config.lexical_limit = 12
    harness.retrieval_config.candidate_pool_limit = 30

    candidate_pool = harness._retrieve_docs('Qual empresa parceira do projeto "AI for Customer Support"?')

    assert lexical_relevant in candidate_pool
    assert candidate_pool.index(lexical_relevant) < 30


def test_protected_lexical_candidate_survives_when_llm_selector_omits_it() -> None:
    distractor = make_doc("Dense.md", text="Trecho sem a informacao pedida.", candidate_id="cand_dense")
    relevant = make_doc(
        "Lexical.md",
        text="O projeto AI for Customer Support ocorreu em parceria com a empresa Dell.",
        candidate_id="cand_lexical",
    )
    harness = RetrievalHarness(
        [distractor, relevant],
        selector_response='{"selected_candidate_ids":["cand_dense"]}',
    )
    harness.retrieval_config.llm_selection_limit = 2
    harness._last_retrieval_dense_docs = [distractor]
    harness._last_retrieval_lexical_docs = [relevant]

    selected = harness._select_docs_for_context(
        [distractor, relevant],
        resolved_question='Qual empresa parceira do projeto "AI for Customer Support"?',
    )

    assert selected == [distractor, relevant]
    assert harness.recorded_stages["llm_selected"] == [distractor]


def test_selector_prompt_instructs_recall_first_selection() -> None:
    harness = RetrievalHarness([])
    prompt = harness._build_llm_selector_prompt(
        question="Qual empresa parceira do projeto?",
        candidate_payloads=[],
        limit=8,
    )

    assert "Priorize recall" in prompt
    assert "maybe_candidate_ids" in prompt
    assert "nomes, datas, numeros, empresas, cargos, projetos ou siglas" in prompt


def test_lexical_retrieval_expands_full_dates_without_document_filtering() -> None:
    relevant = make_doc(
        "Ata_2022.md",
        text="O Chefe do Departamento convocou a reuniao de 14 de janeiro de 2022.",
        candidate_id="cand_relevant",
    )
    distractor = make_doc(
        "Outro.md",
        text="Reuniao administrativa de fevereiro de 2022.",
        candidate_id="cand_other",
    )
    harness = RetrievalHarness([distractor, relevant])

    ranked = harness._retrieve_lexical_docs(
        "Quem convocou a reuniao de 14/01/2022?",
        limit=2,
    )

    assert ranked[0] == relevant
