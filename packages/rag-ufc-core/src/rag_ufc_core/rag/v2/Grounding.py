"""Validated claim/requirement coverage and global answer policy."""

from .Models import ClaimVerification


def validate_entity_constraints(result, draft, contract, evidence, resolver):
    """Necessary evidence coverage for explicit surface-form constraints.

    Document aliases are source-backed catalog facts, never aliases invented by
    a claim. This is NOT a semantic entailment scorer: an exact entity alone
    still does not prove role, date, decision or completion.
    """
    from .Planning import normalized
    import re

    sources = {e.evidence_id: e for e in evidence}
    records = {r["document_id"]: r for r in resolver.records}

    def contains(text, entity):
        return bool(
            re.search(
                r"(?<!\w)" + re.escape(normalized(entity)) + r"(?!\w)", normalized(text)
            )
        )

    def present(entity, ids):
        for eid in ids:
            source = sources.get(eid)
            if source is None:
                continue
            catalog = records.get(source.document_id, {})
            if any(
                contains(text, entity)
                for text in [source.excerpt, source.document_name]
                + catalog.get("aliases", [])
            ):
                return True
        return False

    claims = {c.claim_id: c for c in draft.claims}
    for verdict in result.claims:
        claim = claims.get(verdict.claim_id)
        if claim and verdict.status == "SUPPORTED":
            missing = [
                entity
                for entity in contract.explicit_entities
                if contains(claim.text, entity)
                and not present(entity, claim.evidence_ids)
            ]
            if missing:
                verdict.status, verdict.reason = (
                    "UNSUPPORTED",
                    "Explicit entities absent from citations: " + ", ".join(missing),
                )
    requirements = {r.requirement_id: r.text for r in contract.requirements}
    for coverage in result.coverage:
        ids = {
            eid
            for cid in coverage.claim_ids
            if cid in claims
            for eid in claims[cid].evidence_ids
        }
        needed = [
            e
            for e in contract.explicit_entities
            if contains(requirements.get(coverage.requirement_id, ""), e)
        ]
        if coverage.covered and any(not present(e, ids) for e in needed):
            coverage.covered = False
            coverage.reason = "Explicit entity constraint lacks cited evidence"
    return result


def validate_support_quotes(result, draft, evidence):
    """A claimed explicit support must have a literal witness in EACH citation.

    Literal containment is necessary, not semantic entailment. Coverage and
    relation correctness remain independently evaluated; no gold is consulted.
    """
    from .Focus import _normalized_with_offsets

    sources = {e.evidence_id: e.excerpt for e in evidence}
    claims = {c.claim_id: c for c in draft.claims}
    for verdict in result.claims:
        if verdict.status != "SUPPORTED" or verdict.claim_id not in claims:
            continue
        claim = claims[verdict.claim_id]
        witnessed = set()
        for support in verdict.support_quotes:
            if (
                support.evidence_id not in claim.evidence_ids
                or support.evidence_id not in sources
            ):
                continue
            source, _ = _normalized_with_offsets(sources[support.evidence_id])
            quote, _ = _normalized_with_offsets(support.quote)
            if quote and quote in source:
                witnessed.add(support.evidence_id)
        if witnessed != set(claim.evidence_ids):
            verdict.status = "UNSUPPORTED"
            verdict.reason = "Missing/non-literal support witness for cited evidence"
    return result


def validate_verification(result, draft, contract, available_ids):
    claims = {c.claim_id: c for c in draft.claims}
    if len(claims) != len(draft.claims):
        raise ValueError("Duplicate claim IDs")
    verdicts = {v.claim_id: v for v in result.claims}
    for cid, claim in claims.items():
        if (
            cid not in verdicts
            or not claim.evidence_ids
            or not set(claim.evidence_ids) <= available_ids
        ):
            verdicts[cid] = ClaimVerification(
                claim_id=cid,
                status="UNSUPPORTED",
                reason="Missing/invalid citation or verdict",
            )
    result.claims = [verdicts[cid] for cid in claims]
    supported = {cid for cid in claims if verdicts[cid].status == "SUPPORTED"}
    requirements = {r.requirement_id for r in contract.requirements}
    for conflict in result.conflicts:
        if not set(conflict.evidence_ids) <= available_ids or not set(
            conflict.claim_ids
        ) <= set(claims):
            raise ValueError("Invalid conflict references")
        if not set(conflict.requirement_ids) <= requirements:
            raise ValueError("Invalid conflict requirements")
    seen = set()
    for coverage in result.coverage:
        if (
            coverage.requirement_id not in requirements
            or coverage.requirement_id in seen
        ):
            raise ValueError("Invalid/duplicate coverage requirement")
        seen.add(coverage.requirement_id)
        if not set(coverage.claim_ids) <= set(claims):
            raise ValueError("Invalid coverage claim references")
        coverage.covered = (
            coverage.covered
            and bool(coverage.claim_ids)
            and set(coverage.claim_ids) <= supported
        )
        if not all(
            coverage.requirement_id in c.requirement_ids
            for c in (claims[i] for i in coverage.claim_ids)
        ):
            coverage.covered = False
    conflicts = {
        rid
        for c in result.conflicts
        for rid in (c.requirement_ids or list(requirements))
    }
    for c in result.coverage:
        if c.requirement_id in conflicts:
            c.covered = False
    covered = {c.requirement_id for c in result.coverage if c.covered}
    result.central_question_supported = (
        bool(requirements) and covered == requirements and not result.conflicts
    )
    return result


def useful_claims(draft, verification):
    supported = {v.claim_id for v in verification.claims if v.status == "SUPPORTED"}
    relevant = {
        cid
        for coverage in verification.coverage
        if coverage.covered
        for cid in coverage.claim_ids
    }
    return [c for c in draft.claims if c.claim_id in supported & relevant]


def answer_status(contract, verification, claims):
    if not claims:
        return "abstained", [r.text for r in contract.requirements]
    covered = {c.requirement_id for c in verification.coverage if c.covered}
    missing = [r.text for r in contract.requirements if r.requirement_id not in covered]
    return (
        "answered" if not missing and not verification.conflicts else "partial"
    ), missing
