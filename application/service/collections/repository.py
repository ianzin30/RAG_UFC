from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .contracts import (
    CollectionDocumentEntry,
    CollectionManifest,
    NormalizedCollection,
    NormalizedDocument,
)


class CollectionRepository:
    def __init__(self, project_root: Path | None = None):
        root = project_root or Path(__file__).resolve().parents[3]
        self.project_root = root
        self.collections_root = self.project_root / "data" / "collections"

    def save_collection(
        self,
        collection_name: str,
        source_kind: str,
        extraction_method: str,
        documents: list[NormalizedDocument],
    ) -> CollectionManifest:
        collection_path = self.collections_root / collection_name
        documents_path = collection_path / "documents"

        if collection_path.exists():
            shutil.rmtree(collection_path)
        documents_path.mkdir(parents=True, exist_ok=True)

        manifest_documents = []
        for document in documents:
            relative_markdown_path = Path("documents") / f"{document.document_id}.md"
            relative_sidecar_path = Path("documents") / f"{document.document_id}.json"
            document.content_markdown_path = relative_markdown_path.as_posix()

            markdown_path = collection_path / relative_markdown_path
            markdown_path.write_text(self._render_markdown_export(document), encoding="utf-8")

            sidecar_path = collection_path / relative_sidecar_path
            sidecar_path.write_text(
                json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            manifest_documents.append(
                CollectionDocumentEntry(
                    document_id=document.document_id,
                    display_name=document.display_name,
                    document_type=document.document_type,
                    summary=document.summary,
                )
            )

        manifest = CollectionManifest(
            collection_name=collection_name,
            source_kind=source_kind,
            created_at=datetime.now(timezone.utc).isoformat(),
            extraction_method=extraction_method,
            documents=manifest_documents,
        )
        manifest_path = collection_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def load_collection(self, collection_name: str) -> NormalizedCollection:
        collection_path = self.collections_root / collection_name
        manifest_path = collection_path / "manifest.json"
        if not manifest_path.exists():
            raise Exception(
                f"Collection '{collection_name}' is not in the normalized format. "
                "Regenerate it so it includes manifest.json and document sidecars."
            )

        manifest = CollectionManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        documents = []
        for entry in manifest.documents:
            sidecar_path = collection_path / "documents" / f"{entry.document_id}.json"
            if not sidecar_path.exists():
                raise Exception(
                    f"Collection '{collection_name}' is inconsistent. Missing sidecar for document '{entry.document_id}'."
                )

            document_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            markdown_path = collection_path / (document_data.get("content_markdown_path") or "")
            content_markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
            documents.append(NormalizedDocument.from_dict(document_data, content_markdown=content_markdown))

        return NormalizedCollection(manifest=manifest, documents=documents)

    def _render_markdown_export(self, document: NormalizedDocument) -> str:
        header_lines = [
            f"# {document.display_name}",
            "",
            f"Source kind: {document.source_kind}",
            f"Extraction method: {document.extraction_method}",
            f"Document type: {document.document_type}",
        ]
        if document.summary:
            header_lines.extend(["", f"Summary: {document.summary}"])

        body = document.content_markdown.strip()
        if body:
            header_lines.extend(["", body])

        return "\n".join(header_lines).strip() + "\n"
