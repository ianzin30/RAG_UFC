"""Markdown collection loading and content hashes, independent of retrieval."""

import hashlib
from pathlib import Path
from langchain_core.documents import Document


class CollectionStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _files(self, names):
        for name in names:
            # The upload surface represents all local collections, as in V1/V2.
            path = self.root if name in {"__root__", "uploaded_files"} else self.root / name
            if not path.exists():
                raise ValueError(f"Collection '{name}' not found.")
            files = sorted(p for p in path.rglob("*.md") if p.is_file())
            if not files:
                raise ValueError(f"No documents found in collection '{name}'.")
            yield name, files

    def enumerate(self, names):
        records = {}
        for _, files in self._files(names):
            for path in files:
                relative = path.relative_to(self.root).as_posix()
                records[relative] = {
                    "relative_path": relative,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
        return [records[key] for key in sorted(records)]

    def load(self, names):
        documents = []
        for name, files in self._files(names):
            for path in files:
                documents.append(Document(
                    page_content=path.read_text(encoding="utf-8"),
                    metadata={"source": str(path), "collection_name": name},
                ))
        return documents
