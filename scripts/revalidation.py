#!/usr/bin/env python3
"""Compute and execute bounded semantic revalidation cones for issue #6."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import duckdb


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "contracts/revalidation-profile-v1.json"
EVIDENCE = ROOT / "evidence/issue-6/revalidation-report-v1.json"
ORACLE_SPEC = importlib.util.spec_from_file_location("governed_oracle", ROOT / "scripts/oracle.py")
ORACLE = importlib.util.module_from_spec(ORACLE_SPEC)
ORACLE_SPEC.loader.exec_module(ORACLE)


class RevalidationError(ValueError):
    """The proposed cone is unsafe or inconsistent with frozen evidence."""


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise RevalidationError(f"{path} must contain an object")
    return value


def descendants(graph: dict[str, list[str]], sources: list[str]) -> set[str]:
    unknown = set(sources) - set(graph)
    if unknown:
        raise RevalidationError(f"unknown dependency source: {sorted(unknown)}")
    found: set[str] = set()
    pending = list(sources)
    while pending:
        node = pending.pop()
        for child in graph[node]:
            if child not in graph:
                raise RevalidationError(f"dependency target is undeclared: {child}")
            if child not in found and child not in sources:
                found.add(child)
                pending.append(child)
    return found


def validate_profile(profile: dict) -> None:
    required = {"schema_version", "active_case", "curated_regression_set", "changes", "semantic_dependencies", "semantic_public_nodes", "executable_dependencies", "frozen_descendant_oracle", "node_checks", "path_invariants"}
    if set(profile) != required or profile["schema_version"] != "revalidation-profile/v1":
        raise RevalidationError("revalidation profile shape/version is invalid")
    archive = load_json(ROOT / "counterexamples/archive/index-v1.json")
    regressions = load_json(ROOT / "regressions/curated-v1.json")
    if archive["accepted_counterexamples"]:
        raise RevalidationError("accepted CE archive changed without an explicit issue #6 profile decision")
    if [item["id"] for item in regressions["cases"]] != profile["curated_regression_set"]:
        raise RevalidationError("curated regression set differs from its separate retained artifact")
    manifest = load_json(ROOT / "projection/manifest-v1.json")
    sql_models = {f"governed.{Path(path).stem}" for path in manifest["files"] if path.startswith("models/")}
    if set(profile["executable_dependencies"]) != sql_models:
        raise RevalidationError("executable dependency graph does not exactly cover SQLMesh models")
    semantic_nodes = set(profile["semantic_dependencies"])
    executable_nodes = set(profile["executable_dependencies"])
    if semantic_nodes == executable_nodes:
        raise RevalidationError("semantic and executable dependencies were collapsed")
    for source, expected in profile["frozen_descendant_oracle"].items():
        fixture_id = profile["active_case"] if source.startswith("edge.trade_history") else profile["curated_regression_set"][0]
        fixture = load_json(ROOT / f"oracle/fixtures/public/{fixture_id}.json")
        if fixture["affected_descendants"] != expected:
            raise RevalidationError("profile differs from frozen exhaustive descendant oracle")
        observed = {
            profile["semantic_public_nodes"].get(node, node)
            for node in descendants(profile["semantic_dependencies"], [source])
        }
        if observed != set(expected):
            raise RevalidationError("semantic dependency graph differs from frozen exhaustive descendant oracle")


def calculate(profile: dict, change_id: str, proposed: set[str] | None = None) -> dict:
    validate_profile(profile)
    if change_id not in profile["changes"]:
        raise RevalidationError(f"unknown governed change: {change_id}")
    change = profile["changes"][change_id]
    internal_semantic = descendants(profile["semantic_dependencies"], [change["semantic_source"]])
    semantic = {profile["semantic_public_nodes"].get(node, node) for node in internal_semantic}
    executable = set(change["executable_sources"]) | descendants(profile["executable_dependencies"], change["executable_sources"])
    calculated = semantic if proposed is None else set(proposed)
    expected = set(profile["frozen_descendant_oracle"][change["semantic_source"]])
    escaped = expected - calculated
    unnecessary = calculated - expected
    if escaped:
        raise RevalidationError(f"known affected descendants escaped revalidation: {sorted(escaped)}")
    precision = len(expected & calculated) / len(calculated) if calculated else 0.0
    recall = len(expected & calculated) / len(expected) if expected else 1.0
    invariants = sorted(name for name, detail in profile["path_invariants"].items() if change["semantic_source"] in detail["sources"])
    nodes = calculated | executable
    uncovered = nodes - set(profile["node_checks"])
    if uncovered:
        raise RevalidationError(f"affected revalidation nodes lack checks: {sorted(uncovered)}")
    checks = {profile["active_case"], *profile["curated_regression_set"], *invariants, "sqlmesh.audits"}
    return {
        "change_id": change_id,
        "changed_pointer": change["pointer"],
        "semantic_descendants": sorted(calculated),
        "executable_revalidation": sorted(executable),
        "all_revalidation_nodes": sorted(nodes),
        "checks": sorted(checks),
        "node_count": len(nodes),
        "check_count": len(checks),
        "precision": precision,
        "recall": recall,
        "unnecessary_recomputation": sorted(unnecessary),
        "escaped_regressions": sorted(escaped),
    }


def run_checks(checks: list[str]) -> dict:
    started = time.perf_counter()
    results = {}
    for case_id in ("edge-trade-history-create-time-v1", "local-trade-type-name-v1"):
        if case_id in checks:
            fixture = load_json(ROOT / f"oracle/fixtures/public/{case_id}.json")
            submission = load_json(ROOT / f"oracle/submissions/examples/{case_id}.json")
            results[case_id] = ORACLE.score(fixture, submission)["passed"]
    connection = duckdb.connect(str(ROOT / "build/tpcdi.duckdb"), read_only=True)
    try:
        if "invariant.dim_trade_identity" in checks:
            results["invariant.dim_trade_identity"] = connection.execute("SELECT count(*) = count(DISTINCT trade_id) AND count(*) = 390978 FROM governed.dim_trade").fetchone()[0]
        if "invariant.lifecycle_duration" in checks:
            results["invariant.lifecycle_duration"] = connection.execute("SELECT count(*) = 0 FROM governed.dim_trade WHERE created_at IS NULL OR (closed_at IS NOT NULL AND closed_at < created_at)").fetchone()[0]
    finally:
        connection.close()
    if "sqlmesh.audits" in checks:
        audit = subprocess.run([str(ROOT / ".venv/bin/sqlmesh"), "-p", str(ROOT / "build/issue5-projection/arms/compositional_cess"), "audit"], cwd=ROOT, text=True, capture_output=True)
        results["sqlmesh.audits"] = audit.returncode == 0 and "0 audit errors" in audit.stdout
    if set(results) != set(checks) or not all(results.values()):
        raise RevalidationError(f"revalidation checks failed or were not executed: {results}")
    return {"elapsed_ms": round((time.perf_counter() - started) * 1000, 3), "results": results}


def execute(change_id: str, retain: bool = True) -> dict:
    profile = load_json(PROFILE)
    cone = calculate(profile, change_id)
    cone["execution"] = run_checks(cone["checks"])
    all_semantic = {profile["semantic_public_nodes"].get(node, node) for node in profile["semantic_dependencies"]} - {profile["changes"][change_id]["semantic_source"]}
    full_nodes = set(profile["semantic_dependencies"]) | set(profile["executable_dependencies"])
    full_checks = {profile["active_case"], *profile["curated_regression_set"], *profile["path_invariants"], "sqlmesh.audits"}
    full_execution = run_checks(sorted(full_checks))
    expected = set(profile["frozen_descendant_oracle"][profile["changes"][change_id]["semantic_source"]])
    report = {
        "schema_version": "revalidation-report/v1",
        "claim": "bounded historical Trade slice; correctness precedes cone size",
        "cone": cone,
        "full_replay_control": {
            "nodes": sorted(full_nodes),
            "node_count": len(full_nodes),
            "check_count": len(full_checks),
            "precision": len(expected) / len(all_semantic),
            "recall": 1.0,
            "unnecessary_recomputation": sorted(all_semantic - expected),
            "escaped_regressions": [],
            "execution": full_execution,
        },
        "separation": {
            "accepted_ce_archive": "counterexamples/archive/index-v1.json",
            "curated_regression_set": "regressions/curated-v1.json",
            "semantic_dependencies": "contracts/revalidation-profile-v1.json#/semantic_dependencies",
            "executable_dependencies": "contracts/revalidation-profile-v1.json#/executable_dependencies",
        },
    }
    if retain:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("change", choices=("edge.create_status", "edge.close_statuses", "stage.trade_type.rule"))
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args.change), indent=2, sort_keys=True))
    except (RevalidationError, OSError, json.JSONDecodeError) as error:
        print(f"revalidation error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
