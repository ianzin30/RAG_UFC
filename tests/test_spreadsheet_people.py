import sys
from io import BytesIO
from pathlib import Path
from textwrap import dedent

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openpyxl import Workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from application.service.collections.contracts import NormalizedDocument, QueryPlan, SpreadsheetModel
from application.service.collections.repository import CollectionRepository
from application.service.rag import RAGService
from application.service.retrieval.coordinator import RetrievalCoordinator
from application.service.retrieval.query_planner import QueryPlanner
from application.service.spreadsheets.markdown import extract_spreadsheet_markdown
from application.service.spreadsheets.normalizer import SpreadsheetNormalizer


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
    assert "Person: Serviços outros" not in markdown


def test_spreadsheet_normalizer_parses_structured_markdown_and_preserves_people_rows():
    normalizer = SpreadsheetNormalizer()
    model = normalizer.normalize("PlanilhaFinanceira.xlsx", _legacy_spreadsheet_markdown(), "xlsx")

    assert model.sheets
    rh_sheet = model.sheets[0]
    row_entities = [row.entity.name for row in rh_sheet.rows if row.entity]

    assert row_entities == [
        "Fernando Antonio Mota Trinta",
        "Maria Letícia dos Santos Dantas",
        "Paulo Antonio Rego",
    ]
    assert [person.name for person in rh_sheet.people] == row_entities


def test_spreadsheet_normalizer_parses_docling_pure_markdown_tables():
    normalizer = SpreadsheetNormalizer()
    model = normalizer.normalize("PlanilhaFinanceira.xlsx", _docling_pure_table_markdown(), "xlsx")

    assert model.sheets
    sheet = model.sheets[0]
    assert [person.name for person in sheet.people][:2] == [
        "Fernando Antonio Mota Trinta",
        "Maria Letícia dos Santos Dantas",
    ]


def test_collection_repository_loads_manifest_backed_collection_without_markdown_inference(tmp_path):
    repository = CollectionRepository(tmp_path)
    document = NormalizedDocument(
        document_id="01_contract",
        display_name="Canonical.pdf",
        document_type="pdf",
        source_kind="google_drive",
        source_metadata={"id": "123"},
        extraction_method="docling-puro",
        content_markdown_path="",
        content_text="Texto canônico do documento.",
        summary="Texto canônico do documento.",
        structured_data=None,
        content_markdown="# WrongHeading\n\nThis markdown header must not become the document identity.",
    )

    repository.save_collection("contract_test", "google_drive", "docling-puro", [document])
    loaded = repository.load_collection("contract_test")

    assert loaded.manifest.collection_name == "contract_test"
    assert loaded.documents[0].display_name == "Canonical.pdf"
    assert loaded.documents[0].document_type == "pdf"


def test_collection_repository_rejects_legacy_markdown_only_collection(tmp_path):
    repository = CollectionRepository(tmp_path)
    legacy_path = tmp_path / "data" / "collections" / "legacy"
    legacy_path.mkdir(parents=True, exist_ok=True)
    (legacy_path / "01_legacy.md").write_text("# Legacy", encoding="utf-8")

    try:
        repository.load_collection("legacy")
    except Exception as exc:
        assert "manifest.json" in str(exc)
    else:
        raise AssertionError("Legacy collections must be rejected without manifest.json")


def test_query_planner_routes_inventory_multi_doc_and_spreadsheet_entity_questions():
    planner = QueryPlanner()
    catalog = [
        planner.build_catalog_entry("01_afo_pdf", "AFO.pdf", "pdf", ""),
        planner.build_catalog_entry("02_afo_xlsx", "AFO.xlsx", "spreadsheet", ""),
        planner.build_catalog_entry("03_planilha", "PlanilhaFinanceira.xlsx", "spreadsheet", ""),
    ]

    inventory = planner.plan("quantos arquivos voce processou?", "quantos arquivos voce processou?", catalog)
    comparison = planner.plan("compare AFO.pdf e AFO.xlsx", "compare AFO.pdf e AFO.xlsx", catalog)
    spreadsheet = planner.plan(
        "quais pessoas aparecem na PlanilhaFinanceira.xlsx?",
        "quais pessoas aparecem na PlanilhaFinanceira.xlsx?",
        catalog,
    )

    assert inventory.intent == "inventory"
    assert inventory.inventory_mode == "count"
    assert comparison.intent == "multi_document"
    assert comparison.target_document_ids == ["01_afo_pdf", "02_afo_xlsx"]
    assert spreadsheet.intent == "spreadsheet_entity"
    assert spreadsheet.target_document_ids == ["03_planilha"]


def test_retrieval_coordinator_retrieves_people_from_normalized_spreadsheet_model():
    normalizer = SpreadsheetNormalizer()
    model = normalizer.normalize("PlanilhaFinanceira.xlsx", _legacy_spreadsheet_markdown(), "xlsx")
    document = _build_spreadsheet_document("01_planilha", "PlanilhaFinanceira.xlsx", model)
    coordinator = RetrievalCoordinator(
        RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ": ", "  ", " ", ""],
        )
    )

    chunks = coordinator._build_spreadsheet_chunks(document, SpreadsheetModel.from_dict(document.structured_data))
    docs = coordinator.retrieve(
        plan=QueryPlan(
            intent="spreadsheet_entity",
            target_document_ids=["01_planilha"],
            requested_document_type="spreadsheet",
            needs_structured_lookup=True,
            resolved_query="quais sao alguns trabalhadores mencionados na PlanilhaFinanceira.xlsx?",
        ),
        vector_store=None,
        retriever=None,
        spreadsheet_chunk_index={"01_planilha": chunks},
        document_catalog=[
            {
                "document_id": "01_planilha",
                "display_name": "PlanilhaFinanceira.xlsx",
                "document_type": "spreadsheet",
            }
        ],
    )

    names = [doc.metadata.get("entity_name") for doc in docs if doc.metadata.get("entity_name")]
    assert names[:3] == [
        "Fernando Antonio Mota Trinta",
        "Maria Letícia dos Santos Dantas",
        "Paulo Antonio Rego",
    ]


def test_ask_question_answers_collection_inventory_from_catalog_without_llm():
    rag = _build_rag_stub()
    rag.retriever = object()
    rag.answer_chain = _FailingChain()
    rag.small_talk_chain = _FailingChain()
    rag.collection_name = "documentos de teste"
    rag.document_catalog = [
        rag.query_planner.build_catalog_entry("01_afo", "AFO.pdf", "pdf", ""),
        rag.query_planner.build_catalog_entry("02_saar_pdf", "SAAR.pdf", "pdf", ""),
        rag.query_planner.build_catalog_entry("03_rack", "RACK.pdf", "pdf", ""),
        rag.query_planner.build_catalog_entry("04_saar_xlsx", "SAAR.xlsx", "spreadsheet", ""),
        rag.query_planner.build_catalog_entry("05_planilha", "PlanilhaFinanceira.xlsx", "spreadsheet", ""),
    ]

    answer = rag.ask_question("quais seriam os documentos?")

    assert "Encontrei 5 arquivos carregados:" in answer
    assert "AFO.pdf" in answer
    assert "SAAR.xlsx" in answer
    assert "PlanilhaFinanceira.xlsx" in answer


def _build_rag_stub() -> RAGService:
    rag = RAGService.__new__(RAGService)
    rag.project_root = Path("/Users/fernandotrinta/Desktop/RAG")
    rag.collections_root = rag.project_root / "data" / "collections"
    rag.query_planner = QueryPlanner()
    rag.retrieval_coordinator = None
    rag.vector_store = None
    rag.retriever = None
    rag.answer_chain = None
    rag.small_talk_chain = None
    rag.query_rewrite_chain = None
    rag.loaded_collection_id = None
    rag.collection_name = None
    rag.collection_manifest = None
    rag.normalized_documents = []
    rag.document_catalog = []
    rag.spreadsheet_chunk_index = {}
    return rag


class _FailingChain:
    def invoke(self, *_args, **_kwargs):
        raise AssertionError("LLM chain should not be invoked for collection inventory questions.")


def _build_spreadsheet_document(document_id: str, display_name: str, model: SpreadsheetModel) -> NormalizedDocument:
    content_text = model.to_text()
    return NormalizedDocument(
        document_id=document_id,
        display_name=display_name,
        document_type="spreadsheet",
        source_kind="google_drive",
        source_metadata={"id": document_id},
        extraction_method="docling",
        content_markdown_path="",
        content_text=content_text,
        summary=content_text.split("\n", 1)[0],
        structured_data=model.to_dict(),
        content_markdown=_legacy_spreadsheet_markdown(),
    )


def _legacy_spreadsheet_markdown() -> str:
    return dedent(
        """
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
        | RH DIRETO - BOLSAS              | RH DIRETO - BOLSAS                   | RH DIRETO - BOLSAS |
        |---------------------------------|--------------------------------------|--------------------|
        | NOME                            | Cargo/Função                         | Início             |
        | Fernando Antonio Mota Trinta    | Consultor em Arquitetura de Software | 1.0                |
        | Maria Letícia dos Santos Dantas | Testador 2                           | 1.0                |
        | Paulo Antonio Rego              | Coordenador do Projeto               | 1.0                |
        """
    ).strip()
