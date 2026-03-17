EXTRACTION_METHOD_PYPDF = "pypdf"
EXTRACTION_METHOD_DOCLING = "docling"


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
    return None


def format_extraction_method(extraction_method: str | None) -> str:
    if extraction_method == EXTRACTION_METHOD_DOCLING:
        return "Docling"
    return "PyPDF"


def build_extraction_choice_prompt() -> str:
    return (
        "Antes do login, escolha como voce quer extrair os arquivos.\n\n"
        "Responda com `pypdf` ou `docling`.\n\n"
        "`pypdf` funciona para PDFs. `docling` suporta mais tipos de documento e preserva melhor a estrutura."
    )


def build_invalid_extraction_choice_message() -> str:
    return "Opcao invalida. Responda com `pypdf` ou `docling`."


def build_extraction_selected_message(extraction_method: str) -> str:
    label = format_extraction_method(extraction_method)
    return f"Perfeito. Vou usar `{extraction_method}` ({label}) nesta importacao."
