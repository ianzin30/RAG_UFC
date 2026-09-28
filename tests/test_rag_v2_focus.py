from types import SimpleNamespace

from application.service.rag.v2.Focus import literal_span, resolve_focus_spans


def evidence(text):
    return SimpleNamespace(excerpt=text)


def selection(claim_id, evidence_id, quote):
    return SimpleNamespace(claim_id=claim_id, evidence_id=evidence_id, quote=quote)


def test_literal_span_allows_whitespace_but_not_paraphrase():
    text = "O Prof. Fernando\nTrinta é o novo Tutor do PET."
    assert literal_span(text, "Fernando Trinta é o novo Tutor") == (8, 38)
    assert literal_span(text, "Fernando Trinta assumiu o PET") is None


def test_focus_spans_deduplicate_and_merge_overlaps():
    text = "Fernando Trinta é o novo Tutor do PET e coordena atividades."
    spans = resolve_focus_spans(
        [
            selection("C1", "E1", "Fernando Trinta é o novo Tutor do PET"),
            selection("C2", "E1", "novo Tutor do PET"),
        ],
        {"E1": evidence(text)},
        ["C1", "C2"],
    )
    assert len(spans["E1"]) == 1
    assert spans["E1"][0]["claim_ids"] == ["C1", "C2"]
    assert spans["E1"][0]["quote"] == "Fernando Trinta é o novo Tutor do PET"


def test_focus_ignores_unknown_claim_evidence_and_missing_quote():
    spans = resolve_focus_spans(
        [
            selection("unknown", "E1", "Fernando"),
            selection("C1", "E2", "Fernando"),
            selection("C1", "E1", "Maria"),
        ],
        {"E1": evidence("Fernando Trinta")},
        ["C1"],
    )
    assert spans == {}
