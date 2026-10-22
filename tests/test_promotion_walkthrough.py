"""Research → release → application, with synthetic metadata and no model calls.

This validates the mechanism (identities, approval gates, pins, divergence and index
compatibility reporting), not the scientific quality of any candidate.
"""
from copy import deepcopy
import json

import pytest

from benchmark.promotion import tool
from rag_ufc_core import EngineSettings, check_adoption, pipeline_identity, release_manifest
from rag_ufc_core.identity import core_source_fingerprint

DEPLOYMENT = {"llm": {"providers": {"spark": {"base_url": "https://llm.invalid/api"}}}}


@pytest.fixture
def research(tmp_path, monkeypatch):
    """A research checkout with one evaluated candidate and its evidence."""
    monkeypatch.setattr(tool, "PROJECT_ROOT", tmp_path)
    evidence = tmp_path / "docs/coverage_first_evaluation.md"
    evidence.parent.mkdir()
    evidence.write_text("Pipeline-scope evaluation of coverage-first ordering (synthetic).", encoding="utf-8")
    registry = {"schema": tool.REGISTRY_SCHEMA, "candidates": [{
        "id": "synthetic.coverage_first", "status": "candidate", "component": "evidence_selection",
        "validation_scope": "pipeline", "evidence": [tool.evidence_entry(evidence)], "released_in": None}]}
    path = tmp_path / "registry.json"
    tool.write_json(path, registry)
    monkeypatch.setattr(tool, "REGISTRY", path)
    # The configuration the candidate was evaluated with: baseline + one changed setting.
    document = tool.config_document()
    document["rag_v2"]["context_tokens"] = 5000
    return {"registry": path, "evidence": evidence, "document": document}


def approve(research):
    registry = tool.read_json(research["registry"])
    registry["candidates"][0].update(status="approved", released_in="1.0.0")
    tool.write_json(research["registry"], registry)


def build(research, status="approved"):
    return tool.build_manifest(
        version="1.0.0", kind="improvement", status=status, decision="synthetic walkthrough",
        evidence=[research["evidence"]], document=research["document"], approved_by="maintainer",
        approved_at="2026-10-21", evaluation_scope="pipeline", evaluation_statement="synthetic",
        candidates=["synthetic.coverage_first"])


def test_candidate_must_be_approved_before_it_can_be_released(research):
    with pytest.raises(ValueError, match="not approved"):
        build(research)
    approve(research)
    manifest = build(research)
    assert manifest["included_candidates"] == ["synthetic.coverage_first"]
    assert manifest["evaluation"]["evidence"][0]["sha256"] == tool.sha(research["evidence"])


def test_released_pipeline_is_exactly_the_evaluated_one_and_the_application_adopts_it(research):
    approve(research)
    manifest = build(research)
    evaluated = tool.config_identity(research["document"])
    assert manifest["pipeline"]["pipeline_config_hash"] == evaluated["pipeline_config_hash"]

    # The application builds its settings from the release, never from research files.
    app_settings = EngineSettings.from_release(DEPLOYMENT, manifest=manifest)
    identity = pipeline_identity(app_settings)
    pin = {"core_version": "1.0.0", "core_source_fingerprint": core_source_fingerprint()}
    assert check_adoption(identity, pin, manifest=manifest)["status"] == "approved_match"
    assert identity["pipeline_config"]["retrieval"]["context_tokens"] == 5000

    # An application still configured for the previous release is told exactly what differs.
    old = pipeline_identity(EngineSettings.from_release(DEPLOYMENT))
    report = check_adoption(old, pin, manifest=manifest)
    assert report["status"] == "divergent"
    assert [d["path"] for d in report["divergences"]] == ["pipeline_config.retrieval.context_tokens"]


def test_unapproved_status_stale_pin_and_index_change_are_detected(research):
    approve(research)
    candidate = build(research, status="candidate")
    identity = pipeline_identity(EngineSettings.from_release(DEPLOYMENT, manifest=candidate))
    assert check_adoption(identity, manifest=candidate)["status"] == "unapproved"

    released = build(research)
    stale_pin = {"core_version": "1.0.0", "core_source_fingerprint": "0" * 64}
    assert check_adoption(identity, stale_pin, manifest=released)["status"] == "pin_mismatch"

    new_representation = deepcopy(released)
    new_representation["index_compatibility"]["representation_id"] = "track_b_identity_representation_v2"
    report = check_adoption(identity, manifest=new_representation)
    assert report["status"] == "divergent"
    assert report["divergences"][0]["path"] == "index_format.representation_id"


def test_shipped_release_has_no_candidates_and_matches_the_research_config():
    manifest = release_manifest()
    assert manifest["included_candidates"] == []
    assert manifest["approval"]["status"] == "baseline_continuity"
    shipped = tool.config_identity(tool.config_document())
    # [llm]/[rag_v2] in config/config.toml describe the released pipeline. If this fails, the
    # research default diverged from the release: cut a release or restore the setting.
    assert shipped["pipeline_config_hash"] == manifest["pipeline"]["pipeline_config_hash"]
    # E04 and the other research candidates are not part of any release.
    registry = json.loads(tool.REGISTRY.read_text())
    assert all(c["status"] != "approved" or c.get("released_in") for c in registry["candidates"])
