import re
import unicodedata


SPREADSHEET_MIME_TYPES = {
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
}
IMAGE_FILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
PDF_MIME_TYPE = "application/pdf"

INVENTORY_VERBS = (
    "qual",
    "quais",
    "quantos",
    "quantas",
    "liste",
    "listar",
    "mostre",
    "mostrar",
    "tem",
    "ha",
    "exist",
    "nomes",
    "carregou",
    "carregados",
    "carregadas",
    "usado",
    "usada",
    "veio",
    "vieram",
    "origem",
    "viu",
)


def ensure_collection_session(session: dict) -> dict:
    session.setdefault("loaded_files", [])
    session.setdefault("loaded_folder_name", None)
    session.setdefault("last_collection_intent", None)
    return session


def clear_collection_session(session: dict) -> None:
    session["loaded_files"] = []
    session["loaded_folder_name"] = None
    session["last_collection_intent"] = None


def update_collection_session(session: dict, result: dict) -> None:
    session["loaded_files"] = list(result.get("files") or [])
    session["loaded_folder_name"] = result.get("folder_name")
    session["last_collection_intent"] = None


def build_collection_route_response(question: str, session: dict) -> str | None:
    files = session.get("loaded_files") or []
    if not files:
        return None

    normalized = _normalize_text(question)
    if not normalized:
        return None

    intent = _detect_collection_intent(normalized)
    if intent is None and _is_collection_follow_up(normalized):
        intent = session.get("last_collection_intent")

    if not intent:
        return None

    session["last_collection_intent"] = intent

    if intent == "extractor":
        extraction_method = session.get("extraction_method") or "desconhecido"
        return f"O extrator usado na coleção atual foi `{extraction_method}`."

    if intent == "folder":
        folder_name = session.get("loaded_folder_name") or "não identificada"
        return f"Os arquivos atuais vieram da pasta '{folder_name}'."

    if intent == "spreadsheets":
        return _build_typed_files_answer(
            files=files,
            folder_name=session.get("loaded_folder_name"),
            label_plural="planilhas",
            predicate=_is_spreadsheet_file,
        )

    if intent == "images":
        return _build_typed_files_answer(
            files=files,
            folder_name=session.get("loaded_folder_name"),
            label_plural="imagens",
            predicate=_is_image_file,
        )

    if intent == "pdfs":
        return _build_typed_files_answer(
            files=files,
            folder_name=session.get("loaded_folder_name"),
            label_plural="PDFs",
            predicate=lambda item: (item.get("mime_type") or "").lower() == PDF_MIME_TYPE,
        )

    if intent == "files":
        return _build_all_files_answer(files, session.get("loaded_folder_name"))

    return None


def _build_all_files_answer(files: list[dict], folder_name: str | None) -> str:
    folder = folder_name or "a pasta carregada"
    lines = [
        f"Carreguei {_format_count(len(files), 'arquivo', 'arquivos')} da pasta '{folder}':",
        "",
        *_enumerate_file_names(files),
    ]

    summary = _build_type_summary(files)
    if summary:
        lines.extend(["", f"Resumo por tipo: {summary}."])

    return "\n".join(lines)


def _build_typed_files_answer(
    files: list[dict],
    folder_name: str | None,
    label_plural: str,
    predicate,
) -> str:
    filtered_files = [item for item in files if predicate(item)]
    folder = folder_name or "a pasta carregada"
    if not filtered_files:
        return f"Não encontrei {label_plural} na pasta '{folder}'."

    singular_map = {
        "planilhas": "planilha",
        "imagens": "imagem",
        "PDFs": "PDF",
    }
    singular = singular_map.get(label_plural, label_plural.rstrip("s"))
    lines = [
        f"Encontrei {_format_count(len(filtered_files), singular, label_plural)} na pasta '{folder}':",
        "",
        *_enumerate_file_names(filtered_files),
    ]
    return "\n".join(lines)


def _build_type_summary(files: list[dict]) -> str:
    counts = {"PDFs": 0, "planilhas": 0, "imagens": 0, "outros": 0}
    singular_map = {
        "PDFs": "PDF",
        "planilhas": "planilha",
        "imagens": "imagem",
        "outros": "outro",
    }
    for item in files:
        if _is_spreadsheet_file(item):
            counts["planilhas"] += 1
        elif _is_image_file(item):
            counts["imagens"] += 1
        elif (item.get("mime_type") or "").lower() == PDF_MIME_TYPE:
            counts["PDFs"] += 1
        else:
            counts["outros"] += 1

    parts = [
        _format_count(
            count,
            singular_map[label],
            label,
        )
        for label, count in counts.items()
        if count
    ]
    return ", ".join(parts)


def _enumerate_file_names(files: list[dict]) -> list[str]:
    return [f"{index}. {item.get('name', 'arquivo sem nome')}" for index, item in enumerate(files, start=1)]


def _is_spreadsheet_file(item: dict) -> bool:
    mime_type = (item.get("mime_type") or "").lower()
    return mime_type in SPREADSHEET_MIME_TYPES


def _is_image_file(item: dict) -> bool:
    mime_type = (item.get("mime_type") or "").lower()
    if mime_type.startswith("image/"):
        return True

    file_name = item.get("name") or ""
    return any(file_name.lower().endswith(extension) for extension in IMAGE_FILE_EXTENSIONS)


def _is_files_question(normalized: str) -> bool:
    nouns = ("arquivo", "arquivos", "documento", "documentos")
    return _is_inventory_question(normalized, nouns)


def _is_spreadsheet_question(normalized: str) -> bool:
    nouns = ("planilha", "planilhas", "excel", "excels", "xls", ".xls", ".xlsx", ".csv", "sheet", "sheets")
    return _is_inventory_question(normalized, nouns)


def _is_image_question(normalized: str) -> bool:
    nouns = ("imagem", "imagens", ".png", ".jpg", ".jpeg", ".webp", "foto", "fotos")
    return _is_inventory_question(normalized, nouns)


def _is_pdf_question(normalized: str) -> bool:
    nouns = ("pdf", "pdfs")
    return _is_inventory_question(normalized, nouns)


def _is_extractor_question(normalized: str) -> bool:
    nouns = ("extrator", "extractor", "metodo de extracao", "metodo de ingestao")
    return _is_inventory_question(normalized, nouns)


def _is_folder_question(normalized: str) -> bool:
    folder_patterns = (
        r"\bde qual pasta\b",
        r"\bqual pasta\b",
        r"\bnome da pasta\b",
        r"\bpasta de origem\b",
        r"\borigem da pasta\b",
        r"\bvieram da pasta\b",
        r"\bveio da pasta\b",
        r"\bpasta do google drive\b",
    )
    return any(re.search(pattern, normalized) for pattern in folder_patterns)


def _detect_collection_intent(normalized: str) -> str | None:
    if _is_spreadsheet_question(normalized):
        return "spreadsheets"
    if _is_image_question(normalized):
        return "images"
    if _is_pdf_question(normalized):
        return "pdfs"
    if _is_extractor_question(normalized):
        return "extractor"
    if _is_folder_question(normalized):
        return "folder"
    if _is_files_question(normalized):
        return "files"
    return None


def _is_collection_follow_up(normalized: str) -> bool:
    relaxed = re.sub(r"[^a-z0-9\s]+", " ", normalized)
    relaxed = re.sub(r"\s+", " ", relaxed).strip()
    if len(relaxed.split()) > 8:
        return False

    follow_up_patterns = (
        r"^(e|mas|certo|ok|beleza|perfeito|entendi)( mas)?( quais( sao)?| qual( deles| delas)?| os nomes| as planilhas| os pdfs| as imagens)?$",
        r"^quais( sao)?\??$",
        r"^qual( deles| delas)?\??$",
        r"^e quais( sao)?\??$",
        r"^mas quais( sao)?\??$",
        r"^os nomes\??$",
    )
    return any(re.search(pattern, relaxed) for pattern in follow_up_patterns)


def _is_inventory_question(normalized: str, nouns: tuple[str, ...]) -> bool:
    if not any(noun in normalized for noun in nouns):
        return False
    return any(re.search(rf"\b{verb}", normalized) for verb in INVENTORY_VERBS)


def _normalize_text(text: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", (text or "").lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _format_count(count: int, singular: str, plural: str) -> str:
    label = singular if count == 1 else plural
    return f"{count} {label}"
