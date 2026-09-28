"""Bounded structural traversal for broad requests, independent of top-K."""

from .Models import EvidenceUnit, RetrievalOccurrence


def evidence_batches(flow, scope):
    allowed = None if scope is None else set(scope)
    parents = {}
    for chunk in flow.retriever.chunks:
        if allowed is None or chunk.document_id in allowed:
            parents.setdefault(chunk.parent_id, []).append(chunk)
    existing = {item.parent_id: item for item in flow.state.evidence}
    batch, size, batches = [], 0, []
    skipped = []
    for parent_id, children in parents.items():
        text = flow.parents[parent_id]
        cost = flow.tokens(text)
        if cost > flow.config.context_tokens:
            skipped.append(parent_id)
            continue
        if batch and size + cost > flow.config.context_tokens:
            batches.append(batch)
            batch, size = [], 0
        if len(batches) >= flow.config.max_map_batches:
            skipped.append(parent_id)
            continue
        evidence = existing.get(parent_id)
        if evidence is None:
            chunk = children[0]
            evidence = EvidenceUnit(
                **{**chunk.model_dump(), "text": text},
                evidence_id=f"E{len(flow.state.evidence) + 1}",
                excerpt=text,
                context=text,
                retrieved_chunk_ids=[item.chunk_id for item in children],
                occurrences=[
                    RetrievalOccurrence(
                        retrieval_query=flow.state.plan.resolved_question,
                        hop_id=flow.state.current_hop,
                    )
                ],
            )
            flow.state.evidence.append(evidence)
        else:
            evidence.retrieved_chunk_ids = list(
                dict.fromkeys(
                    evidence.retrieved_chunk_ids + [item.chunk_id for item in children]
                )
            )
        batch.append(evidence)
        size += cost
    if batch:
        batches.append(batch)
    flow.diagnostics["coverage"] = {
        "eligible_parents": len(parents),
        "processed_parents": sum(len(batch) for batch in batches),
        "skipped_parent_ids": skipped,
        "complete": not skipped,
        "batches": len(batches),
    }
    flow.diagnostics["structural_enumeration"] = [
        item.chunk_id for group in parents.values() for item in group
    ]
    return batches
