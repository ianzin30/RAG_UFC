"""Deterministic transition policy, independent of generator wording."""


def next_action(reasoning, contract, hop, max_hops):
    action = reasoning.next_action
    # Legacy outputs normalize contradictions to continued discovery.
    if action is None:
        action = (
            "retrieve"
            if reasoning.requires_additional_retrieval
            else (
                "answer"
                if reasoning.sufficient
                else "abstain" if reasoning.unanswerable else "retrieve"
            )
        )
    if action == "clarify" and not contract.unresolved_reference:
        action = "retrieve"
    if (
        action == "revise_scope"
        and contract.mandatory_document_ids
        and contract.scope_is_exclusive
    ):
        action = "retrieve"
    if action == "abstain" and reasoning.requires_additional_retrieval:
        action = "retrieve"
    if action == "answer" and reasoning.requires_additional_retrieval:
        action = "retrieve"
    if action == "abstain" and not (
        reasoning.impossibility_evidence_ids and reasoning.impossibility_reason
    ):
        action = "retrieve"
    if action == "answer" and reasoning.missing_requirement_ids:
        action = "retrieve"
    if action in {"retrieve", "revise_scope"} and hop >= max_hops:
        return "abstain", "max_hops"
    return action, {
        "answer": "evidence_sufficient",
        "abstain": "unanswerable",
        "clarify": "unresolved_reference",
    }.get(action, "missing_evidence")
