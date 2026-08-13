#!/usr/bin/env python3
"""Recompute and bind every issue #8 publication claim to retained evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "evidence/issue-8/bounded-decision-v1.json"
RESULT = ROOT / "evidence/issue-7/experiment-result-v2.4.json"
CORPUS = ROOT / "experiments/corpus-v2.json"
PREREG = ROOT / "experiments/preregistration-v2.2.json"
REPORT = ROOT / "docs/bounded-experiment-report.md"
VALID_PREREG_COMMIT = "e9aa5bb6e1dcaeb2d03af755a7073d2dbcbec608"
VALID_RESULT_COMMIT = "30109d75dc613a29682a37652c751ef474289608"
INVALID_V1_PREREG_COMMIT = "0e35102"
BEGIN = "<!-- BEGIN CANONICAL EVIDENCE -->\n```json\n"
END = "\n```\n<!-- END CANONICAL EVIDENCE -->"


class FinalReportError(ValueError):
    pass


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FinalReportError(f"{path} must contain an object")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def evidence_hash(value: dict) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def git_show_json(commit: str, path: str) -> tuple[dict, bytes]:
    run = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True)
    if run.returncode:
        raise FinalReportError(f"cannot read frozen git artifact: {commit}:{path}")
    return json.loads(run.stdout), run.stdout


def report_block(text: str) -> dict:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise FinalReportError("report must contain exactly one canonical evidence block")
    return json.loads(text.split(BEGIN, 1)[1].split(END, 1)[0])


def arm_metrics(result: dict, name: str) -> dict:
    arm, summary = result["arms"][name], result["summaries"][name]
    if arm["arm_kind"] != "deterministic_scripted_agent" or arm["model_calls"] != 0 or arm["model_tokens"] != 0:
        raise FinalReportError("operator/model availability declaration differs from harness")
    if any(key in arm for key in ("operator_seconds", "human_operator_seconds", "compute_cost", "compute_cost_usd")):
        raise FinalReportError("unexpected operator-time or compute-cost measurement requires a new report schema")
    return {
        "active_repair_rate": summary["active_repair_rate"],
        "authority_violations": summary["authority_violations"],
        "compute_cost_available": False,
        "compute_cost_unavailable_reason": "No monetary or normalized resource-cost measurement was collected; elapsed wall time is descriptive only.",
        "escaped_composition_failures": summary["escaped_composition_failures"],
        "heldout_regressions": summary["heldout_regressions"],
        "localization_accuracy": summary["localization_accuracy"],
        "model_calls": arm["model_calls"],
        "model_tokens": arm["model_tokens"],
        "operator_time_available": False,
        "operator_time_unavailable_reason": "The arm used a scripted zero-model harness and collected no human operator timing.",
        "operator_work_units": summary["operator_work_units"],
        "wall_elapsed_seconds_descriptive": arm["wall_ns"] / 1_000_000_000,
    }


def same_members_different_order(actual: list[str], expected: list[str]) -> tuple[bool, bool]:
    return set(actual) == set(expected) and len(actual) == len(expected), actual == expected


def derive_canonical(result: dict, corpus: dict, prereg: dict, fresh_manifest: dict) -> dict:
    if result["schema_version"] != "matched-experiment-result/v2.3":
        raise FinalReportError("valid v2.4 retained file's internal schema label changed")
    arms = {name: arm_metrics(result, name) for name in ("compositional_cess", "native", "stage_local_cess")}
    comp = result["arms"]["compositional_cess"]
    traces = {item["case_id"]: item for item in comp["traces"]}
    cases = {item["id"]: item for item in corpus["cases"]}
    edge = traces["v2-edge-creation-time"]
    path = traces["v2-path-lifecycle-duration"]
    verification = traces["v2-verification-audit-gap"]
    edge_members, edge_order = same_members_different_order(edge["proposal"]["affected_descendants"], cases["v2-edge-creation-time"]["expected"]["affected_descendants"])
    verification_members, verification_order = same_members_different_order(verification["proposal"]["affected_descendants"], cases["v2-verification-audit-gap"]["expected"]["affected_descendants"])
    if not edge_members or edge_order or edge["deterministic_score"]["dimensions"]["affected_descendants"] or edge["deterministic_score"]["passed"]:
        raise FinalReportError("edge scorer false-negative explanation is not derived from frozen evidence")
    if not verification_members or verification_order or verification["deterministic_score"]["dimensions"]["affected_descendants"] or verification["deterministic_score"]["passed"]:
        raise FinalReportError("verification-gap scorer false-negative explanation is not derived from frozen evidence")
    physical_edge = edge["defect_execution"]["observed_output"]["trade_id_0_created_at"] != edge["live_result"]["created_at"]
    physical_path = path["defect_execution"]["path_observed"] != path["live_result"]["trade_id_0_lifecycle_seconds"]
    if not physical_edge or not physical_path:
        raise FinalReportError("two physical composition repairs are not retained")
    valid_prereg, valid_bytes = git_show_json(VALID_PREREG_COMMIT, str(PREREG.relative_to(ROOT)))
    if valid_bytes != PREREG.read_bytes() or valid_prereg != prereg:
        raise FinalReportError("working preregistration differs from exact valid ancestor")
    invalid_v1, _ = git_show_json(INVALID_V1_PREREG_COMMIT, "experiments/preregistration-v1.json")
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", VALID_PREREG_COMMIT, VALID_RESULT_COMMIT], cwd=ROOT)
    if ancestry.returncode:
        raise FinalReportError("valid preregistration does not precede valid result")
    valid_quality = result["threshold_evaluation"]["quality_pass"]
    invalid_v1_would_adopt = valid_quality and result["threshold_evaluation"]["operator_work_unit_multiple"] <= invalid_v1["cost_ceiling"]["compositional_operator_ms_multiple_vs_native"]
    localized = comp["localized_replay"]
    localized_execution = localized["execution_metrics"]
    full = comp["full_replay_control"]
    full_execution = full["execution_metrics"]
    if any("projection_diff" in trace for arm in result["arms"].values() for trace in arm["traces"]):
        raise FinalReportError("generated projection diff is now retained; limitation is stale")
    issue4_test = "test_independent_local_checks_pass_while_edge_value_fails"
    if issue4_test not in (ROOT / "tests/test_contracts.py").read_text(encoding="utf-8"):
        raise FinalReportError("issue #4 executable local-pass basis is absent")
    excluded = fresh_manifest["excluded_context"]
    projection_hashes = {item["projection_sha256"] for item in fresh_manifest["arms"].values()}
    if len(projection_hashes) != 1:
        raise FinalReportError("fresh projection arms differ")
    return {
        "arms": arms,
        "chronology": {
            "invalid_v1_criteria": {
                "compositional_operator_pseudo_ms_multiple": invalid_v1["cost_ceiling"]["compositional_operator_ms_multiple_vs_native"],
                "governs_valid_run": False,
                "localized_replay_wall_multiple": invalid_v1["cost_ceiling"]["localized_replay_wall_ms_multiple_vs_full_replay"],
                "reason_invalid": "V1 fabricated milliseconds from deterministic work units and used a non-executing harness.",
                "would_change_valid_decision_to_adopt": invalid_v1_would_adopt,
            },
            "unit_change_before_valid_run": "After invalidating fabricated v1 milliseconds, the valid preregistration uses explicit deterministic work units and treats measured wall time as descriptive only.",
            "valid_preregistration_commit": VALID_PREREG_COMMIT,
            "valid_preregistration_path": str(PREREG.relative_to(ROOT)),
            "valid_preregistration_sha256": sha256_bytes(valid_bytes),
            "valid_result_commit": VALID_RESULT_COMMIT,
            "valid_thresholds_precede_result": True,
        },
        "decision": {
            "bounded_decision": result["threshold_evaluation"]["decision"],
            "cost_pass": result["threshold_evaluation"]["cost_pass"],
            "incremental_scored_composition_catches": result["incremental_edge_or_composition_catches"],
            "operator_work_unit_multiple_vs_native": result["threshold_evaluation"]["operator_work_unit_multiple"],
            "quality_pass": valid_quality,
            "valid_operator_work_unit_ceiling": prereg["cost_ceiling"]["compositional_operator_work_unit_multiple_vs_native"],
            "valid_wall_time_role": prereg["cost_ceiling"]["wall_time_role"],
        },
        "fresh_projection": {
            "ce_archive_used": False,
            "excluded_context": excluded,
            "manifest_sha256": sha256_bytes((ROOT / "projection/manifest-v1.json").read_bytes()),
            "passed": True,
            "projection_sha256": next(iter(projection_hashes)),
        },
        "limitations": {
            "corpus_private_case_count": prereg["heldout_custody"]["case_count"],
            "corpus_visible_case_count": len(corpus["cases"]),
            "custody_tests_layer_availability_only": "case[\"layer\"] in request[\"layers\"]" in (ROOT / "scripts/sealed_custodian_v2.py").read_text(encoding="utf-8"),
            "generated_projection_diff_retained": False,
            "invalid_scored_attempts_excluded": ["v1", "v2_attempt_a", "v2.1", "v2.3"],
            "issue4_executable_local_pass_test": issue4_test,
            "local_pass_contract_validator_rerun_inside_v2": False,
            "valid_file_internal_schema_label": result["schema_version"],
            "valid_run": "v2.4",
        },
        "physical_vs_scored": {
            "edge": {
                "affected_descendant_members_equal": edge_members,
                "affected_descendant_order_equal": edge_order,
                "after": edge["live_result"]["created_at"],
                "before": edge["defect_execution"]["observed_output"]["trade_id_0_created_at"],
                "physically_repaired": physical_edge,
                "scored_pass": edge["deterministic_score"]["passed"],
            },
            "path": {
                "after": path["live_result"]["trade_id_0_lifecycle_seconds"],
                "before": path["defect_execution"]["path_observed"],
                "physically_repaired": physical_path,
                "scored_pass": path["deterministic_score"]["passed"],
            },
            "physical_composition_repairs": sum((physical_edge, physical_path)),
            "scored_composition_catches": result["summaries"]["compositional_cess"]["composition_catches"],
            "scorer_false_negative_derived": edge_members and not edge_order and not edge["deterministic_score"]["passed"],
            "verification_gap": {
                "affected_descendant_members_equal": verification_members,
                "affected_descendant_order_equal": verification_order,
                "scored_pass": verification["deterministic_score"]["passed"],
            },
        },
        "publication_gates": result["publication_gates"],
        "revalidation": {
            "full": {
                "audit_count": full_execution["audit_count"],
                "check_count": full_execution["check_count"],
                "restaged_model_count": full_execution["restaged_model_count"],
                "restaged_rows": full_execution["restaged_rows"],
                "semantic_recall": full["recall"],
                "wall_elapsed_ms_descriptive": full_execution["wall_ms"],
            },
            "localized": {
                "audit_count": localized_execution["audit_count"],
                "check_count": localized_execution["check_count"],
                "restaged_model_count": localized_execution["restaged_model_count"],
                "restaged_rows": localized_execution["restaged_rows"],
                "reused_ancestor_count": localized_execution["reused_ancestor_count"],
                "semantic_precision": localized["precision"],
                "semantic_recall": localized["recall"],
                "wall_elapsed_ms_descriptive": localized_execution["wall_ms"],
            },
        },
        "thresholds": prereg["decision_rules"]["adopt"],
    }


def verify(decision: dict | None = None, report_text: str | None = None) -> dict:
    decision = load(DECISION) if decision is None else decision
    report_text = REPORT.read_text(encoding="utf-8") if report_text is None else report_text
    if set(decision) != {"canonical_evidence", "canonical_evidence_sha256", "report_sha256", "schema_version"} or decision["schema_version"] != "bounded-adoption-decision/v2":
        raise FinalReportError("machine decision shape/version is invalid")
    if sha256_bytes(report_text.encode()) != decision["report_sha256"]:
        raise FinalReportError("complete report hash differs from machine decision")
    block = report_block(report_text)
    if block != decision["canonical_evidence"] or evidence_hash(block) != decision["canonical_evidence_sha256"]:
        raise FinalReportError("report block differs from hash-bound machine evidence")
    result, corpus, prereg = load(RESULT), load(CORPUS), load(PREREG)
    envelope_spec = importlib.util.spec_from_file_location("verify_v2", ROOT / "scripts/verify_experiment_v2.py")
    envelope_module = importlib.util.module_from_spec(envelope_spec)
    envelope_spec.loader.exec_module(envelope_module)
    envelope_module.verify(load(envelope_module.ENVELOPE), result)
    compiler = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/compile_projection.py"), "fresh"], cwd=ROOT, text=True, capture_output=True)
    if compiler.returncode:
        raise FinalReportError(f"fresh projection failed: {compiler.stderr}")
    derived = derive_canonical(result, corpus, prereg, json.loads(compiler.stdout))
    if decision["canonical_evidence"] != derived:
        raise FinalReportError("published evidence differs from independently derived evidence")
    if derived["decision"]["bounded_decision"] != "revise":
        raise FinalReportError("bounded decision is not the frozen valid result")
    return {"schema_version": "final-report-verification/v2", "passed": True, "decision": "revise", "valid_experiment": "v2.4", "fresh_projection_passed": True}


def main() -> int:
    try:
        print(json.dumps(verify(), indent=2, sort_keys=True))
    except (FinalReportError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"final report verification error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
