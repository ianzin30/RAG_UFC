import numpy as np
from application.service.rag.v2.Sources import displayed_sources, preserve_v2_fields
from application.service.rag.v2.Cache import fingerprint, load_bundle, save_bundle
from application.service.rag.v2.Models import Chunk


def test_empty_citations_never_fall_back_to_legacy_sources():
    payload = {
        "sources": [{"document_name": "legacy"}],
        "cited_sources": [],
        "trace_version": 2,
    }
    restored = preserve_v2_fields(payload, {"sources": payload["sources"]})
    assert displayed_sources(restored) == []
    assert displayed_sources({"sources": payload["sources"]}) == payload["sources"]


def test_bundle_roundtrip_and_invalidation(tmp_path):
    chunk = Chunk(
        chunk_id="a", document_id="d", document_name="D", parent_id="p", text="same"
    )
    path = tmp_path / "index.npz"
    save_bundle(path, [chunk], {"p": "same"}, [], [[1, 0]], [{"1": 0.5}])
    loaded = load_bundle(path)
    assert loaded[0] == [chunk]
    assert np.array_equal(loaded[3], [[1, 0]])
    assert fingerprint([], {"child": 256}) != fingerprint([], {"child": 384})
    path.write_bytes(b"broken")
    assert load_bundle(path) is None


def test_history_roundtrip_preserves_v2_evidence_and_empty_citations(monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(
        str(Path(__file__).resolve().parents[1] / "application")
    )
    from presentation.chat_sessions.Normalization import coerce_messages

    message = {
        "role": "assistant",
        "content": "Sem evidência",
        "trace_version": 2,
        "cited_sources": [],
        "sources": [{"document_name": "legacy", "excerpt": "unused"}],
        "evidence": [{"evidence_id": "E1", "chunk_id": "a"}],
        "claims": [],
    }
    normalized = coerce_messages([message])[0]
    assert normalized["evidence"] == message["evidence"]
    assert displayed_sources(normalized) == []


def test_history_roundtrip_preserves_source_focus(monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(
        str(Path(__file__).resolve().parents[1] / "application")
    )
    from presentation.chat_sessions.Normalization import coerce_messages

    source = {
        "evidence_id": "E1",
        "excerpt": "Fernando Trinta é Tutor do PET.",
        "focus_status": "focused",
        "focus_spans": [
            {"claim_ids": ["C1"], "quote": "Tutor do PET", "start": 18, "end": 30}
        ],
    }
    normalized = coerce_messages(
        [{"role": "assistant", "content": "ok", "trace_version": 2, "cited_sources": [source]}]
    )[0]
    assert normalized["cited_sources"][0]["focus_status"] == "focused"
    assert normalized["cited_sources"][0]["focus_spans"][0]["quote"] == "Tutor do PET"
