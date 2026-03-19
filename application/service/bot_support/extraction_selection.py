EXTRACTION_METHOD_PYPDF = "pypdf"
EXTRACTION_METHOD_DOCLING = "docling"
EXTRACTION_METHOD_DOCLING_PURE = "docling-puro"
EXTRACTION_METHOD_DOC_CSV = "doc-csv"


def ensure_extraction_session(session: dict) -> dict:
    session.setdefault("extraction_method", None)
    session.setdefault("awaiting_extraction_choice", False)
    return session


def normalize_extraction_method(text: str | None) -> str | None:
    normalized = (text or "").strip().lower()
    if normalized in {"1", EXTRACTION_METHOD_PYPDF}:
        return EXTRACTION_METHOD_PYPDF
    if normalized in {"2", EXTRACTION_METHOD_DOCLING}:
        return EXTRACTION_METHOD_DOCLING
    if normalized in {"3", EXTRACTION_METHOD_DOCLING_PURE, "docling_puro", "docling puro"}:
        return EXTRACTION_METHOD_DOCLING_PURE
    if normalized in {"4", EXTRACTION_METHOD_DOC_CSV, "doc_csv", "doc csv"}:
        return EXTRACTION_METHOD_DOC_CSV
    return None


def format_extraction_method(extraction_method: str | None) -> str:
    if extraction_method == EXTRACTION_METHOD_DOC_CSV:
        return "Doc CSV"
    if extraction_method == EXTRACTION_METHOD_DOCLING_PURE:
        return "Docling Puro"
    if extraction_method == EXTRACTION_METHOD_DOCLING:
        return "Docling"
    return "PyPDF"


def build_extraction_choice_prompt() -> str:
    return (
        "Antes do login, escolha como voce quer extrair os arquivos.\n\n"
        "Responda com `pypdf`, `docling`, `docling-puro` ou `doc-csv`.\n\n"
        "`pypdf` funciona para PDFs.\n"
        "`docling` usa a pipeline atual do projeto, com logica especializada para planilhas.\n"
        "`docling-puro` usa apenas o DocumentConverter do Docling em todas as operacoes, para comparacao.\n"
        "`doc-csv` converte planilhas para CSV em memoria antes de gerar o markdown, para comparacao."
    )


def build_invalid_extraction_choice_message() -> str:
    return "Opcao invalida. Responda com `pypdf`, `docling`, `docling-puro` ou `doc-csv`."


def build_extraction_selected_message(extraction_method: str) -> str:
    label = format_extraction_method(extraction_method)
    return f"Perfeito. Vou usar `{extraction_method}` ({label}) nesta importacao."
