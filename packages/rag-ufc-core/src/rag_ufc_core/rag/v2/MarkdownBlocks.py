"""Contiguous original Markdown spans. No generated text or overlap."""

import re
import html
from .Models import Chunk
from .Documents import stable_id


def normalized_offsets(text):
    """Presentation normalization with raw start/end positions for provenance."""
    omitted = set()
    for m in re.finditer(r"(?m)^#{1,6}\s+", text):
        omitted.update(range(m.start(), m.end()))
    chars, starts, ends = [], [], []
    for m in re.finditer(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);|\s+|.", text, re.S):
        if m.start() in omitted:
            continue
        value = html.unescape(m[0])
        for c in value:
            if c.isspace():
                if chars and chars[-1] != ' ':
                    chars.append(' '); starts.append(m.start()); ends.append(m.end())
            else:
                chars.append(c); starts.append(m.start()); ends.append(m.end())
    if chars and chars[-1] == ' ':
        chars.pop(); starts.pop(); ends.pop()
    return ''.join(chars), starts, ends


def block_spans(text):
    """Paragraphs/tables with consecutive headings attached to following content."""
    # The newline expression also accepts CRLF and blank lines with spaces.
    starts = sorted({0, *[m.end() for m in re.finditer(r"\n[ \t]*\n+", text)
                         if m.end() < len(text)]})
    spans, pending = [], None
    for start, end in zip(starts, starts[1:] + [len(text)]):
        body = text[start:end].strip()
        if not body:
            continue
        heading = all(re.match(r"^#{1,6}\s+", line)
                      for line in body.splitlines() if line.strip())
        if heading:
            if pending is None:
                pending = start
        else:
            spans.append((pending if pending is not None else start, end))
            pending = None
    if pending is not None:
        spans.append((pending, len(text)))
    return spans


def token_spans(text, start, end, limit, tokenizer):
    """Split by BGE offsets; include whitespace and verify re-encoded limits."""
    cursor = start
    while cursor < end:
        offsets = tokenizer(text[cursor:end], add_special_tokens=False,
                            return_offsets_mapping=True)["offset_mapping"]
        if len(offsets) <= limit:
            yield cursor, end
            break
        stop = cursor + offsets[limit][0]
        # Re-encoding at a boundary can change a token; shrink rather than truncate.
        while len(tokenizer(text[cursor:stop], add_special_tokens=False)["input_ids"]) > limit:
            stop = cursor + offsets[limit - 1][0]
            limit -= 1
        if stop <= cursor:
            raise ValueError("Tokenizer cannot split Markdown without losing text")
        yield cursor, stop
        cursor = stop


def markdown_chunks(text, structured, tokenizer, config, doc_id, name, version,
                    source, relative):
    count = lambda a, b: len(tokenizer(text[a:b], add_special_tokens=False)["input_ids"])
    pieces = []
    for a, b in block_spans(text):
        pieces.extend(token_spans(text, a, b, config.parent_tokens, tokenizer))
    grouped = []
    for a, b in pieces:
        if grouped and count(grouped[-1][0], b) <= config.parent_tokens:
            grouped[-1] = (grouped[-1][0], b)
        else:
            grouped.append((a, b))
    # Only unique original matches carry page/box metadata. Escaping and spaces
    # are presentation; the map retains the actual Markdown positions.
    provenance = []
    normalized, starts, ends = normalized_offsets(text)
    for section in structured.get("sections", []):
        body = normalized_offsets(section["text"])[0]
        a = normalized.find(body) if body else -1
        if a >= 0 and normalized.find(body, a + 1) < 0:
            provenance.append((starts[a], ends[a + len(body) - 1], section.get("provenance", [])))
    chunks, parents = [], {}
    for a, b in grouped:
        parent_id = stable_id(doc_id, version, "markdown_blocks_v1", a, b)
        parents[parent_id] = text[a:b]
        for c, d in token_spans(text, a, b, config.child_tokens, tokenizer):
            prov = [p for x, y, values in provenance if x < d and c < y
                    # A partial multipage item cannot identify the child page.
                    if len({p.get('page_no') for p in values}) <= 1 or (c <= x and y <= d)
                    for p in values]
            unique = {str(p): p for p in prov}
            chunks.append(Chunk(
                chunk_id=stable_id(parent_id, c, d), document_id=doc_id,
                document_name=name, parent_id=parent_id, text=text[c:d],
                section_title="", chunk_kind="markdown_block", chunk_order=len(chunks),
                source=source, relative_path=relative, provenance=list(unique.values()),
                metadata={"chunking_strategy": "markdown_blocks_v1",
                          "source_start": c, "source_end": d,
                          "parent_source_start": a, "parent_source_end": b,
                          "source_sha256": __import__('hashlib').sha256(text.encode()).hexdigest()},
            ))
    return chunks, parents
