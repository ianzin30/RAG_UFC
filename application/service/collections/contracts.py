from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EntityRecord:
    name: str
    role: str | None = None
    sheet_name: str | None = None
    row_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "sheet_name": self.sheet_name,
            "row_number": self.row_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EntityRecord":
        return cls(
            name=data.get("name") or "",
            role=data.get("role"),
            sheet_name=data.get("sheet_name"),
            row_number=data.get("row_number"),
        )


@dataclass
class SpreadsheetRow:
    row_number: int | None = None
    pairs: list[dict[str, str]] = field(default_factory=list)
    entity: EntityRecord | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_number": self.row_number,
            "pairs": list(self.pairs),
            "entity": self.entity.to_dict() if self.entity else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpreadsheetRow":
        entity = data.get("entity")
        return cls(
            row_number=data.get("row_number"),
            pairs=list(data.get("pairs") or []),
            entity=EntityRecord.from_dict(entity) if entity else None,
        )


@dataclass
class SpreadsheetSheet:
    name: str
    summary_lines: list[str] = field(default_factory=list)
    column_profiles: list[str] = field(default_factory=list)
    people: list[EntityRecord] = field(default_factory=list)
    rows: list[SpreadsheetRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary_lines": list(self.summary_lines),
            "column_profiles": list(self.column_profiles),
            "people": [person.to_dict() for person in self.people],
            "rows": [row.to_dict() for row in self.rows],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpreadsheetSheet":
        return cls(
            name=data.get("name") or "Sheet",
            summary_lines=list(data.get("summary_lines") or []),
            column_profiles=list(data.get("column_profiles") or []),
            people=[EntityRecord.from_dict(item) for item in data.get("people") or []],
            rows=[SpreadsheetRow.from_dict(item) for item in data.get("rows") or []],
        )


@dataclass
class SpreadsheetModel:
    format: str | None = None
    source_file: str | None = None
    summary_lines: list[str] = field(default_factory=list)
    sheets: list[SpreadsheetSheet] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "source_file": self.source_file,
            "summary_lines": list(self.summary_lines),
            "sheets": [sheet.to_dict() for sheet in self.sheets],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SpreadsheetModel | None":
        if not data:
            return None
        return cls(
            format=data.get("format"),
            source_file=data.get("source_file"),
            summary_lines=list(data.get("summary_lines") or []),
            sheets=[SpreadsheetSheet.from_dict(item) for item in data.get("sheets") or []],
        )

    def to_text(self) -> str:
        lines = []
        if self.source_file:
            lines.append(f"Arquivo da planilha: {self.source_file}")
        if self.format:
            lines.append(f"Formato: {self.format}")
        lines.extend(self.summary_lines)
        for sheet in self.sheets:
            lines.append(f"Aba: {sheet.name}")
            lines.extend(sheet.summary_lines)
            lines.extend(sheet.column_profiles)
            for person in sheet.people:
                entry = f"Pessoa: {person.name}"
                if person.role:
                    entry += f" | Funcao: {person.role}"
                if person.row_number is not None:
                    entry += f" | Linha: {person.row_number}"
                lines.append(entry)
            for row in sheet.rows:
                pairs_text = " | ".join(f"{pair['header']}={pair['value']}" for pair in row.pairs)
                if pairs_text:
                    lines.append(f"Registro: {pairs_text}")
        return "\n".join(line for line in lines if line).strip()


@dataclass
class DocumentSegment:
    segment_id: str
    kind: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "kind": self.kind,
            "content": self.content,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentSegment":
        return cls(
            segment_id=data.get("segment_id") or "",
            kind=data.get("kind") or "text",
            content=data.get("content") or "",
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class NormalizedDocument:
    document_id: str
    display_name: str
    document_type: str
    source_kind: str
    source_metadata: dict[str, Any]
    extraction_method: str
    content_markdown_path: str
    content_text: str
    summary: str
    structured_data: dict[str, Any] | None = None
    content_markdown: str = field(default="", repr=False)
    logical_item_id: str | None = None
    logical_item_name: str | None = None
    logical_item_kind: str | None = None
    catalog_visibility: str | None = None
    parent_document_id: str | None = None
    component_kind: str | None = None
    component_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "display_name": self.display_name,
            "document_type": self.document_type,
            "source_kind": self.source_kind,
            "source_metadata": dict(self.source_metadata),
            "extraction_method": self.extraction_method,
            "content_markdown_path": self.content_markdown_path,
            "content_text": self.content_text,
            "summary": self.summary,
            "structured_data": self.structured_data,
            "logical_item_id": self.logical_item_id,
            "logical_item_name": self.logical_item_name,
            "logical_item_kind": self.logical_item_kind,
            "catalog_visibility": self.catalog_visibility,
            "parent_document_id": self.parent_document_id,
            "component_kind": self.component_kind,
            "component_name": self.component_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], content_markdown: str = "") -> "NormalizedDocument":
        return cls(
            document_id=data.get("document_id") or "",
            display_name=data.get("display_name") or "",
            document_type=data.get("document_type") or "document",
            source_kind=data.get("source_kind") or "unknown",
            source_metadata=dict(data.get("source_metadata") or {}),
            extraction_method=data.get("extraction_method") or "unknown",
            content_markdown_path=data.get("content_markdown_path") or "",
            content_text=data.get("content_text") or "",
            summary=data.get("summary") or "",
            structured_data=data.get("structured_data"),
            content_markdown=content_markdown,
            logical_item_id=data.get("logical_item_id"),
            logical_item_name=data.get("logical_item_name"),
            logical_item_kind=data.get("logical_item_kind"),
            catalog_visibility=data.get("catalog_visibility"),
            parent_document_id=data.get("parent_document_id"),
            component_kind=data.get("component_kind"),
            component_name=data.get("component_name"),
        )


@dataclass
class CollectionDocumentEntry:
    document_id: str
    display_name: str
    document_type: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "display_name": self.display_name,
            "document_type": self.document_type,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CollectionDocumentEntry":
        return cls(
            document_id=data.get("document_id") or "",
            display_name=data.get("display_name") or "",
            document_type=data.get("document_type") or "document",
            summary=data.get("summary") or "",
        )


@dataclass
class CollectionManifest:
    collection_name: str
    source_kind: str
    created_at: str
    extraction_method: str
    documents: list[CollectionDocumentEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "source_kind": self.source_kind,
            "created_at": self.created_at,
            "extraction_method": self.extraction_method,
            "documents": [document.to_dict() for document in self.documents],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CollectionManifest":
        return cls(
            collection_name=data.get("collection_name") or "",
            source_kind=data.get("source_kind") or "unknown",
            created_at=data.get("created_at") or "",
            extraction_method=data.get("extraction_method") or "unknown",
            documents=[CollectionDocumentEntry.from_dict(item) for item in data.get("documents") or []],
        )


@dataclass
class NormalizedCollection:
    manifest: CollectionManifest
    documents: list[NormalizedDocument]


@dataclass
class QueryPlan:
    intent: str
    target_document_ids: list[str]
    requested_document_type: str | None
    needs_structured_lookup: bool
    resolved_query: str
    inventory_mode: str | None = None
    retrieval_profile: str = "default"
