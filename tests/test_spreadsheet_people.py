import sys
from io import BytesIO
from pathlib import Path
from textwrap import dedent

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openpyxl import Workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from application.service.rag import RAGService
from application.service.spreadsheet_markdown import extract_spreadsheet_markdown


def test_extract_spreadsheet_markdown_emits_people_index():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "RH"
    sheet.append(["RH DIRETO - BOLSAS", "Column_2", "Column_3"])
    sheet.append(["NOME", "Cargo/Função", "Início"])
    sheet.append(["Fernando Antonio Mota Trinta", "Consultor em Arquitetura de Software", "1.0"])
    sheet.append(["Maria Letícia dos Santos Dantas", "Testador 2", "1.0"])
    sheet.append(["RH INDIRETO - ADMINISTRATIVO", "", ""])
    sheet.append(["TOTAL", "", ""])

    buffer = BytesIO()
    workbook.save(buffer)

    markdown = extract_spreadsheet_markdown(buffer.getvalue(), ".xlsx", "PlanilhaFinanceira.xlsx")

    assert "People index:" in markdown
    assert "Person: Fernando Antonio Mota Trinta | Role: Consultor em Arquitetura de Software | Sheet: RH | Row: 3" in markdown
    assert "Person: Maria Letícia dos Santos Dantas | Role: Testador 2 | Sheet: RH | Row: 4" in markdown
    assert "Person: RH INDIRETO - ADMINISTRATIVO" not in markdown
    assert "Person: TOTAL" not in markdown
    assert "Person: NOME" not in markdown


def test_spreadsheet_chunks_keep_row_records_intact_for_legacy_markdown():
    rag = _build_rag_stub()
    document = Document(
        page_content=_legacy_spreadsheet_markdown(),
        metadata={
            "source": "/tmp/06_PlanilhaFinanceira.md",
            "document_name": "PlanilhaFinanceira.xlsx",
            "document_name_normalized": "planilhafinanceira xlsx",
            "document_stem_normalized": "planilhafinanceira",
            "document_type": "spreadsheet",
        },
    )

    chunks = rag._build_spreadsheet_chunks(document, rag._extract_document_header(document.page_content))
    row_chunks = [chunk for chunk in chunks if chunk.metadata.get("chunk_kind") == "row_record"]
    people_chunks = [chunk for chunk in chunks if chunk.metadata.get("chunk_kind") == "people_index"]

    assert any(chunk.metadata.get("entity_name") == "Fernando Antonio Mota Trinta" for chunk in row_chunks)
    assert any(chunk.metadata.get("entity_name") == "Maria Letícia dos Santos Dantas" for chunk in row_chunks)
    assert any("Fernando Antonio Mota Trinta" in chunk.page_content for chunk in row_chunks)
    assert any(chunk.metadata.get("entity_name") == "Fernando Antonio Mota Trinta" for chunk in people_chunks)


def test_structured_spreadsheet_retrieval_prioritizes_people_rows():
    rag = _build_rag_stub()
    document = Document(
        page_content=_legacy_spreadsheet_markdown(),
        metadata={
            "source": "/tmp/06_PlanilhaFinanceira.md",
            "document_name": "PlanilhaFinanceira.xlsx",
            "document_name_normalized": "planilhafinanceira xlsx",
            "document_stem_normalized": "planilhafinanceira",
            "document_type": "spreadsheet",
        },
    )

    chunks = rag._build_spreadsheet_chunks(document, rag._extract_document_header(document.page_content))
    rag.spreadsheet_chunk_index["PlanilhaFinanceira.xlsx"] = chunks
    rag.document_catalog = [
        {
            "name": "PlanilhaFinanceira.xlsx",
            "normalized_name": "planilhafinanceira xlsx",
            "normalized_stem": "planilhafinanceira",
            "document_type": "spreadsheet",
        }
    ]

    docs = rag._retrieve_spreadsheet_chunks(
        "quais sao alguns trabalhadores mencionados na PlanilhaFinanceira.xlsx?",
        "PlanilhaFinanceira.xlsx",
    )

    names = [doc.metadata.get("entity_name") for doc in docs if doc.metadata.get("entity_name")]
    assert names[:3] == [
        "Fernando Antonio Mota Trinta",
        "Maria Letícia dos Santos Dantas",
        "Paulo Antonio Rego",
    ]


def test_literal_name_query_hits_matching_spreadsheet_entry():
    rag = _build_rag_stub()
    document = Document(
        page_content=_legacy_spreadsheet_markdown(),
        metadata={
            "source": "/tmp/06_PlanilhaFinanceira.md",
            "document_name": "PlanilhaFinanceira.xlsx",
            "document_name_normalized": "planilhafinanceira xlsx",
            "document_stem_normalized": "planilhafinanceira",
            "document_type": "spreadsheet",
        },
    )

    chunks = rag._build_spreadsheet_chunks(document, rag._extract_document_header(document.page_content))
    rag.spreadsheet_chunk_index["PlanilhaFinanceira.xlsx"] = chunks
    rag.document_catalog = [
        {
            "name": "PlanilhaFinanceira.xlsx",
            "normalized_name": "planilhafinanceira xlsx",
            "normalized_stem": "planilhafinanceira",
            "document_type": "spreadsheet",
        }
    ]

    docs = rag._retrieve_spreadsheet_chunks("Fernando Antonio Mota Trinta", "PlanilhaFinanceira.xlsx")

    assert docs
    assert docs[0].metadata.get("entity_name") == "Fernando Antonio Mota Trinta"


def _build_rag_stub() -> RAGService:
    rag = RAGService.__new__(RAGService)
    rag.project_root = Path("/Users/fernandotrinta/Desktop/RAG")
    rag.collections_root = rag.project_root / "data" / "collections"
    rag.text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ": ", "  ", " ", ""],
    )
    rag.vector_store = None
    rag.retriever = None
    rag.answer_chain = None
    rag.small_talk_chain = None
    rag.query_rewrite_chain = None
    rag.collection_name = None
    rag.document_catalog = []
    rag.spreadsheet_chunk_index = {}
    return rag


def _legacy_spreadsheet_markdown() -> str:
    return dedent(
        """
        # PlanilhaFinanceira.xlsx
        Extraction method: docling
        Document type: spreadsheet
        Spreadsheet format: xlsx
        Spreadsheet file: PlanilhaFinanceira.xlsx
        Total sheets: 1
        Sheet names: RH
        ## Sheet: RH
        Spreadsheet file: PlanilhaFinanceira.xlsx
        Sheet name: RH
        Header columns: RH DIRETO - BOLSAS, Column_2, Column_3
        Data rows indexed: 3
        Row records:
        - Spreadsheet file PlanilhaFinanceira.xlsx | Sheet RH | Row 7: RH DIRETO - BOLSAS=Fernando Antonio Mota Trinta | Column_2=Consultor em Arquitetura de Software | Column_3=1.0
        - Spreadsheet file PlanilhaFinanceira.xlsx | Sheet RH | Row 8: RH DIRETO - BOLSAS=Maria Letícia dos Santos Dantas | Column_2=Testador 2 | Column_3=1.0
        - Spreadsheet file PlanilhaFinanceira.xlsx | Sheet RH | Row 9: RH DIRETO - BOLSAS=Paulo Antonio Rego | Column_2=Coordenador do Projeto | Column_3=1.0
        """
    ).strip()
