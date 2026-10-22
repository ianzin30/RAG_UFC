"""Pipeline identity, release manifest and adoption checks."""
from copy import deepcopy

import pytest

import rag_ufc_core
from rag_ufc_core import EngineSettings, check_adoption, pipeline_identity, release_manifest
from rag_ufc_core.identity import canonical_hash, core_source_fingerprint
from rag_ufc_core.release import ReleaseError, validate_manifest


def test_release_manifest_describes_this_version_and_is_adoptable():
    manifest = release_manifest()
    assert manifest["core_version"] == rag_ufc_core.__version__
    assert manifest["approval"]["status"] in {"approved", "baseline_continuity"}
    assert manifest["included_candidates"] == []
    assert canonical_hash(manifest["pipeline"]["pipeline_config"]) == manifest["pipeline"]["pipeline_config_hash"]


def test_release_settings_reproduce_the_approved_pipeline_exactly(settings):
    identity = pipeline_identity(settings)
    assert identity["pipeline_config_hash"] == release_manifest()["pipeline"]["pipeline_config_hash"]
    assert check_adoption(identity)["status"] == "approved_match"


def test_identity_is_deterministic_and_ignores_deployment_details():
    first = EngineSettings.from_release({
        "llm": {"timeout_seconds": 30, "providers": {"spark": {"base_url": "https://a.invalid", "api_key_env": "A"}}},
        "retrieval": {"device": "cpu", "batch_size": 2, "embedding_ollama_base_url": "http://a.invalid"},
    })
    second = EngineSettings.from_release({
        "llm": {"timeout_seconds": 900, "providers": {"spark": {"base_url": "https://b.invalid", "api_key_env": "B"}}},
        "retrieval": {"device": "mps", "batch_size": 16, "embedding_ollama_base_url": "http://b.invalid"},
    })
    a, b = pipeline_identity(first), pipeline_identity(second)
    assert a["pipeline_signature"] == b["pipeline_signature"]
    serialized = repr(a)
    assert "a.invalid" not in serialized and "api_key_env" not in serialized


def test_deployment_settings_cannot_change_the_pipeline():
    with pytest.raises(ValueError, match="llm.temperature"):
        EngineSettings.from_release({"llm": {"temperature": 0.7}})
    with pytest.raises(ValueError, match="retrieval.rerank_k"):
        EngineSettings.from_release({"retrieval": {"rerank_k": 10}})
    with pytest.raises(ValueError, match="llm.providers.spark.options"):
        EngineSettings.from_release({"llm": {"providers": {"spark": {"options": {"seed": 1}}}}})


def test_explicit_overrides_are_reported_as_divergence():
    settings = EngineSettings.from_release(overrides={"retrieval": {"rerank_k": 30}, "llm": {"model": "other/model"}})
    report = check_adoption(pipeline_identity(settings))
    assert report["status"] == "divergent"
    assert {d["path"] for d in report["divergences"]} == {
        "pipeline_config.retrieval.rerank_k", "pipeline_config.llm.model"}


def test_unapproved_release_and_wrong_build_are_reported(settings):
    identity = pipeline_identity(settings)
    candidate = deepcopy(release_manifest())
    candidate["approval"]["status"] = "candidate"
    assert check_adoption(identity, manifest=candidate)["status"] == "unapproved"
    pin = {"core_version": rag_ufc_core.__version__, "core_source_fingerprint": "0" * 64}
    report = check_adoption(identity, pin)
    assert report["status"] == "pin_mismatch"
    assert check_adoption(identity, {"core_version": rag_ufc_core.__version__,
                                     "core_source_fingerprint": core_source_fingerprint()})["status"] == "approved_match"


def test_index_representation_mismatch_is_divergence(settings):
    identity = pipeline_identity(settings)
    identity["index_format"] = {**identity["index_format"], "representation_id": "track_b_identity_representation_v2"}
    report = check_adoption(identity)
    assert report["status"] == "divergent"
    assert report["divergences"][0]["path"] == "index_format.representation_id"


def test_manifest_validation_rejects_tampering():
    manifest = deepcopy(release_manifest())
    manifest["pipeline"]["pipeline_config"]["retrieval"]["search_k"] = 99
    with pytest.raises(ReleaseError, match="hash"):
        validate_manifest(manifest)
    manifest = deepcopy(release_manifest())
    manifest["approval"]["status"] = "looks-fine"
    with pytest.raises(ReleaseError, match="status"):
        validate_manifest(manifest)


def test_dependency_versions_differing_from_the_evaluated_environment_are_warnings(settings):
    identity = pipeline_identity(settings)
    assert set(release_manifest()["evaluated_environment"]) == set(identity["environment"])
    identity["environment"] = {**identity["environment"], "crewai": "9.9.9"}
    report = check_adoption(identity)
    assert report["status"] == "approved_match"
    assert {"package": "crewai", "evaluated": release_manifest()["evaluated_environment"]["crewai"],
            "installed": "9.9.9"} in report["environment_differences"]
