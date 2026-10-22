"""python -m benchmark.promotion {identity,config-identity,lineage,manifest,record,check}"""

import argparse
import json
import sys

from benchmark.core.bootstrap import bootstrap_python_path

from . import tool


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m benchmark.promotion", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    identity = commands.add_parser("identity", help="pipeline identity of a config with the current core")
    identity.add_argument("--config", default=str(tool.PROJECT_ROOT / "config/config.toml"))
    identity.add_argument("--out")

    historical = commands.add_parser("config-identity", help="config-only identity, e.g. of a historical run")
    source = historical.add_mutually_exclusive_group(required=True)
    source.add_argument("--config")
    source.add_argument("--code-zip", help="a run's code.zip; reads its archived config/config.toml")
    historical.add_argument("--llm-section", default="llm",
                            help="'benchmark.llm' for benchmark runs, 'llm' for the application profile")
    historical.add_argument("--compare-release", action="store_true",
                            help="list differences with the pipeline approved in RELEASE.json")

    lineage = commands.add_parser("lineage", help="moved engine files and whether their bytes changed")
    lineage.add_argument("--base", required=True, help="last commit before the extraction")
    lineage.add_argument("--out")

    manifest = commands.add_parser("manifest", help="write the package RELEASE.json")
    manifest.add_argument("--version", required=True)
    manifest.add_argument("--kind", required=True, help="e.g. baseline_continuity, improvement, fix")
    manifest.add_argument("--status", required=True)
    manifest.add_argument("--decision", required=True)
    manifest.add_argument("--evidence", nargs="*", default=[])
    manifest.add_argument("--candidate", action="append", default=[], help="approved registry candidate shipped")
    manifest.add_argument("--evaluation-scope", required=True, choices=["none_new", "component", "pipeline", "application"])
    manifest.add_argument("--evaluation-statement", required=True)
    manifest.add_argument("--approved-by")
    manifest.add_argument("--approved-at")
    manifest.add_argument("--config", default=str(tool.PROJECT_ROOT / "config/config.toml"))

    record = commands.add_parser("record", help="write releases/rag-ufc-core/<version>.json after building")
    record.add_argument("--wheel", required=True)
    record.add_argument("--tag", required=True)

    commands.add_parser("check", help="registry, manifest, evidence and pipeline-boundary consistency")

    args = parser.parse_args(argv)
    bootstrap_python_path()

    if args.command == "identity":
        result = tool.current_identity(tool.config_document(args.config))
        if args.out:
            tool.write_json(args.out, result)
    elif args.command == "config-identity":
        document = tool.archived_config_document(args.code_zip) if args.code_zip else tool.config_document(args.config)
        result = tool.config_identity(document, args.llm_section)
        if args.compare_release:
            from rag_ufc_core.identity import diff
            from rag_ufc_core.release import release_manifest
            approved = release_manifest()["pipeline"]
            result = {"llm_section": args.llm_section, "pipeline_config_hash": result["pipeline_config_hash"],
                      "approved_pipeline_config_hash": approved["pipeline_config_hash"],
                      "differences": diff(approved["pipeline_config"], result["pipeline_config"], "pipeline_config")}
    elif args.command == "lineage":
        result = tool.source_lineage(args.base)
        if args.out:
            tool.write_json(args.out, {"base": args.base, "files": result})
    elif args.command == "manifest":
        result = tool.build_manifest(
            version=args.version, kind=args.kind, status=args.status, decision=args.decision,
            evidence=args.evidence, document=tool.config_document(args.config), approved_by=args.approved_by,
            approved_at=args.approved_at, evaluation_scope=args.evaluation_scope,
            evaluation_statement=args.evaluation_statement, candidates=args.candidate)
        tool.write_json(tool.MANIFEST, result)
    elif args.command == "record":
        result = tool.release_record(wheel=args.wheel, tag=args.tag)
        tool.write_json(tool.RELEASES / f"{result['core_version']}.json", result)
    else:
        problems = tool.check()
        print(json.dumps({"consistent": not problems, "problems": problems}, ensure_ascii=False, indent=2))
        return 1 if problems else 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
