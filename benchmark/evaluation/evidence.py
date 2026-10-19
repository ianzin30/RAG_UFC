"""Frozen, source-position evidence coverage; never accept ambiguous occurrences.

Whitespace, HTML entity escaping and heading markers are presentation, not evidence. Legacy
synthetic headings count only when the corresponding real heading is verified.
"""

import hashlib
import html
import json
import re
from pathlib import Path
from benchmark.evaluation.literal import canonical

VERSION = "evidence_v2"


def occurrences(source, needle):
    positions, cursor = [], 0
    while needle:
        cursor = source.find(needle, cursor)
        if cursor < 0:
            break
        positions.append((cursor, cursor + len(needle)))
        cursor += 1
    return positions


def normalized(text):
    """Canonical text and its exact raw-character positions."""
    skip = set()
    for m in re.finditer(r"(?m)^#{1,6}\s+", text):
        skip.update(range(m.start(), m.end()))
    chars, indices = [], []
    units, cursor = [], 0
    for match in re.finditer(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);", text):
        units.extend((i, text[i]) for i in range(cursor, match.start()))
        units.extend((match.start(), c) for c in html.unescape(match[0]))
        cursor = match.end()
    units.extend((i, text[i]) for i in range(cursor, len(text)))
    for i, c in units:
        if i in skip:
            continue
        if c.isspace():
            if chars and chars[-1] != " ":
                chars.append(" "); indices.append(i)
        else:
            chars.append(c); indices.append(i)
    if chars and chars[-1] == " ":
        chars.pop(); indices.pop()
    return "".join(chars), indices


def source_end(raw, position):
    entity = re.match(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);", raw[position:])
    return position + len(entity[0]) if entity else position + 1


def freeze_rules(anchors, root):
    audited = {"AFO_DATES", "SAAR_DATES", "SAAR_DASHBOARD", "SAAR_NAME", "AFO_NAME", "RACK_NAME"}
    rules = {"version": VERSION, "definition": "all explicit requirements at verified original positions; ambiguous source mappings receive no credit", "anchors": {}}
    for aid, anchor in anchors.items():
        path = root / anchor["document"]
        raw = path.read_text()
        text, indices = normalized(raw)
        quote = normalized(anchor["quote"])[0]
        matches = occurrences(text, quote)
        if len(matches) != 1:
            raise ValueError(f"Gold anchor needs manual audit: {aid}: {len(matches)} occurrences")
        a, b = matches[0]
        if aid in {"AFO_NAME", "RACK_NAME", "SAAR_NAME"}:
            # Identity is the frozen correct document, with a verified role/name
            # pair. Project-title fragments are not required a second time.
            role = "Coordenador na Instituição"
            local = quote.index(role)
            requirements = [("role_and_name", a + local, b)]
        elif aid in {"AFO_DATES", "SAAR_DATES"}:
            first = quote.index("Data de início:")
            second = quote.index("Data de estimada de término:")
            requirements = [("start_label_value", a + first, a + second),
                            ("end_label_value", a + second, b)]
        else:
            requirements = [("complete_factual_span", a, b)]
        rules["anchors"][aid] = {
            "document": anchor["document"], "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "audited": aid in audited, "section": anchor["section"],
            "quote_source_start": indices[a], "quote_source_end": source_end(raw, indices[b - 1]),
            "requirements": [{"name": name, "normalized_start": x, "normalized_end": y,
                              "source_start": indices[x], "source_end": source_end(raw, indices[y - 1]),
                              "text": text[x:y]} for name, x, y in requirements],
            "audit_note": ("Correct document plus the original coordinator role/name relation"
                           if aid.endswith("_NAME") and aid in audited else
                           "Label/value at audited duration location; repeated dates elsewhere do not qualify"
                           if aid.endswith("_DATES") and aid in audited else
                           "All information required, including across fragments; synthetic headings cannot add facts"),
        }
    return rules


class SourceAligner:
    def __init__(self, root, rules):
        self.root, self.rules = Path(root), rules
        self.sources, self.sections, self.headings, self.cache = {}, {}, {}, {}
        for name in {a["document"] for a in rules["anchors"].values()}:
            path = self.root / name
            raw = path.read_text()
            text, mapping = normalized(raw)
            expected = next(a["source_sha256"] for a in rules["anchors"].values() if a["document"] == name)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Frozen evaluation source changed: {name}")
            self.sources[name] = (raw, text, mapping)
            self.headings[name] = [(m.start(), m.end(), canonical(m[1]))
                                   for m in re.finditer(r"(?m)^#{1,6}\s+(.+)$", raw)]
            sidecar = path.with_suffix(".structure.json")
            sections = json.loads(sidecar.read_text()).get("sections", []) if sidecar.exists() else []
            if sidecar.exists() and json.loads(sidecar.read_text()).get("markdown_sha256") != expected:
                raise ValueError(f"Stale sidecar in evaluation: {name}")
            # Monotonic lower/upper bounds, rather than choosing the first match.
            # Only locations identical in both passes are proven by source order.
            all_matches = [occurrences(text, normalized(s["text"])[0]) for s in sections]
            low, high, cursor = [], [], 0
            for matches in all_matches:
                chosen = next((x for x in matches if x[0] >= cursor), None)
                low.append(chosen)
                if chosen: cursor = chosen[1]
            cursor = len(text)
            for matches in reversed(all_matches):
                chosen = next((x for x in reversed(matches) if x[1] <= cursor), None)
                high.append(chosen)
                if chosen: cursor = chosen[0]
            self.sections[name] = [(s, lo) for s, lo, hi in zip(sections, low, reversed(high)) if lo is not None and lo == hi]

    def align(self, entry, parent=True):
        name = Path(entry.get("relative_path", "")).name
        if name not in self.sources:
            return {"document": name, "spans": [], "status": "unannotated_document"}
        value = str(entry.get("excerpt") or entry.get("text") or "")
        metadata = entry.get("metadata", {})
        title = entry.get("section_title", "")
        key = (name, value, title, json.dumps(metadata, sort_keys=True), json.dumps(entry.get("provenance", []), sort_keys=True), parent)
        if key in self.cache: return self.cache[key]
        raw, text, mapping = self.sources[name]
        prefix = "parent_source_" if parent else "source_"
        if prefix + "start" in metadata:
            a, b = metadata[prefix + "start"], metadata[prefix + "end"]
            valid = 0 <= a <= b <= len(raw) and raw[a:b] == value
            if metadata.get("source_sha256") and metadata["source_sha256"] != hashlib.sha256(raw.encode()).hexdigest():
                valid = False
            result = {"spans": [(a, b)] if valid else [], "status": "explicit_offsets" if valid else "invalid_offsets"}
        else:
            needle = normalized(value)[0]
            matches = occurrences(text, needle)
            synthetic = False
            if len(matches) != 1 and title and value.startswith(title + "\n"):
                needle = normalized(value[len(title) + 1:])[0]
                matches = occurrences(text, needle)
                synthetic = True
            if len(matches) != 1:
                candidates = []
                for section, (a, b) in self.sections[name]:
                    if section.get("title", "") != title or section.get("provenance", []) != entry.get("provenance", []):
                        continue
                    candidates += [x for x in matches if a <= x[0] and x[1] <= b]
                matches = sorted(set(candidates))
            if len(matches) == 1:
                a, b = matches[0]
                spans = [(mapping[a], source_end(raw, mapping[b - 1]))]
                if synthetic:
                    preceding = [h for h in self.headings[name] if h[1] <= spans[0][0]]
                    if preceding and preceding[-1][2] == canonical(title):
                        spans.append(preceding[-1][:2])
                result = {"spans": spans, "status": "verified_body_and_heading" if synthetic else "unique_source_match"}
            else:
                result = {"spans": [], "status": "ambiguous" if matches else "unaligned", "matches": len(matches)}
        result["document"] = name
        self.cache[key] = result
        return result

    def score(self, case, entries):
        required = case.metadata["evidence_ids"]
        aligned = [self.align(e) for e in entries]
        hits, details, pending = {}, {}, []
        for aid in required:
            rule = self.rules["anchors"][aid]
            raw, text, mapping = self.sources[rule["document"]]
            spans = [s for e in aligned if e["document"] == rule["document"] for s in e["spans"]]
            reqs = []
            for req in rule["requirements"]:
                a, b = req["normalized_start"], req["normalized_end"]
                ok = all(c.isspace() or any(x <= mapping[i] < y for x, y in spans)
                         for i, c in enumerate(text[a:b], a))
                reqs.append({"name": req["name"], "hit": ok,
                             "source_start": req["source_start"], "source_end": req["source_end"]})
            hits[aid] = all(r["hit"] for r in reqs)
            details[aid] = reqs
            ambiguous = [e for e in aligned if e["document"] == rule["document"] and e["status"] in {"ambiguous", "unaligned", "invalid_offsets"}]
            if ambiguous and not hits[aid]: pending.append(aid)
        return {"version": VERSION, "selected_hits": hits,
                "selected_anchor_recall": sum(hits.values()) / len(required),
                "complete_selected_anchors": all(hits.values()), "requirements": details,
                "pending_anchors": pending, "source_alignment": aligned}
