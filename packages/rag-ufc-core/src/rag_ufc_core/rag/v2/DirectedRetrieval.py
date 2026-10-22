"""Opt-in, source-bound directed queries and per-query context packing.

This module has no benchmark/dataset imports and is not enabled by the app.
Local reranker scores remain local; global scores use the original question.
"""

from dataclasses import asdict, dataclass, field as dataclass_field
import re

import numpy as np

from .Planning import DocumentResolver, dates_in, normalized


TEMPLATES = {
    "coordinator": "Quem é o coordenador na instituição?",
    "objective": "Qual é o objetivo principal e o escopo do projeto?",
    "chair": "Como a chefia é identificada na abertura da ata?",
    "modality": "Qual é a modalidade da reunião informada na abertura da ata?",
}
FIELD_PATTERNS = {
    "coordinator": r"\b(?:coordenador(?:a|es|as)?|coordena|coordenacao)\b",
    "objective": r"\b(?:objetivos?|objetos?|escopo)\b",
    "chair": r"\b(?:chefia|chefe|subchefe)\b",
    "modality": r"\bmodalidades?\b",
}


@dataclass
class DirectedSearch:
    query_id: str
    text: str
    document_ids: list[str] | None
    field: str = "original"
    origin: str = "user_question"
    source_proof: list[dict] = dataclass_field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class DirectedPlanner:
    def __init__(self, catalog, chunks):
        self.chunks = chunks
        self.resolver = DocumentResolver(catalog, chunks)
        self.by_document = {}
        for chunk in chunks:
            self.by_document.setdefault(chunk.document_id, []).append(chunk)
        self.records = {r["document_id"]: r for r in self.resolver.records}

    def compatible(self, document_id, requested_field):
        record = self.records[document_id]
        if requested_field in {"chair", "modality"}:
            return bool(record["meeting_dates"])
        pattern = (r"^coordenador(?:a)?(?:\s+(?:na|da|do|de)\s+(?:instituicao|projeto))?$"
                   if requested_field == "coordinator" else r"\b(?:objetivos?|objetos?|escopo)\b")
        return any(re.search(pattern, normalized(c.section_title))
                   for c in self.by_document[document_id])

    def reference(self, record, text):
        norm = normalized(text)
        hits = []
        for alias in record["aliases"]:
            match = re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", norm)
            if match:
                hits.append((match.start(), {"kind": "document_alias", "quote": alias,
                                            "document_id": record["document_id"]}))
        # Match each mention separately so sorting follows the user's order.
        date_pattern = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b|\b\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b"
        for match in re.finditer(date_pattern, norm):
            found = set(dates_in(match.group())) & set(record["meeting_dates"])
            if found:
                proof = next(p for p in record["date_provenance"] if found & set(p["dates"]))
                hits.append((match.start(), {"kind": "meeting_date", "mention": match.group(),
                                            "document_id": record["document_id"], **proof}))
        for match in re.finditer(r"\bata\s+(\d{2})[-/](\d{4})\b",norm):
            month,year=match.groups()
            if not re.search(month+r"[-_]"+year,record.get("document_name","")):
                continue
            proofs=[p for p in record["date_provenance"]
                    if any(d[3:5]==month and d[6:]==year for d in p["dates"])]
            if proofs:
                hits.append((match.start(),{"kind":"meeting_month","mention":match.group(),
                    "document_id":record["document_id"],**proofs[0]}))
        if not hits:
            return None
        return min(p for p, _ in hits), [proof for _, proof in hits]

    def plan(self, question, original_query, history, ranking, scope=None, max_searches=4):
        if not 1 <= max_searches <= 4:
            raise ValueError("max_searches must be between 1 and 4")
        searches = [DirectedSearch("Q0", original_query, scope)]
        issues = []
        if scope == [] or max_searches == 1:
            return searches, issues
        field_text = normalized(question)
        requested = sorted((match.start(), key) for key, pattern in FIELD_PATTERNS.items()
                           if (match := re.search(pattern, field_text)))
        if not requested:
            return searches, issues
        allowed = set(self.records) if scope is None else set(scope)
        resolved = self.resolver.resolve(question, history)
        reference_text = resolved["resolution_text"]
        explicit = []
        for doc_id in resolved["ids"]:
            if doc_id not in allowed:
                continue
            reference = self.reference(self.records[doc_id], reference_text)
            if reference:
                explicit.append((reference[0], doc_id, reference[1]))
        ambiguous = set()
        for _, doc_id, proofs in explicit:
            for proof in proofs:
                signature = (proof["kind"], proof.get("mention", proof.get("quote")))
                matches = [d for _, d, pp in explicit if any(
                    (p["kind"], p.get("mention", p.get("quote"))) == signature for p in pp)]
                if len(set(matches)) > 1:
                    ambiguous.update(matches)
        if ambiguous:
            issues.append({"reason": "ambiguous_reference", "document_ids": sorted(ambiguous)})
        # Source-bound explicit references precede discovery. Ties use stable IDs.
        documents = [(d, "explicit_reference", pp) for _, d, pp in sorted(explicit)
                     if d not in ambiguous]
        known = {d for d, _, _ in documents} | ambiguous
        for item in ranking:
            chunk = self.chunks[item["position"]]
            if chunk.document_id in allowed and chunk.document_id not in known:
                known.add(chunk.document_id)
                documents.append((chunk.document_id, "retrieved_document", [{
                    "kind": "retrieved_chunk", "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id, "query_id": "Q0"}]))
        seen = {(normalized(original_query), tuple(sorted(scope)) if scope is not None else None)}
        for doc_id, origin, proof in documents:
            for _, requested_field in requested:
                if not self.compatible(doc_id, requested_field):
                    continue
                text = TEMPLATES[requested_field]
                key = (normalized(text), (doc_id,))
                if key in seen:
                    continue
                seen.add(key)
                searches.append(DirectedSearch(f"Q{len(searches)}", text, [doc_id],
                                               requested_field, origin, proof))
                if len(searches) == max_searches:
                    return searches, issues
        return searches, issues


def merge_and_rerank(original_query, runs, chunks, reranker):
    """Union, retaining query provenance; scores never mix across queries."""
    combined = {}
    for search, ranking, _ in runs:
        for rank, item in enumerate(ranking, 1):
            entry = combined.setdefault(item["chunk_id"], {**item, "query_occurrences": []})
            entry["query_occurrences"].append({
                "query_id": search.query_id, "query": search.text, "scope": search.document_ids,
                "local_rank": rank, "local_reranker_score": item["reranker_score"],
                "dense_rank": item["dense_rank"], "sparse_rank": item["sparse_rank"],
                "rrf_score": item["rrf_score"],
            })
    candidates = list(combined.values())
    scores = ([item["reranker_score"] for item in candidates] if len(runs) == 1 else
              reranker.score(original_query, [chunks[item["position"]].text for item in candidates]))
    if len(scores) != len(candidates) or not np.isfinite(scores).all():
        raise ValueError("Invalid global reranker output")
    for item, score in zip(candidates, scores):
        item["reranker_score"] = float(score)
    return sorted(candidates, key=lambda item: (-item["reranker_score"], item["chunk_id"]))


def select_round_robin(flow, query_rankings):
    """Pack exact parents in local-rank order, alternating queries."""
    items = {item.parent_id: item for item in flow.state.found_evidence}
    queues = []
    for search, ranking, _ in query_rankings:
        parents, seen = [], set()
        for entry in ranking:
            parent_id = flow.retriever.chunks[entry["position"]].parent_id
            if parent_id not in seen:
                seen.add(parent_id)
                parents.append(parent_id)
        queues.append((search.query_id, iter(parents)))
    used, selected, decided, trace = 0, [], set(), []
    active = queues
    while active:
        remaining = []
        for query_id, queue in active:
            # A repeated parent doesn't consume the query's turn.
            parent_id = next((p for p in queue if p not in decided), None)
            if parent_id is None:
                continue
            remaining.append((query_id, queue))
            decided.add(parent_id)
            item = items[parent_id]
            cost = flow.tokens(item.context)
            accepted = used + cost <= flow.config.context_tokens
            if accepted:
                selected.append(item)
                used += cost
            trace.append({"query_id": query_id, "parent_id": parent_id,
                          "chunk_id": item.chunk_id, "evidence_id": item.evidence_id,
                          "tokens": cost, "reason": "selected" if accepted else "token_budget"})
        active = remaining
    flow.state.evidence = selected
    flow.diagnostics["context_selection"] = [t for t in trace if t["reason"] != "selected"]
    flow.diagnostics["packing_trace"] = trace
    flow.diagnostics["active_context"] = [{
        "hop_id": flow.state.current_hop, "evidence_ids": [e.evidence_id for e in selected],
        "embedding_tokens": used, "policy": "query_round_robin_v1"}]
    return selected
