import sys
from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPLICATION_ROOT = PROJECT_ROOT / "application"
for path in (PROJECT_ROOT, APPLICATION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from application.service.rag_service.modules.retrieval_parts.aggregation import RetrievalAggregationMixin
from application.service.rag_service.modules.retrieval_parts.core import RetrievalCoreMixin
from application.service.rag_service.modules.retrieval_parts.intents import RetrievalIntentMixin
from application.service.rag_service.modules.spreadsheet_parts.chunks import SpreadsheetChunkBuilderMixin
from application.service.rag_service.modules.text_processing import TextProcessingMixin


SAMPLE_DOCUMENT_PATH = (
    PROJECT_ROOT
    / "data/collections/google_drive_rag/60_01-2022_Ata_de_Reuniao.md"
)
SAMPLE_DOCUMENT_NAME = "01-2022_Ata_de_Reuniao.pdf"


class RetrievalPrecisionHarness(
    RetrievalAggregationMixin,
    RetrievalCoreMixin,
    RetrievalIntentMixin,
    SpreadsheetChunkBuilderMixin,
    TextProcessingMixin,
):
    def __init__(self) -> None:
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._vector_docs = []
        self.vector_store = SimpleNamespace(
            max_marginal_relevance_search=lambda *args, **kwargs: [],
            similarity_search=lambda *args, **kwargs: [],
        )
        self.retriever = SimpleNamespace(invoke=lambda question: [])

    def _get_vector_store_documents(self) -> list:
        return list(self._vector_docs)

    def _is_spreadsheet_document_name(self, document_name: str | None) -> bool:
        return False

    def _retrieve_spreadsheet_chunks(self, question: str, target_document_name: str | None):
        return []


def build_sample_chunks() -> tuple[RetrievalPrecisionHarness, list[Document]]:
    service = RetrievalPrecisionHarness()
    raw_text = SAMPLE_DOCUMENT_PATH.read_text(encoding="utf-8")
    normalized_text = service._normalize_whitespace(raw_text)
    document = Document(
        page_content=normalized_text,
        metadata={
            "source": str(SAMPLE_DOCUMENT_PATH),
            "document_name": SAMPLE_DOCUMENT_NAME,
            "document_type": "document",
        },
    )
    chunks = service._build_generic_chunks(document, service._extract_document_header(normalized_text))
    service._vector_docs = chunks
    return service, chunks


def test_generic_chunk_builder_creates_structured_chunks_for_long_document():
    service, chunks = build_sample_chunks()

    chunk_kinds = {str(chunk.metadata.get("chunk_kind") or "") for chunk in chunks}
    assert "document_profile" in chunk_kinds
    assert "section_overview" in chunk_kinds
    assert "entity_index" in chunk_kinds
    assert "list_block" in chunk_kinds
    assert "section_detail" in chunk_kinds
    assert any(chunk.metadata.get("section_title") for chunk in chunks if chunk.metadata.get("chunk_kind") != "document_profile")
    extracted_names = service._extract_name_candidates("Javam de Castro Machado, Joao Bosco Ferreira Filho")
    assert "Joao Bosco Ferreira Filho" in extracted_names or "Javam de Castro Machado" in extracted_names


def test_document_expansion_intent_is_detected_for_broad_follow_ups():
    service = RetrievalPrecisionHarness()
    assert service._infer_retrieval_intent("fale mais sobre ele, me dê detalhes") == "document_expansion"


def test_lexical_retrieval_respects_locked_document_scope():
    service = RetrievalPrecisionHarness()
    doc_one = Document(
        page_content="Documento: doc-1.pdf\nSecao: Equipe\nTrecho:\nJoao Paulo Pordeus Gomes e Paulo Antonio Leal Rego.",
        metadata={
            "document_name": "doc-1.pdf",
            "chunk_kind": "entity_index",
            "chunk_order": 0,
            "search_text_normalized": service._normalize_identifier(
                "doc-1.pdf Joao Paulo Pordeus Gomes Paulo Antonio Leal Rego coordenador"
            ),
        },
    )
    doc_two = Document(
        page_content="Documento: doc-2.pdf\nSecao: Equipe\nTrecho:\nOutro documento com coordenadores distintos.",
        metadata={
            "document_name": "doc-2.pdf",
            "chunk_kind": "entity_index",
            "chunk_order": 0,
            "search_text_normalized": service._normalize_identifier("doc-2.pdf outros coordenadores"),
        },
    )
    service._vector_docs = [doc_one, doc_two]

    docs = service._retrieve_lexical_docs(
        "quem sao os coordenadores joao paulo",
        target_document_name="doc-1.pdf",
        limit=5,
    )

    assert docs
    assert all(doc.metadata.get("document_name") == "doc-1.pdf" for doc in docs)


def test_document_expansion_prefers_coverage_across_multiple_sections():
    service = RetrievalPrecisionHarness()
    docs = [
        Document(
            page_content=f"Documento: {SAMPLE_DOCUMENT_NAME}\nSecao: Abertura\nTrecho:\nResumo geral da reuniao.",
            metadata={
                "document_name": SAMPLE_DOCUMENT_NAME,
                "chunk_kind": "document_profile" if index == 0 else "section_overview",
                "section_key": f"section-{index}",
                "section_title": section_title,
                "chunk_order": index,
                "search_text_normalized": service._normalize_identifier(section_title),
            },
        )
        for index, section_title in enumerate(["Abertura", "Eleicoes", "Projetos", "Orcamento"])
    ]
    docs.append(
        Document(
            page_content=f"Documento: {SAMPLE_DOCUMENT_NAME}\nSecao: Participantes\nPessoas ou entidades: Ana Silva; Bruno Lima; Carla Rocha",
            metadata={
                "document_name": SAMPLE_DOCUMENT_NAME,
                "chunk_kind": "entity_index",
                "section_key": "section-participantes",
                "section_title": "Participantes",
                "chunk_order": 4,
                "entity_names": ["Ana Silva", "Bruno Lima", "Carla Rocha"],
                "search_text_normalized": service._normalize_identifier("participantes Ana Silva Bruno Lima Carla Rocha"),
            },
        )
    )
    service._vector_docs = docs

    selected = service._retrieve_document_coverage_docs(
        "me de detalhes desse documento",
        target_document_name=SAMPLE_DOCUMENT_NAME,
        retrieval_intent="document_expansion",
        limit=6,
    )

    section_keys = {doc.metadata.get("section_key") for doc in selected if doc.metadata.get("section_key")}
    assert len(section_keys) >= 4
    assert any(doc.metadata.get("chunk_kind") == "entity_index" for doc in selected)
    assert all(doc.metadata.get("document_name") == SAMPLE_DOCUMENT_NAME for doc in selected)


def test_aggregated_answer_context_surfaces_names_and_topics_from_sample_document():
    service, chunks = build_sample_chunks()
    selected_docs = service._select_docs_for_context(
        chunks,
        target_document_name=SAMPLE_DOCUMENT_NAME,
        retrieval_intent="document_expansion",
        resolved_question="fale mais sobre esse documento e me de detalhes",
    )

    context = service._build_answer_context(
        selected_docs,
        retrieval_intent="document_expansion",
        target_document_name=SAMPLE_DOCUMENT_NAME,
        resolved_question="fale mais sobre esse documento e me de detalhes",
    )

    assert "Pacote agregado de evidencias" in context
    assert "Pessoas ou entidades consolidadas:" in context
    assert "Javam de Castro Machado" in context
    assert "João Bosco Ferreira Filho" in context
    assert "Secoes ou topicos cobertos:" in context
