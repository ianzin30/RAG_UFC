"""Structural text parents and token-aware children with stable provenance."""

import hashlib
import json
import re
from pathlib import Path
from .Models import Chunk


def stable_id(*parts):
    return hashlib.sha256(
        "\x1f".join(str(part) for part in parts).encode()
    ).hexdigest()[:24]


def build_document_chunks(documents, root, tokenizer, config, spreadsheet_builder):
    chunks, parents, catalog = [], {}, []
    seen = set()
    for document in documents:
        source = str(document.metadata["source"])
        relative = Path(source).resolve().relative_to(Path(root).resolve()).as_posix()
        if relative in seen:
            continue
        seen.add(relative)
        text = document.page_content
        sidecar = Path(source).with_suffix(".structure.json")
        structured = json.loads(sidecar.read_text()) if sidecar.exists() else {}
        if (
            structured
            and structured.get("markdown_sha256")
            != hashlib.sha256(text.encode()).hexdigest()
        ):
            raise ValueError(f"Stale structural sidecar: {relative}")
        doc_id = stable_id(relative)
        name = next(
            (line[2:].strip() for line in text.splitlines() if line.startswith("# ")),
            Path(source).name,
        )
        version = stable_id(text, structured)
        catalog.append(
            {"document_id": doc_id, "document_name": name, "relative_path": relative}
        )
        document.metadata.update(document_name=name)
        if (config.chunking_strategy == "markdown_blocks_v1"
                and "document type: spreadsheet" not in text.lower()):
            from .MarkdownBlocks import markdown_chunks
            new_chunks, new_parents = markdown_chunks(
                text, structured, tokenizer, config, doc_id, name, version,
                source, relative,
            )
            chunks.extend(new_chunks)
            parents.update(new_parents)
            continue
        if "document type: spreadsheet" in text.lower():
            items = spreadsheet_builder(document, "")
            sections = [
                (
                    str(item.metadata.get("sheet_name", "")),
                    item.page_content,
                    item.metadata,
                    [],
                )
                for item in items
            ]
        elif structured.get("sections"):
            sections = [
                (item.get("title", ""), item["text"], {}, item.get("provenance", []))
                for item in structured["sections"]
            ]
        else:
            sections = []
            heading, start = "", 0
            for match in re.finditer(r"(?m)^#{1,6}\s+(.+)$", text):
                if text[start : match.start()].strip():
                    sections.append(
                        (
                            heading,
                            text[start : match.start()].strip(),
                            {"text_start": start, "text_end": match.start()},
                            [],
                        )
                    )
                heading, start = match[1], match.end()
            if text[start:].strip():
                sections.append(
                    (
                        heading,
                        text[start:].strip(),
                        {"text_start": start, "text_end": len(text)},
                        [],
                    )
                )
        order = 0
        for section_index, (title, body, metadata, provenance) in enumerate(sections):
            encoded = tokenizer(
                body, add_special_tokens=False, return_offsets_mapping=True
            )
            offsets = encoded["offset_mapping"]
            # Spreadsheet records stay whole, retaining original column/row metadata.
            parent_size = (
                len(offsets) if metadata.get("chunk_kind") else config.parent_tokens
            )
            for parent_start in range(0, len(offsets), max(1, parent_size)):
                parent_end = min(len(offsets), parent_start + parent_size)
                parent_body = body[
                    offsets[parent_start][0] : offsets[parent_end - 1][1]
                ]
                # A heading often carries the semantic label for a very short
                # value (for example, "Coordenador na Instituição" followed by
                # a person's name).  Keep it in both retrieval and parent
                # context, rather than relying on a later heuristic to join
                # adjacent Markdown fragments.
                parent_text = (
                    f"{title}\n{parent_body}".strip() if title else parent_body
                )
                parent_id = stable_id(doc_id, version, section_index, parent_start)
                parents[parent_id] = parent_text
                child_size = (
                    len(offsets) if metadata.get("chunk_kind") else config.child_tokens
                )
                for child_start in range(parent_start, parent_end, max(1, child_size)):
                    child_end = min(parent_end, child_start + child_size)
                    child_body = body[
                        offsets[child_start][0] : offsets[child_end - 1][1]
                    ]
                    content = (
                        f"{title}\n{child_body}".strip() if title else child_body
                    )
                    chunks.append(
                        Chunk(
                            chunk_id=stable_id(parent_id, child_start, content),
                            document_id=doc_id,
                            document_name=name,
                            parent_id=parent_id,
                            text=content,
                            section_title=title,
                            chunk_kind=metadata.get("chunk_kind", "section_detail"),
                            chunk_order=order,
                            source=source,
                            relative_path=relative,
                            provenance=provenance,
                            metadata=metadata,
                        )
                    )
                    order += 1
    return chunks, parents, catalog
