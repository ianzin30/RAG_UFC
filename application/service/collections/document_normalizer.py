from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from .contracts import NormalizedDocument, SpreadsheetModel


SPREADSHEET_SUFFIXES = {".xlsx", ".csv"}
PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}
PRESENTATION_SUFFIXES = {".ppt", ".pptx"}
TEXT_DOCUMENT_SUFFIXES = {".doc", ".docx", ".html", ".md", ".txt"}


class DocumentNormalizer:
    def normalize_drive_document(
        self,
        index: int,
        drive_file: dict,
        extraction_method: str,
        content_markdown: str,
        spreadsheet_model: SpreadsheetModel | None = None,
    ) -> NormalizedDocument:
        display_name = drive_file.get("name") or f"document_{index}"
        document_type = self.infer_document_type(display_name)
        content_text = spreadsheet_model.to_text() if spreadsheet_model else self.normalize_text(content_markdown)
        summary = self.extract_summary(content_text)
        document_id = self.build_document_id(index, display_name)

        return NormalizedDocument(
            document_id=document_id,
            display_name=display_name,
            document_type=document_type,
            source_kind="google_drive",
            source_metadata={
                "id": drive_file.get("id"),
                "mime_type": drive_file.get("mimeType"),
                "name": display_name,
            },
            extraction_method=extraction_method,
            content_markdown_path="",
            content_text=content_text,
            summary=summary,
            structured_data=spreadsheet_model.to_dict() if spreadsheet_model else None,
            content_markdown=content_markdown.strip(),
        )

    def normalize_scraped_page(
        self,
        index: int,
        content_markdown: str,
        source_url: str | None,
        extraction_method: str = "firecrawl",
    ) -> NormalizedDocument:
        display_name = self._build_scraped_display_name(index, source_url)
        document_id = self.build_document_id(index, display_name)
        content_text = self.normalize_text(content_markdown)
        summary = self.extract_summary(content_text)

        return NormalizedDocument(
            document_id=document_id,
            display_name=display_name,
            document_type="text_document",
            source_kind="scraped_web",
            source_metadata={"url": source_url} if source_url else {},
            extraction_method=extraction_method,
            content_markdown_path="",
            content_text=content_text,
            summary=summary,
            structured_data=None,
            content_markdown=content_markdown.strip(),
        )

    def build_document_id(self, index: int, display_name: str) -> str:
        stem = Path(display_name).stem or display_name or f"document_{index}"
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or f"document_{index}"
        return f"{index:02d}_{safe_stem}"

    def infer_document_type(self, display_name: str) -> str:
        suffix = Path(display_name or "").suffix.lower()
        if suffix in SPREADSHEET_SUFFIXES:
            return "spreadsheet"
        if suffix in PDF_SUFFIXES:
            return "pdf"
        if suffix in IMAGE_SUFFIXES:
            return "image"
        if suffix in PRESENTATION_SUFFIXES:
            return "presentation"
        if suffix in TEXT_DOCUMENT_SUFFIXES:
            return "text_document"
        return "document"

    def normalize_text(self, text: str) -> str:
        cleaned = re.sub(r"<!--.*?-->", " ", text or "", flags=re.DOTALL)
        lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.replace("\r\n", "\n").split("\n")]
        return "\n".join(line for line in lines if line)

    def extract_summary(self, text: str, max_lines: int = 3) -> str:
        if not text:
            return ""
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped:
                continue
            if lowered.startswith("source kind:") or lowered.startswith("extraction method:"):
                continue
            lines.append(stripped)
            if len(lines) >= max_lines:
                break
        return " ".join(lines[:max_lines]).strip()

    def _build_scraped_display_name(self, index: int, source_url: str | None) -> str:
        if not source_url:
            return f"page_{index}.md"

        parsed = urlparse(source_url)
        path = parsed.path.rstrip("/")
        if not path or path == "/":
            label = parsed.netloc or f"page_{index}"
        else:
            label = path.rsplit("/", 1)[-1] or parsed.netloc or f"page_{index}"
        safe_label = re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("._") or f"page_{index}"
        if not safe_label.endswith(".md"):
            safe_label = f"{safe_label}.md"
        return safe_label
