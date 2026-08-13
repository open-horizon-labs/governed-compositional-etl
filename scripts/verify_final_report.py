#!/usr/bin/env python3
"""Recompute the issue #8 decision report from valid retained evidence."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "evidence/issue-8/bounded-decision-v1.json"
RESULT = ROOT / "evidence/issue-7/experiment-result-v2.4.json"
REPORT = ROOT / "docs/bounded-experiment-report.md"


class FinalReportError(ValueError):
    pass


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FinalReportError(f"{path} must contain an object")
    return value


def exact_arm(result: dict, name: str) -> dict:
    arm, summary = result["arms"][name], result["summaries"][name]
    value = {
        "active_repair_rate": summary["active_repair_rate"],
        "authority_violations": summary["authority_violations"],
        "escaped_composition_failures": summary["escaped_composition_failures"],
        "heldout_regressions": summary["heldout_regressions"],
        "localization_accuracy": summary["localization_accuracy"],
        "model_calls": arm["model_calls"],
        "model_tokens": arm["model_tokens"],
        "operator_work_units": summary["operator_work_units"],
        "wall_seconds_descriptive": arm["wall_ns"] / 1_000_000_000,
    }
    if name == "compositional_cess":
        localized = arm["localized_replay"]["execution_metrics"]
        full = arm["full_replay_control"]["execution_metrics"]
        value["localized_replay"] = {
            "audit_count": localized["audit_count"],
            "check_count": localized["check_count"],
            "restaged_model_count": localized["restaged_model_count"],
            "restaged_rows": localized["restaged_rows"],
            "reused_ancestor_count": localized["reused_ancestor_count"],
            "semantic_precision": arm["localized_replay"]["precision"],
            "semantic_recall": arm["localized_replay"]["recall"],
            "wall_ms_descriptive": localized["wall_ms"],
        }
        value["full_replay"] = {
            "audit_count": full["audit_count"],
            "check_count": full["check_count"],
            "restaged_model_count": full["restaged_model_count"],
            "restaged_rows": full["restaged_rows"],
            "semantic_recall": arm["full_replay_control"]["recall"],
            "wall_ms_descriptive": full["wall_ms"],
        }
    return value


def verify() -> dict:
    decision, result = load(DECISION), load(RESULT)
    if decision["valid_experiment"] != "v2.4" or result["schema_version"] != "matched-experiment-result/v2.3":
        raise FinalReportError("decision does not use the sole valid retained experiment")
    for name in ("native", "stage_local_cess", "compositional_cess"):
        if decision["arms"][name] != exact_arm(result, name):
            raise FinalReportError(f"reported arm metrics differ from valid traces: {name}")
    threshold = result["threshold_evaluation"]
    basis = decision["decision_basis"]
    expected_basis = {
        "cost_pass": threshold["cost_pass"],
        "incremental_scored_composition_catches": result["incremental_edge_or_composition_catches"],
        "operator_work_unit_multiple_vs_native": threshold["operator_work_unit_multiple"],
        "quality_pass": threshold["quality_pass"],
        "scorer_false_negative": basis["scorer_false_negative"],
    }
    if basis != expected_basis or threshold["decision"] != decision["bounded_decision"] or decision["bounded_decision"] != "revise":
        raise FinalReportError("bounded decision does not follow frozen threshold evaluation")
    for name, arm in result["arms"].items():
        for trace in arm["traces"]:
            changed = trace["artifact_diff"]["changed_artifacts"]
            if trace["proposal"]["disposition"] == "resolved":
                if not changed or not trace["artifact_diff"]["unified_diff"]:
                    raise FinalReportError(f"resolved proposal lacks an actual diff: {name}/{trace['case_id']}")
            elif changed:
                raise FinalReportError(f"inconclusive proposal edited an artifact: {name}/{trace['case_id']}")
            if trace["artifact_diff"]["outside_allowed"] or trace["artifact_diff"]["forbidden_touched"]:
                raise FinalReportError(f"repair crossed authority: {name}/{trace['case_id']}")
    comp = result["arms"]["compositional_cess"]
    edge = next(item for item in comp["traces"] if item["case_id"] == "v2-edge-creation-time")
    path = next(item for item in comp["traces"] if item["case_id"] == "v2-path-lifecycle-duration")
    if (edge["defect_execution"]["observed_output"]["trade_id_0_created_at"], edge["live_result"]["created_at"]) != ("2012-07-07T00:02:34", "2012-07-07T00:01:13"):
        raise FinalReportError("reported edge materialization is not retained")
    if (path["defect_execution"]["path_observed"], path["live_result"]["trade_id_0_lifecycle_seconds"]) != (0, 81):
        raise FinalReportError("reported path materialization is not retained")
    prereg = decision["preregistration"]
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", prereg["commit"], prereg["result_commit"]], cwd=ROOT)
    if ancestry.returncode or not prereg["thresholds_precede_valid_run"]:
        raise FinalReportError("preregistration does not precede the valid result")
    envelope_spec = importlib.util.spec_from_file_location("verify_v2", ROOT / "scripts/verify_experiment_v2.py")
    envelope_module = importlib.util.module_from_spec(envelope_spec)
    envelope_spec.loader.exec_module(envelope_module)
    envelope_module.verify(load(envelope_module.ENVELOPE), result)
    compiler = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/compile_projection.py"), "fresh"], cwd=ROOT, text=True, capture_output=True)
    if compiler.returncode:
        raise FinalReportError(f"fresh projection failed: {compiler.stderr}")
    manifest = json.loads(compiler.stdout)
    fresh = decision["fresh_projection"]
    if manifest["excluded_context"] != fresh["excluded_context"] or len({item["projection_sha256"] for item in manifest["arms"].values()}) != 1:
        raise FinalReportError("fresh projection did not preserve excluded context or arm equivalence")
    if next(iter(manifest["arms"].values()))["projection_sha256"] != fresh["projection_sha256"] or not fresh["passed"] or fresh["ce_archive_used"]:
        raise FinalReportError("fresh projection evidence differs from report")
    if hashlib.sha256((ROOT / "projection/manifest-v1.json").read_bytes()).hexdigest() != fresh["manifest_sha256"]:
        raise FinalReportError("reported retained projection manifest hash is stale")
    prose = REPORT.read_text(encoding="utf-8")
    required = ("**Revise.**", "not a compliant TPC-DI benchmark", "zero model calls", "v2.4 is never rescored", "human review")
    if any(fragment.lower() not in prose.lower() for fragment in required):
        raise FinalReportError("report omits a required decision/publication boundary")
    return {"schema_version": "final-report-verification/v1", "passed": True, "decision": "revise", "valid_experiment": "v2.4", "fresh_projection_passed": True}


def main() -> int:
    try:
        print(json.dumps(verify(), indent=2, sort_keys=True))
    except (FinalReportError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"final report verification error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
