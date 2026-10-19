"""Bounded structural traversal for broad requests, independent of top-K."""

from .Models import (
    EvidenceUnit,
    RetrievalOccurrence,
    GlobalVerification,
    VerificationResult,
)


def global_verification(flow, draft, batch_verdicts, known_conflicts):
    """Global coverage/coherence over locally verified, literal witnesses.

    Full parents were checked in their individual batches. Do not concatenate
    every parent again into one over-window request, or upgrade a rejected
    local claim by borrowing another batch's evidence.
    """
    from .Grounding import validate_verification

    by_id = {v.claim_id: v for v in batch_verdicts}
    ids = {c.claim_id for c in draft.claims}
    proofs = []
    for claim in draft.claims:
        verdict = by_id.get(claim.claim_id)
        if verdict is None or verdict.status != "SUPPORTED":
            raise ValueError(
                "Global verification requires completed local support checks"
            )
        proofs.append(
            {
                "claim_id": claim.claim_id,
                "support_quotes": [q.model_dump() for q in verdict.support_quotes],
            }
        )
    payload = {
        **flow.contract_payload(),
        "claims": [c.model_dump() for c in draft.claims],
        "batch_support": proofs,
        "known_conflicts": [
            {**c.model_dump(), "claim_ids": [cid for cid in c.claim_ids if cid in ids]}
            for c in known_conflicts
        ],
        "batch_progress": flow.diagnostics.get("coverage", {}),
        "evidence": [
            {
                "evidence_id": e.evidence_id,
                "document_name": e.document_name,
                "document_id": e.document_id,
            }
            for e in flow.state.evidence
        ],
    }
    result = flow.team.run(
        "verification",
        "Os claims já passaram por verificação local com excertos completos e testemunhos literais validados por código. Avalie GLOBALMENTE cobertura de CADA requisito e incompatibilidades entre todos os claims/fontes. Não use OR dos lotes, não invente fatos. Coverage só é completa se os fatos substantivos pedidos estão respondidos; lote preparado não é lote concluído. Preserve conflitos conhecidos. Seja conciso.",
        payload,
        GlobalVerification,
    )
    conflicts = list(result.conflicts)
    for conflict in known_conflicts:
        # A rejected local claim can disappear from the draft, but the source
        # conflict remains relevant to its requirement.
        conflicts.append(
            conflict.model_copy(
                update={"claim_ids": [cid for cid in conflict.claim_ids if cid in ids]}
            )
        )
    verdict = VerificationResult(
        claims=[by_id[c.claim_id] for c in draft.claims],
        coverage=result.coverage,
        conflicts=conflicts,
    )
    verdict = validate_verification(
        verdict,
        draft,
        flow.state.question_contract,
        {e.evidence_id for e in flow.state.evidence},
    )
    flow.diagnostics["verification"].append(
        {"scope": "global_verified_batches", **verdict.model_dump()}
    )
    return verdict, payload


def evidence_batches(flow, scope):
    allowed = None if scope is None else set(scope)
    parents = {}
    for chunk in flow.retriever.chunks:
        if allowed is None or chunk.document_id in allowed:
            parents.setdefault(chunk.parent_id, []).append(chunk)
    existing = {item.parent_id: item for item in flow.state.found_evidence}
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
                evidence_id=f"E{len(flow.state.found_evidence) + 1}",
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
            flow.state.found_evidence.append(evidence)
            existing[parent_id] = evidence
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
        "prepared_parents": sum(len(batch) for batch in batches),
        "processed_parents": 0,
        "skipped_parent_ids": skipped,
        "complete": False,
        "prepared_batches": len(batches),
        "sent_batches": 0,
        "completed_batches": 0,
        "batches": len(batches),
    }
    flow.diagnostics["structural_enumeration"] = [
        item.chunk_id for group in parents.values() for item in group
    ]
    return batches
