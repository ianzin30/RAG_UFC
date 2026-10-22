"""Release manifest shipped with the package, and adoption checks for applications.

``RELEASE.json`` records what this core release was approved to run: the pipeline
configuration (by hash and value), the index format it reads, the approval
decision and the evidence behind it. It is written in the research repository by
``benchmark.promotion`` and never edited by applications.

``check_adoption`` compares an application's *effective* pipeline with that record
and with the application's own pin (core version and source fingerprint), so a
divergent configuration, an unapproved release or a different build is reported
instead of silently presented as the evaluated pipeline.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from .identity import diff

MANIFEST_SCHEMA = "rag_ufc_core.release.v1"
# Statuses an application may run. "baseline_continuity" means the release repackages
# the pipeline already in production without new behavior; it makes no new claim.
ADOPTABLE_STATUSES = {"approved", "baseline_continuity"}
KNOWN_STATUSES = ADOPTABLE_STATUSES | {"candidate", "experimental", "rejected", "superseded"}


class ReleaseError(ValueError):
    pass


@lru_cache(maxsize=1)
def release_manifest() -> dict:
    path = Path(__file__).with_name("RELEASE.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict) -> None:
    from . import __version__

    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ReleaseError("Unknown release manifest schema")
    if manifest.get("core_version") != __version__:
        raise ReleaseError("RELEASE.json describes another core version")
    status = (manifest.get("approval") or {}).get("status")
    if status not in KNOWN_STATUSES:
        raise ReleaseError(f"Unknown approval status: {status!r}")
    pipeline = manifest.get("pipeline") or {}
    from .identity import canonical_hash
    if canonical_hash(pipeline.get("pipeline_config")) != pipeline.get("pipeline_config_hash"):
        raise ReleaseError("Approved pipeline configuration does not match its hash")


def check_adoption(identity: dict, pin: dict | None = None, *, manifest: dict | None = None) -> dict:
    """Report whether ``identity`` (from ``pipeline_identity``) runs an approved pipeline.

    ``pin`` is the application's lock (``core_version``, ``core_source_fingerprint``,
    optionally ``pipeline_config_hash``). The result never raises for divergence: hosts
    decide whether to refuse to start. Status values:
    ``approved_match`` · ``divergent`` · ``unapproved`` · ``pin_mismatch``.
    """
    manifest = manifest or release_manifest()
    problems = []
    status = manifest["approval"]["status"]
    if status not in ADOPTABLE_STATUSES:
        problems.append({"kind": "approval", "detail": f"release status is {status}"})
    if pin:
        for key in ("core_version", "core_source_fingerprint"):
            if pin.get(key) and pin[key] != identity.get(key):
                problems.append({"kind": "pin", "detail": f"{key} differs from the application pin",
                                 "expected": pin[key], "actual": identity.get(key)})
    approved = manifest["pipeline"]
    divergences = []
    if identity.get("pipeline_id") != approved.get("pipeline_id"):
        divergences.append({"path": "pipeline_id", "expected": approved.get("pipeline_id"),
                            "actual": identity.get("pipeline_id"), "change": "different"})
    if identity.get("pipeline_config_hash") != approved["pipeline_config_hash"]:
        divergences.extend(diff(approved["pipeline_config"], identity.get("pipeline_config") or {}, "pipeline_config"))
    compatible = manifest.get("index_compatibility") or {}
    for key in ("format_version", "representation_id", "chunker"):
        if key in compatible and compatible[key] != (identity.get("index_format") or {}).get(key):
            divergences.append({"path": f"index_format.{key}", "expected": compatible[key],
                                "actual": (identity.get("index_format") or {}).get(key), "change": "different"})
    evaluated = manifest.get("evaluated_environment") or {}
    installed = identity.get("environment") or {}
    environment = [{"package": name, "evaluated": version, "installed": installed.get(name)}
                   for name, version in sorted(evaluated.items()) if installed.get(name) != version]
    if any(p["kind"] == "pin" for p in problems):
        verdict = "pin_mismatch"
    elif any(p["kind"] == "approval" for p in problems):
        verdict = "unapproved"
    elif divergences:
        verdict = "divergent"
    else:
        verdict = "approved_match"
    return {
        "status": verdict,
        "release": {"core_version": manifest["core_version"], "approval_status": status,
                    "release_kind": manifest.get("release_kind")},
        "problems": problems,
        "divergences": divergences,
        # Warnings only: dependency versions that differ from the evaluated environment.
        "environment_differences": environment,
    }
