"""String-compatible ingestion result preserving textual provenance."""

import hashlib
import json
from pathlib import Path


class ExtractedText(str):
    def __new__(cls, text, sections=()):
        value = super().__new__(cls, text)
        value.sections = list(sections)
        return value

    def strip(self, chars=None):
        return ExtractedText(super().strip(chars), self.sections)


def write_structure_sidecar(output_path, extracted):
    sections = getattr(extracted, "sections", None)
    path = Path(output_path).with_suffix(".structure.json")
    if not sections:
        if path.exists():
            path.unlink()
        return
    markdown = Path(output_path).read_bytes()
    payload = {
        "version": 2,
        "markdown_sha256": hashlib.sha256(markdown).hexdigest(),
        "sections": sections,
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def docling_text(document):
    sections = []
    title = ""
    for item, _ in document.iterate_items():
        label = str(getattr(item, "label", ""))
        text = getattr(item, "text", "")
        if "section_header" in label or "title" in label:
            title = text
        elif text:
            sections.append(
                {
                    "title": title,
                    "text": text,
                    "provenance": [
                        prov.model_dump(mode="json")
                        for prov in getattr(item, "prov", [])
                    ],
                }
            )
        elif "table" in label:
            sections.append(
                {
                    "title": title,
                    "text": item.export_to_markdown(doc=document),
                    "provenance": [
                        prov.model_dump(mode="json")
                        for prov in getattr(item, "prov", [])
                    ],
                }
            )
    return ExtractedText(document.export_to_markdown().strip(), sections)
