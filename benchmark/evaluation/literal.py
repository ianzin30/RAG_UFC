"""Frozen literal_v1 evaluator, shared without a generation runner."""
from pathlib import Path
import re

def canonical(text):
    return " ".join(re.sub(r"(?m)^#{1,6}\s+", "", text).split())


def anchor_coverage(case, trace, anchors, corpus):
    """Exact whitespace/heading-normalized containment; not semantic entailment."""
    expected = case.metadata.get("evidence_ids", [])
    if not expected:
        return {"applicable": False, "selected_anchor_recall": None,
                "complete_selected_anchors": None, "cited_anchor_recall": None}
    selected = trace.get("evidence", [])
    cited = trace.get("cited_sources", [])

    def matches(entries, anchor):
        document = anchor["document"]
        quote = canonical(anchor["quote"])
        texts = [canonical(str(entry.get("excerpt") or entry.get("text") or ""))
                 for entry in entries
                 if Path(str(entry.get("relative_path", ""))).name == document]
        if any(quote in text for text in texts):
            return True
        # A reference can bridge structural sections. Credit coverage only if
        # all non-space characters are covered by exact retrieved source spans.
        source = corpus[document]
        start = source.find(quote)
        if start < 0:
            return False
        covered = bytearray(len(quote))
        for text in texts:
            if not text:
                continue
            position = source.find(text)
            while position >= 0:
                left, right = max(start, position), min(start + len(quote), position + len(text))
                if right > left:
                    covered[left - start:right - start] = b"\x01" * (right - left)
                position = source.find(text, position + 1)
        return all(covered[i] or char.isspace() for i, char in enumerate(quote))

    selected_hits = {key: matches(selected, anchors[key]) for key in expected}
    cited_hits = {key: matches(cited, anchors[key]) for key in expected}
    return {
        "applicable": True,
        "definition": "strict_literal_anchor_coverage_not_semantic_support",
        "selected_anchor_recall": sum(selected_hits.values()) / len(expected),
        "complete_selected_anchors": all(selected_hits.values()),
        "cited_anchor_recall": sum(cited_hits.values()) / len(expected),
        "selected_hits": selected_hits, "cited_hits": cited_hits,
    }

