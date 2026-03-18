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
    sheet.append(["KARLA CRISTINA SOARES SOUZA", "Gerente de projetos", "1.0"])
    sheet.append(["RH INDIRETO - ADMINISTRATIVO", "", ""])
    sheet.append(["TOTAL", "", ""])

    planning_sheet = workbook.create_sheet("PLANEJADO")
    planning_sheet.append(["INSTITUTO/IES: UFC", "Column_2", "Column_3"])
    planning_sheet.append(["Serviços outros", "", ""])
    planning_sheet.append(["Licenças Gsuit", "", ""])
    planning_sheet.append(["Fundo de reserva", "Demais custos de P&D", ""])

    buffer = BytesIO()
    workbook.save(buffer)

    markdown = extract_spreadsheet_markdown(buffer.getvalue(), ".xlsx", "PlanilhaFinanceira.xlsx")

    assert "People index:" in markdown
    assert "Person: Fernando Antonio Mota Trinta | Role: Consultor em Arquitetura de Software | Sheet: RH | Row: 3" in markdown
    assert "Person: Maria Letícia dos Santos Dantas | Role: Testador 2 | Sheet: RH | Row: 4" in markdown
    assert "Person: KARLA CRISTINA SOARES SOUZA | Role: Gerente de projetos | Sheet: RH | Row: 5" in markdown
    assert "Person: RH INDIRETO - ADMINISTRATIVO" not in markdown
    assert "Person: TOTAL" not in markdown
    assert "Person: NOME" not in markdown
    assert "Person: Serviços outros" not in markdown
    assert "Person: Licenças Gsuit" not in markdown
    assert "Person: Fundo de reserva" not in markdown


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


def test_docling_pure_markdown_tables_are_indexed_as_spreadsheets_and_retrieve_people():
    rag = _build_rag_stub()
    document = Document(
        page_content=_docling_pure_table_markdown(),
        metadata={"source": "/tmp/06_PlanilhaFinanceira.md"},
    )

    document_name = rag._extract_document_name(document.page_content, document.metadata["source"])
    document_type = rag._extract_document_type(document.page_content, document.metadata["source"], document_name)

    assert document_type == "spreadsheet"

    document.metadata.update(
        {
            "document_name": document_name,
            "document_name_normalized": rag._normalize_identifier(document_name),
            "document_stem_normalized": rag._normalize_identifier(Path(document_name).stem),
            "document_type": document_type,
        }
    )

    chunks = rag._build_spreadsheet_chunks(document, rag._extract_document_header(document.page_content))
    rag.spreadsheet_chunk_index["PlanilhaFinanceira.xlsx"] = chunks
    rag.document_catalog = [
        {
            "name": "PlanilhaFinanceira.xlsx",
            "display_name": "PlanilhaFinanceira.xlsx",
            "normalized_name": "planilhafinanceira xlsx",
            "normalized_stem": "planilhafinanceira",
            "document_type": "spreadsheet",
            "summary": "",
        }
    ]

    docs = rag._retrieve_spreadsheet_chunks(
        "quais sao alguns trabalhadores mencionados na PlanilhaFinanceira.xlsx?",
        "PlanilhaFinanceira.xlsx",
    )

    names = [doc.metadata.get("entity_name") for doc in docs if doc.metadata.get("entity_name")]
    assert names[:2] == [
        "Fernando Antonio Mota Trinta",
        "Maria Letícia dos Santos Dantas",
    ]


def test_ask_question_answers_collection_inventory_from_catalog_without_llm():
    rag = _build_rag_stub()
    rag.retriever = object()
    rag.answer_chain = _FailingChain()
    rag.small_talk_chain = _FailingChain()
    rag.collection_name = "documentos de teste"
    rag.document_catalog = [
        {
            "name": "AFO.pdf",
            "display_name": "AFO.pdf",
            "normalized_name": "afo pdf",
            "normalized_stem": "afo",
            "document_type": "pdf",
            "summary": "",
        },
        {
            "name": "SAAR.pdf",
            "display_name": "SAAR.pdf",
            "normalized_name": "saar pdf",
            "normalized_stem": "saar",
            "document_type": "pdf",
            "summary": "",
        },
        {
            "name": "RACK.pdf",
            "display_name": "RACK.pdf",
            "normalized_name": "rack pdf",
            "normalized_stem": "rack",
            "document_type": "pdf",
            "summary": "",
        },
        {
            "name": "SAAR.xlsx",
            "display_name": "SAAR.xlsx",
            "normalized_name": "saar xlsx",
            "normalized_stem": "saar",
            "document_type": "spreadsheet",
            "summary": "",
        },
        {
            "name": "PlanilhaFinanceira.xlsx",
            "display_name": "PlanilhaFinanceira.xlsx",
            "normalized_name": "planilhafinanceira xlsx",
            "normalized_stem": "planilhafinanceira",
            "document_type": "spreadsheet",
            "summary": "",
        },
    ]

    answer = rag.ask_question("quais seriam os documentos?")

    assert "Encontrei 5 arquivos carregados:" in answer
    assert "AFO.pdf" in answer
    assert "SAAR.pdf" in answer
    assert "RACK.pdf" in answer
    assert "SAAR.xlsx" in answer
    assert "PlanilhaFinanceira.xlsx" in answer


def test_saar_legacy_chunks_recover_uppercase_names_and_filter_false_people_entries():
    rag = _build_rag_stub()
    document = Document(
        page_content=_legacy_saar_markdown(),
        metadata={
            "source": "/tmp/05_SAAR.md",
            "document_name": "SAAR.xlsx",
            "document_name_normalized": "saar xlsx",
            "document_stem_normalized": "saar",
            "document_type": "spreadsheet",
        },
    )

    chunks = rag._build_spreadsheet_chunks(document, rag._extract_document_header(document.page_content))
    people_names = {
        chunk.metadata.get("entity_name")
        for chunk in chunks
        if chunk.metadata.get("chunk_kind") == "people_index" and chunk.metadata.get("entity_name")
    }

    assert "KARLA CRISTINA SOARES SOUZA" in people_names
    assert "JULIA BASTOS DA NOBREGA" in people_names
    assert "Serviços outros" not in people_names
    assert "Licenças Gsuit" not in people_names
    assert "Fundo de reserva" not in people_names


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


class _FailingChain:
    def invoke(self, *_args, **_kwargs):
        raise AssertionError("LLM chain should not be invoked for collection inventory questions.")


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


def _docling_pure_table_markdown() -> str:
    return dedent(
        """
        # PlanilhaFinanceira.xlsx
        Extraction method: docling-puro

        | RH DIRETO - BOLSAS          | RH DIRETO - BOLSAS                   | RH DIRETO - BOLSAS |
        |-----------------------------|--------------------------------------|--------------------|
        | NOME                        | Cargo/Função                         | Início             |
        | Fernando Antonio Mota Trinta | Consultor em Arquitetura de Software | 1.0                |
        | Maria Letícia dos Santos Dantas | Testador 2                       | 1.0                |
        | Paulo Antonio Rego          | Coordenador do Projeto               | 1.0                |
        """
    ).strip()


def _legacy_saar_markdown() -> str:
    return dedent(
        """
        # SAAR.xlsx
        Extraction method: docling
        Document type: spreadsheet
        Spreadsheet format: xlsx
        Spreadsheet file: SAAR.xlsx
        Total sheets: 2
        Sheet names: RH, PLANEJADO
        ## Sheet: RH
        Spreadsheet file: SAAR.xlsx
        Sheet name: RH
        Header columns: RH DIRETO - BOLSAS, Column_2, Column_3
        Data rows indexed: 12
        People index:
        - Person: Lincoln Souza Rocha | Role: Coordenador de Projetos | Sheet: RH | Row: 3
        - Person: Renan Gomes Vieira | Role: Pesquisador em Engenharia de Dados | Sheet: RH | Row: 4
        - Person: Emanuele Marques Rodrigues Santos | Role: Pesquisador em Visualização | Sheet: RH | Row: 5
        - Person: Camilo Camilo Almendra | Role: Pesquisador em Engenharia de Software | Sheet: RH | Row: 6
        - Person: Cesar Lincoln C. Mattos | Role: Pesquisador em Ciência de Dados | Sheet: RH | Row: 7
        - Person: Pedro hericson | Role: Especialista em Engenharia de Dados (Doutorando) | Sheet: RH | Row: 8
        Row records:
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 3: RH DIRETO - BOLSAS=Lincoln Souza Rocha | Column_2=Coordenador de Projetos | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 4: RH DIRETO - BOLSAS=Renan Gomes Vieira | Column_2=Pesquisador em Engenharia de Dados | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 5: RH DIRETO - BOLSAS=Emanuele Marques Rodrigues Santos | Column_2=Pesquisador em Visualização | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 6: RH DIRETO - BOLSAS=Camilo Camilo Almendra | Column_2=Pesquisador em Engenharia de Software | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 7: RH DIRETO - BOLSAS=Cesar Lincoln C. Mattos | Column_2=Pesquisador em Ciência de Dados | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 8: RH DIRETO - BOLSAS=Pedro hericson | Column_2=Especialista em Engenharia de Dados (Doutorando) | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 9: RH DIRETO - BOLSAS=Gabriel Urano? | Column_2=Especialista em Visualização (Doutorando) | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 10: RH DIRETO - BOLSAS=Anderson Almada/TBD | Column_2=Pesquisador em Arquitetura de Software (PhD) | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 11: RH DIRETO - BOLSAS=Gustavo Moraes | Column_2=Especialista em Banco de Dados (Doutorando/PHD) | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 20: RH DIRETO - BOLSAS=KARLA CRISTINA SOARES SOUZA | Column_2=Gerente de projetos | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 22: RH DIRETO - BOLSAS=JULIA BASTOS DA NOBREGA | Column_2=UI/UX Designer | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 23: RH DIRETO - BOLSAS=Renan Alves Barbosa | Column_2=Desenvolvedor full stack 1 | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 24: RH DIRETO - BOLSAS=Davi dos Santos Freitas | Column_2=Desenvolvedor full stack 2 | Column_3=1.0
        - Spreadsheet file SAAR.xlsx | Sheet RH | Row 29: RH DIRETO - BOLSAS=José Mateus Cezário Magalhães | Column_2=Analista de Projetos / Financeiro | Column_3=1.0
        ## Sheet: PLANEJADO
        Spreadsheet file: SAAR.xlsx
        Sheet name: PLANEJADO
        Header columns: INSTITUTO/IES: UFC, Column_2, Column_3
        Data rows indexed: 3
        People index:
        - Person: Serviços outros | Sheet: PLANEJADO | Row: 12
        - Person: Licenças Gsuit | Sheet: PLANEJADO | Row: 37
        - Person: Fundo de reserva | Role: Demais custos de P&D | Sheet: PLANEJADO | Row: 107
        Row records:
        - Spreadsheet file SAAR.xlsx | Sheet PLANEJADO | Row 12: INSTITUTO/IES: UFC=Serviços outros
        - Spreadsheet file SAAR.xlsx | Sheet PLANEJADO | Row 37: INSTITUTO/IES: UFC=Licenças Gsuit
        - Spreadsheet file SAAR.xlsx | Sheet PLANEJADO | Row 107: INSTITUTO/IES: UFC=Fundo de reserva | Column_2=Demais custos de P&D
        """
    ).strip()
