"""Research-to-release promotion: candidate registry, release manifests, release records.

The registry (``registry.json``) says what each research strategy is, where it is
implemented, at which scope it was validated and what its promotion would require.
A core release's ``RELEASE.json`` can only cite evidence whose files still have the
recorded hashes, and only an explicit maintainer decision makes a release adoptable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tomllib
import zipfile

from benchmark.core.bootstrap import PROJECT_ROOT

PACKAGE = PROJECT_ROOT / "packages/rag-ufc-core"
SOURCE = PACKAGE / "src/rag_ufc_core"
MANIFEST = SOURCE / "RELEASE.json"
RELEASES = PROJECT_ROOT / "releases/rag-ufc-core"
REGISTRY = Path(__file__).with_name("registry.json")
REGISTRY_SCHEMA = "rag_ufc.research_candidates.v1"
CANDIDATE_STATUSES = {"baseline", "experimental", "candidate", "approved", "rejected", "superseded"}
SCOPES = {"component", "pipeline", "application"}


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, payload) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def config_document(path=PROJECT_ROOT / "config/config.toml") -> dict:
    """The TOML as written: no process overrides, so the result is reproducible."""
    with Path(path).open("rb") as stream:
        return tomllib.load(stream)


def archived_config_document(code_zip) -> dict:
    """``config/config.toml`` as archived in a historical run's ``code.zip``."""
    with zipfile.ZipFile(code_zip) as archive:
        return tomllib.loads(archive.read("config/config.toml").decode("utf-8"))


def select_llm_section(document, section="llm") -> dict:
    """Benchmarks call models through ``[benchmark.llm]``, applications through ``[llm]``;
    a run's identity must use the section it actually used."""
    llm = document
    for key in section.split("."):
        llm = llm[key]
    return {**document, "llm": llm}


def config_identity(document, llm_section="llm") -> dict:
    """Pipeline configuration identity only; valid for historical runs too, since it
    does not claim anything about the code that ran."""
    from rag_ufc_core.identity import canonical_hash, pipeline_config
    from rag_ufc_core.settings import EngineSettings

    config = pipeline_config(EngineSettings.from_document(select_llm_section(document, llm_section)))
    return {"llm_section": llm_section, "pipeline_config_hash": canonical_hash(config), "pipeline_config": config}


def current_identity(document) -> dict:
    from rag_ufc_core.identity import pipeline_identity
    from rag_ufc_core.settings import EngineSettings

    return pipeline_identity(EngineSettings.from_document(document))


def evidence_entry(path) -> dict:
    # Repository-relative without resolving symlinks: result folders may be linked in.
    path = Path(path) if Path(path).is_absolute() else PROJECT_ROOT / path
    return {"path": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha(path)}


def evidence_problems(entries) -> list[str]:
    problems = []
    for entry in entries:
        path = PROJECT_ROOT / entry["path"]
        if not path.exists():
            problems.append(f"missing evidence: {entry['path']}")
        elif sha(path) != entry["sha256"]:
            problems.append(f"evidence changed since it was cited: {entry['path']}")
    return problems


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True).stdout.strip()


# Moved files whose old path now holds a compatibility shim instead of a symlink.
MOVED_BEHIND_SHIMS = {
    "llm_client.py": "llm_client.py",
    "application/service/LocalUploads.py": "LocalUploads.py",
}


def source_lineage(base_ref: str) -> list[dict]:
    """For each engine file that moved into the package: old path, new path and whether
    its bytes are unchanged since ``base_ref`` (the last pre-extraction commit)."""
    moved = []
    for path in sorted(PROJECT_ROOT.joinpath("application").rglob("*.py")):
        if path.is_symlink() and path.resolve().is_relative_to(SOURCE):
            moved.append((path.relative_to(PROJECT_ROOT).as_posix(), path.resolve(), "symlink"))
    moved += [(legacy, SOURCE / target, "shim") for legacy, target in MOVED_BEHIND_SHIMS.items()]
    rows = []
    for legacy, target, old_path_now in moved:
        try:
            base = hashlib.sha256(subprocess.run(["git", "show", f"{base_ref}:{legacy}"], cwd=PROJECT_ROOT,
                                                 check=True, capture_output=True).stdout).hexdigest()
        except subprocess.CalledProcessError:
            base = None
        current = sha(target)
        rows.append({"legacy_path": legacy, "package_path": target.relative_to(PROJECT_ROOT).as_posix(),
                     "legacy_path_now": old_path_now, "base_sha256": base, "current_sha256": current,
                     "identical": base == current})
    return rows


def build_manifest(*, version, kind, status, decision, evidence, document, approved_by=None,
                   approved_at=None, evaluation_scope, evaluation_statement, candidates=()) -> dict:
    from rag_ufc_core.identity import PIPELINE_ID, REPRESENTATION_ID, chunker_id, runtime_environment
    from rag_ufc_core.release import KNOWN_STATUSES, MANIFEST_SCHEMA
    from rag_ufc_core.rag.v2.Cache import FORMAT_VERSION
    from rag_ufc_core.settings import EngineSettings

    if status not in KNOWN_STATUSES:
        raise ValueError(f"Unknown status {status}")
    if status == "approved" and not (approved_by and approved_at):
        raise ValueError("An approved release needs the approving maintainer and date")
    registry = read_json(REGISTRY)
    known = {c["id"]: c for c in registry["candidates"]}
    for candidate in candidates:
        if known.get(candidate, {}).get("status") != "approved":
            raise ValueError(f"Candidate {candidate} is not approved in the research registry")
    entries = [evidence_entry(path) for path in evidence]
    identity = config_identity(document)
    settings = EngineSettings.from_document(document)
    return {
        "schema": MANIFEST_SCHEMA,
        "core_version": version,
        "release_kind": kind,
        "approval": {"status": status, "decision": decision, "approved_by": approved_by, "approved_at": approved_at},
        "pipeline": {"pipeline_id": PIPELINE_ID, **identity},
        "index_compatibility": {"format_version": FORMAT_VERSION, "representation_id": REPRESENTATION_ID,
                                "chunker": chunker_id(settings.retrieval)},
        "included_candidates": list(candidates),
        # Dependency versions of the environment this release was built and validated in.
        "evaluated_environment": runtime_environment(),
        "evaluation": {"scope": evaluation_scope, "statement": evaluation_statement, "evidence": entries},
    }


def release_record(*, wheel, tag) -> dict:
    from rag_ufc_core import __version__
    from rag_ufc_core.identity import core_source_fingerprint
    from rag_ufc_core.release import release_manifest

    if git("status", "--porcelain", "--", str(PACKAGE), "pyproject.toml", "uv.lock"):
        raise ValueError("Commit the package and packaging files before recording a release")
    # The whole commit, not only the package's: git consumers resolve with this repository's
    # packaging configuration at that commit.
    commit = git("rev-parse", "HEAD")
    manifest = release_manifest()
    return {
        "schema": "rag_ufc_core.release_record.v1",
        "core_version": __version__,
        "git_tag": tag,
        "core_commit": commit,
        "core_source_fingerprint": core_source_fingerprint(),
        "release_manifest_sha256": sha(MANIFEST),
        "wheel": {"file": Path(wheel).name, "sha256": sha(wheel)},
        "install": (f"rag-ufc-core @ git+https://github.com/ianzin30/RAG_UFC.git@{commit}"
                    "#subdirectory=packages/rag-ufc-core"),
        "approval_status": manifest["approval"]["status"],
        "maintainer_signoff": None,
    }


def signoff(*, version, by, statement, at=None) -> dict:
    """Record the maintainer's decision on a release record, once.

    The maintainer signs what the record describes: the command refuses if the package
    in this checkout no longer matches the record (fingerprint or RELEASE.json), or if
    the release was already signed.
    """
    from datetime import date

    from rag_ufc_core.identity import core_source_fingerprint

    if not by.strip() or not statement.strip():
        raise ValueError("A sign-off needs the maintainer's name and a statement")
    path = RELEASES / f"{version}.json"
    record = read_json(path)
    if record.get("maintainer_signoff"):
        raise ValueError(f"Release {version} is already signed; records are append-only")
    if record["core_source_fingerprint"] != core_source_fingerprint() or record["release_manifest_sha256"] != sha(MANIFEST):
        raise ValueError("This checkout's package differs from the release record; check out the released commit")
    record["maintainer_signoff"] = {
        "by": by.strip(), "at": at or date.today().isoformat(), "statement": statement.strip(),
        "approval_status": record["approval_status"],
        "core_source_fingerprint": record["core_source_fingerprint"],
        "release_manifest_sha256": record["release_manifest_sha256"],
    }
    write_json(path, record)
    return record


def check() -> list[str]:
    """Consistency of registry, manifest and evidence. Empty list = consistent."""
    from rag_ufc_core.release import ReleaseError, release_manifest
    from rag_ufc_core.strategies import application_pipeline_modules, experimental_modules

    problems = []
    registry = read_json(REGISTRY)
    if registry.get("schema") != REGISTRY_SCHEMA:
        problems.append("unknown registry schema")
    ids = set()
    for candidate in registry.get("candidates", []):
        name = candidate.get("id")
        if name in ids:
            problems.append(f"duplicate candidate {name}")
        ids.add(name)
        if candidate.get("status") not in CANDIDATE_STATUSES:
            problems.append(f"{name}: unknown status {candidate.get('status')}")
        if candidate.get("validation_scope") not in SCOPES:
            problems.append(f"{name}: unknown validation scope")
        problems.extend(f"{name}: {p}" for p in evidence_problems(candidate.get("evidence", [])))
        # Result packages stay out of Git; verify them wherever they are present.
        present = [a for a in candidate.get("artifact_references", []) if (PROJECT_ROOT / a["path"]).exists()]
        problems.extend(f"{name}: {p}" for p in evidence_problems(present))
        if candidate.get("status") == "approved" and not candidate.get("released_in"):
            problems.append(f"{name}: approved candidates must name the core release that ships them")
    try:
        manifest = release_manifest()
    except (ReleaseError, OSError, ValueError) as exc:
        problems.append(f"release manifest: {exc}")
    else:
        problems.extend(f"release evidence: {p}" for p in evidence_problems(manifest["evaluation"]["evidence"]))
        for name in manifest.get("included_candidates", []):
            if name not in ids:
                problems.append(f"release includes unknown candidate {name}")
    for path in sorted(RELEASES.glob("*.json")):
        record = read_json(path)
        signed = record.get("maintainer_signoff") if record.get("schema") == "rag_ufc_core.release_record.v1" else None
        if signed and (signed.get("core_source_fingerprint") != record.get("core_source_fingerprint")
                       or signed.get("release_manifest_sha256") != record.get("release_manifest_sha256")):
            problems.append(f"{path.name}: sign-off does not match the release it is attached to")
    leaked = application_pipeline_modules() & experimental_modules()
    if leaked:
        problems.append(f"experimental modules reachable from the application pipeline: {sorted(leaked)}")
    return problems
