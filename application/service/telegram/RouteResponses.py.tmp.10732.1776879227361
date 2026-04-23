"""Response builders for collection-routing replies."""
# Simple: Create chat responses about loaded documents

from __future__ import annotations

from .RouteConstants import IMAGE_FILE_EXTENSIONS, PDF_MIME_TYPE, SPREADSHEET_MIME_TYPES
from .RouteIntents import detect_collection_intent, is_collection_follow_up, normalize_text


def build_collection_route_response(question: str, session: dict) -> str | None:
    files = session.get("loaded_files") or []
    if not files:
        return None

    normalized = normalize_text(question)
    if not normalized:
        return None

    intent = detect_collection_intent(normalized)
    if intent is None and is_collection_follow_up(normalized):
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
        return build_typed_files_answer(session, files, "planilhas", is_spreadsheet_file)
    if intent == "images":
        return build_typed_files_answer(session, files, "imagens", is_image_file)
    if intent == "pdfs":
        return build_typed_files_answer(
            session,
            files,
            "PDFs",
            lambda item: (item.get("mime_type") or "").lower() == PDF_MIME_TYPE,
        )
    if intent == "files":
        return build_all_files_answer(files, session.get("loaded_folder_name"))
    return None


def build_all_files_answer(files: list[dict], folder_name: str | None) -> str:
    folder = folder_name or "a pasta carregada"
    lines = [
        f"Carreguei {format_count(len(files), 'arquivo', 'arquivos')} da pasta '{folder}':",
        "",
        *enumerate_file_names(files),
    ]
    summary = build_type_summary(files)
    if summary:
        lines.extend(["", f"Resumo por tipo: {summary}."])
    return "\n".join(lines)


def build_typed_files_answer(session: dict, files: list[dict], label_plural: str, predicate) -> str:
    filtered_files = [item for item in files if predicate(item)]
    folder = session.get("loaded_folder_name") or "a pasta carregada"
    if not filtered_files:
        return f"Não encontrei {label_plural} na pasta '{folder}'."

    singular_map = {
        "planilhas": "planilha",
        "imagens": "imagem",
        "PDFs": "PDF",
    }
    singular = singular_map.get(label_plural, label_plural.rstrip("s"))
    lines = [
        f"Encontrei {format_count(len(filtered_files), singular, label_plural)} na pasta '{folder}':",
        "",
        *enumerate_file_names(filtered_files),
    ]
    return "\n".join(lines)


def build_type_summary(files: list[dict]) -> str:
    counts = {"PDFs": 0, "planilhas": 0, "imagens": 0, "outros": 0}
    singular_map = {
        "PDFs": "PDF",
        "planilhas": "planilha",
        "imagens": "imagem",
        "outros": "outro",
    }
    for item in files:
        if is_spreadsheet_file(item):
            counts["planilhas"] += 1
        elif is_image_file(item):
            counts["imagens"] += 1
        elif (item.get("mime_type") or "").lower() == PDF_MIME_TYPE:
            counts["PDFs"] += 1
        else:
            counts["outros"] += 1

    parts = [
        format_count(count, singular_map[label], label)
        for label, count in counts.items()
        if count
    ]
    return ", ".join(parts)


def enumerate_file_names(files: list[dict]) -> list[str]:
    return [f"{index}. {item.get('name', 'arquivo sem nome')}" for index, item in enumerate(files, start=1)]


def is_spreadsheet_file(item: dict) -> bool:
    return (item.get("mime_type") or "").lower() in SPREADSHEET_MIME_TYPES


def is_image_file(item: dict) -> bool:
    mime_type = (item.get("mime_type") or "").lower()
    if mime_type.startswith("image/"):
        return True
    file_name = item.get("name") or ""
    return any(file_name.lower().endswith(extension) for extension in IMAGE_FILE_EXTENSIONS)


def format_count(count: int, singular: str, plural: str) -> str:
    label = singular if count == 1 else plural
    return f"{count} {label}"
