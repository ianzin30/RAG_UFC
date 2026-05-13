"""Safe markdown preview popups for extracted collection files."""

from __future__ import annotations

from hashlib import sha256
from html import escape
from pathlib import Path
import re

from markdown_it import MarkdownIt

from presentation.shared.Config import PROJECT_ROOT


_MARKDOWN_RENDERER = MarkdownIt("commonmark", {"html": False}).enable("table")


def _collections_root(collections_root: Path | None = None) -> Path:
    return (collections_root or PROJECT_ROOT / "data" / "collections").resolve()


def _is_safe_markdown_path(path: Path, collections_root: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return resolved.is_relative_to(collections_root) and resolved.suffix.lower() == ".md"


def _read_heading(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[:8]:
            heading = line.strip()
            if heading.startswith("# "):
                return heading[2:].strip()
    except OSError:
        return ""
    return ""


def _normalize_match_value(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _candidate_from_source(source_value: object, collections_root: Path) -> Path | None:
    raw_source = str(source_value or "").strip()
    if not raw_source:
        return None

    source_path = Path(raw_source)
    candidates = [source_path] if source_path.is_absolute() else [
        PROJECT_ROOT / source_path,
        collections_root / source_path,
    ]
    for candidate in candidates:
        if _is_safe_markdown_path(candidate, collections_root):
            return candidate.resolve()
    return None


def resolve_markdown_preview_path(
    document: dict[str, object] | None,
    collections_root: Path | None = None,
) -> Path | None:
    """Resolve a source/sidebar document to a safe Markdown file under data/collections."""
    document = document or {}
    root = _collections_root(collections_root)

    relative_path = str(document.get("relative_path") or "").strip()
    if relative_path:
        candidate = root / relative_path
        if _is_safe_markdown_path(candidate, root):
            return candidate.resolve()

    source_candidate = _candidate_from_source(document.get("source"), root)
    if source_candidate is not None:
        return source_candidate

    source_name = _normalize_match_value(document.get("source_name"))
    document_name = _normalize_match_value(document.get("document_name") or document.get("file_name"))
    document_stem = _normalize_match_value(Path(document_name).stem) if document_name else ""
    for path in sorted(root.rglob("*.md"), key=lambda item: item.relative_to(root).as_posix().lower()):
        path_name = _normalize_match_value(path.name)
        path_stem = _normalize_match_value(path.stem)
        heading = _normalize_match_value(_read_heading(path))
        if source_name and source_name == path_name:
            return path.resolve()
        if document_name and document_name in {path_name, path_stem, heading}:
            return path.resolve()
        if document_stem and document_stem in {path_stem, heading}:
            return path.resolve()
    return None


def _preview_id(prefix: str, label: str, path: Path | None, document: dict[str, object] | None) -> str:
    source = str(path or (document or {}).get("relative_path") or (document or {}).get("source") or label)
    digest = sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"markdown-preview-{re.sub(r'[^a-zA-Z0-9_-]+', '-', prefix).strip('-')}-{digest}"


def _render_markdown_file(path: Path | None) -> str:
    if path is None:
        return '<p class="markdown-preview-error">Nao foi possivel localizar o Markdown extraido deste arquivo.</p>'
    try:
        markdown_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return f'<p class="markdown-preview-error">Nao foi possivel abrir o Markdown: {escape(str(exc))}</p>'
    return _MARKDOWN_RENDERER.render(markdown_text)


def render_markdown_preview_link(
    *,
    label: str,
    document: dict[str, object] | None,
    prefix: str,
    class_name: str = "markdown-preview-link",
    close_href: str = "#markdown-preview-closed",
    collections_root: Path | None = None,
) -> str:
    """Return a no-rerun anchor and matching CSS-target modal for a Markdown preview."""
    path = resolve_markdown_preview_path(document, collections_root)
    modal_id = _preview_id(prefix, label, path, document)
    title = label.strip() or (path.name if path else "Arquivo")
    relative_label = ""
    if path is not None:
        try:
            relative_label = path.relative_to(_collections_root(collections_root)).as_posix()
        except ValueError:
            relative_label = path.name
    rendered_markdown = _render_markdown_file(path)
    safe_close_href = close_href if str(close_href).startswith("#") else "#markdown-preview-closed"

    escaped_modal_id = escape(modal_id, quote=True)
    escaped_title = escape(title)
    escaped_relative_label = escape(relative_label)
    escaped_class_name = escape(class_name, quote=True)
    escaped_close_href = escape(safe_close_href, quote=True)
    return (
        f'<a class="{escaped_class_name}" href="#{escaped_modal_id}" title="Abrir Markdown extraido">'
        f"{escaped_title}"
        "</a>"
        f'<div id="{escaped_modal_id}" class="markdown-preview-modal" aria-hidden="true">'
        f'<a class="markdown-preview-backdrop" href="{escaped_close_href}" aria-label="Fechar preview"></a>'
        f'<section class="markdown-preview-panel" role="dialog" aria-modal="true" aria-labelledby="{escaped_modal_id}-title">'
        '<header class="markdown-preview-header">'
        "<div>"
        f'<div id="{escaped_modal_id}-title" class="markdown-preview-title">{escaped_title}</div>'
        f'<div class="markdown-preview-path">{escaped_relative_label}</div>'
        "</div>"
        f'<a class="markdown-preview-close" href="{escaped_close_href}" aria-label="Fechar preview">&times;</a>'
        "</header>"
        f'<div class="markdown-preview-body">{rendered_markdown}</div>'
        "</section>"
        "</div>"
    )
