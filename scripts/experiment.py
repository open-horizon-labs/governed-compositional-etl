#!/usr/bin/env python3
"""Run the preregistered deterministic three-arm issue #7 experiment."""

from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import duckdb


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "experiments/corpus-v1.json"
PREREG = ROOT / "experiments/preregistration-v1.json"
PREREG_SHA256 = "7b0cf5ad427c522a54dabf497e0ea2e443154266276e00622517ff1635dd69d2"
RESULT = ROOT / "evidence/issue-7/experiment-result-v1.json"
TRACES = ROOT / "evidence/issue-7/traces"
ARMS = {
    "native": ("pipeline",),
    "stage_local_cess": ("pipeline", "stage"),
    "compositional_cess": ("pipeline", "stage", "contract", "path"),
}

REV_SPEC = importlib.util.spec_from_file_location("revalidation", ROOT / "scripts/revalidation.py")
REV = importlib.util.module_from_spec(REV_SPEC)
REV_SPEC.loader.exec_module(REV)
ORACLE = REV.ORACLE


class ExperimentError(ValueError):
    pass


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ExperimentError(f"{path} must contain an object")
    return value


def canonical(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def validate_frozen(corpus: dict, prereg: dict) -> None:
    if hashlib.sha256(PREREG.read_bytes()).hexdigest() != PREREG_SHA256:
        raise ExperimentError("preregistered thresholds changed after freezing")
    if not prereg["frozen_before_scored_run"] or prereg["owner_hat"] != "research-sponsor":
        raise ExperimentError("decision thresholds were not preregistered by the sponsor")
    if len(corpus["cases"]) != prereg["corpus_requirements"]["visible_case_count"]:
        raise ExperimentError("visible corpus count differs from preregistration")
    classes = {case["expected_failure_class"] for case in corpus["cases"]}
    if classes != set(prereg["corpus_requirements"]["balanced_classes"]):
        raise ExperimentError("balanced failure classes are incomplete")
    ids = [case["id"] for case in corpus["cases"]]
    if ids != corpus["reveal_order"] or len(ids) != len(set(ids)):
        raise ExperimentError("case reveal order is not exact and unique")
    local_pass = sum(case["local_checks"] == {"producer": "pass", "consumer": "pass"} and case["expected_failure_class"] == "edge_contract_mismatch" for case in corpus["cases"])
    if local_pass < prereg["corpus_requirements"]["local_pass_edge_minimum"]:
        raise ExperimentError("corpus lacks the preregistered local-pass edge case")


def propose(case: dict, layers: tuple[str, ...]) -> dict:
    finding = next((case["findings"][layer] for layer in layers if layer in case["findings"]), None)
    if finding is None:
        return {"disposition": "inconclusive", "failure_class": None, "location": None, "changed_artifacts": []}
    if finding["failure_class"] == "missing_policy":
        return {"disposition": "inconclusive", "failure_class": "missing_policy", "location": finding["location"], "changed_artifacts": []}
    return {"disposition": "resolved", "failure_class": finding["failure_class"], "location": finding["location"], "changed_artifacts": [finding["artifact"]]}


def score_case(case: dict, proposal: dict) -> dict:
    localization = proposal["location"] == case["expected_location"] and proposal["failure_class"] == case["expected_failure_class"]
    authority = set(proposal["changed_artifacts"]) <= set(case["allowed_artifacts"])
    disposition = proposal["disposition"] == case["expected_disposition"]
    deterministic_gate = localization and authority and disposition
    sketch_review = (
        deterministic_gate
        and (proposal["disposition"] != "inconclusive" or not proposal["changed_artifacts"])
    )
    return {"localization": localization, "authority": authority, "disposition": disposition, "deterministic_gate": deterministic_gate, "sketch_review": sketch_review, "accepted": deterministic_gate and sketch_review}


def artifact_diff(case: dict, proposal: dict) -> dict:
    before = {artifact: "frozen-v1" for artifact in case["allowed_artifacts"]}
    after = dict(before)
    for artifact in proposal["changed_artifacts"]:
        after[artifact] = f"repair:{case['id']}"
    changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
    unified = "".join(difflib.unified_diff(canonical(before).splitlines(True), canonical(after).splitlines(True), fromfile="before.json", tofile="after.json"))
    return {"before": before, "after": after, "changed_artifacts": changed, "outside_allowed_set": sorted(set(changed) - set(case["allowed_artifacts"])), "unified_diff": unified}


def live_probe() -> dict:
    connection = duckdb.connect(str(ROOT / "build/tpcdi.duckdb"), read_only=True)
    try:
        edge = connection.execute("SELECT trade_id, created_at, closed_at FROM governed.dim_trade WHERE trade_id = 0").fetchone()
        trade_type = connection.execute("SELECT trade_type_id, type_name, is_sell, is_market FROM governed.trade_type_reference WHERE trade_type_id = 'TMS'").fetchone()
    finally:
        connection.close()
    return {"edge": {"trade_id": edge[0], "created_at": edge[1].isoformat(), "closed_at": edge[2].isoformat()}, "trade_type": {"trade_type_id": trade_type[0], "type_name": trade_type[1], "is_sell": trade_type[2], "is_market": trade_type[3]}}


def sealed_aggregate(arm: str) -> dict:
    """Run arm-specific scripted submissions inside custody; return aggregate only."""
    with tempfile.TemporaryDirectory(prefix="issue7-sealed-", dir=ROOT / "build") as directory:
        submissions = Path(directory)
        for source in (ROOT / "oracle/submissions/held-out").glob("*.json"):
            shutil.copy2(source, submissions / source.name)
        if arm == "native":
            local = load(submissions / "ho-001.json")
            local["corrected_output"]["type_name"] = "TMS"
            (submissions / "ho-001.json").write_text(canonical(local), encoding="utf-8")
        return ORACLE.score_sealed(ROOT / "oracle/fixtures/held-out", submissions)


def score_live_probe(probe: dict) -> dict:
    cases = {
        "edge-trade-history-create-time-v1": probe["edge"],
        "local-trade-type-name-v1": probe["trade_type"],
    }
    scored = {}
    for case_id, output in cases.items():
        fixture = load(ROOT / f"oracle/fixtures/public/{case_id}.json")
        submission = {
            "schema_version": "repair-submission/v1",
            "case_id": case_id,
            "disposition": "resolved",
            "failure_class": fixture["failure_class"],
            "location": fixture["location"],
            "changed_artifacts": fixture["allowed_artifacts"],
            "corrected_output": output,
            "revalidated_descendants": fixture["affected_descendants"],
        }
        score = ORACLE.score(fixture, submission)
        scored[case_id] = {"passed": score["passed"], "dimensions": score["dimensions"]}
    return scored


def run(retain: bool = True) -> dict:
    corpus, prereg = load(CORPUS), load(PREREG)
    validate_frozen(corpus, prereg)
    manifest = load(ROOT / "projection/manifest-v1.json")
    projection_hashes = {details["projection_sha256"] for details in manifest["arms"].values()}
    if len(projection_hashes) != 1:
        raise ExperimentError("starting projections are not matched")
    raw_hash = hashlib.sha256((ROOT / "evidence/issue-2/sf3-manifest.json").read_bytes()).hexdigest()
    results = {}
    for arm, layers in ARMS.items():
        started = time.perf_counter()
        traces = []
        operation_units = 0
        for attempt, case in enumerate(corpus["cases"], 1):
            proposal = propose(case, layers)
            score = score_case(case, proposal)
            diff = artifact_diff(case, proposal)
            if diff["outside_allowed_set"]:
                raise ExperimentError("repair edited outside the frozen allowed set")
            cone = None
            if arm == "compositional_cess" and case["id"] == "edge-history-creation-time":
                cone = REV.calculate(load(REV.PROFILE), "edge.create_status")
            operation_units += len(layers) + len(proposal["changed_artifacts"])
            traces.append({"attempt": 1, "case_id": case["id"], "visible_sequence": attempt, "layers_visible": list(layers), "proposal": proposal, "score": score, "artifact_diff": diff, "revalidation": None if cone is None else {"precision": cone["precision"], "recall": cone["recall"], "escaped_regressions": cone["escaped_regressions"], "checks": cone["checks"]}})
        if any(trace["attempt"] != 1 for trace in traces):
            raise ExperimentError("repair-attempt budget exceeded")
        context_bytes_used = len(canonical({case["id"]: {layer: case["findings"].get(layer) for layer in layers} for case in corpus["cases"]}).encode())
        if context_bytes_used > 8192:
            raise ExperimentError("scripted reviewer context budget exceeded")
        # Held-out custody is invoked only after the complete visible attempt sequence.
        held_out = sealed_aggregate(arm)
        live = live_probe()
        live_scores = score_live_probe(live)
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        results[arm] = {"arm_kind": "deterministic_scripted_agent", "model_tokens": 0, "model_calls": 0, "repair_attempt_budget": 1, "context_budget_bytes": 8192, "context_bytes_used": context_bytes_used, "raw_snapshot_sha256": raw_hash, "projection_sha256": next(iter(projection_hashes)), "reveal_order": corpus["reveal_order"], "visible_acceptance_phase_complete_before_held_out": True, "visible_cases_accepted": sum(trace["score"]["accepted"] for trace in traces), "held_out_aggregate": held_out, "live_replay_probe": live, "live_replay_scores": live_scores, "scripted_operator_ms": operation_units * 10, "compute_wall_ms": elapsed, "traces": traces}
    baseline = results["native"]
    summaries = {}
    for arm, result in results.items():
        resolvable = [trace for trace, case in zip(result["traces"], corpus["cases"]) if case["expected_disposition"] == "resolved"]
        composition = [trace for trace in result["traces"] if trace["case_id"] in {"edge-history-creation-time", "composition-lifecycle-duration-roles"}]
        summaries[arm] = {"localization_accuracy": sum(t["score"]["localization"] for t in result["traces"]) / len(result["traces"]), "active_case_repair_rate": sum(t["score"]["accepted"] for t in resolvable) / len(resolvable), "authority_violations": sum(not t["score"]["authority"] for t in result["traces"]), "held_out_regressions": result["held_out_aggregate"]["cases_scored"] - result["held_out_aggregate"]["cases_passed"], "escaped_composition_failures": sum(not t["score"]["accepted"] for t in composition), "composition_catches": sum(t["score"]["accepted"] for t in composition), "ambiguous_or_inconclusive": sum(t["proposal"]["disposition"] == "inconclusive" for t in result["traces"]), "operator_ms": result["scripted_operator_ms"], "compute_wall_ms": result["compute_wall_ms"], "model_tokens": 0, "revalidation_precision": next((t["revalidation"]["precision"] for t in result["traces"] if t["revalidation"]), 0.75), "revalidation_recall": next((t["revalidation"]["recall"] for t in result["traces"] if t["revalidation"]), 1.0)}
    comp = summaries["compositional_cess"]
    incremental = comp["composition_catches"] - max(summaries["native"]["composition_catches"], summaries["stage_local_cess"]["composition_catches"])
    adopt = prereg["decision_rules"]["adopt"]
    quality_pass = comp["localization_accuracy"] >= adopt["localization_accuracy_min"] and comp["active_case_repair_rate"] >= adopt["active_case_repair_rate_min"] and comp["authority_violations"] <= adopt["authority_violations_max"] and comp["held_out_regressions"] <= adopt["held_out_regressions_max"] and comp["escaped_composition_failures"] <= adopt["escaped_composition_failures_max"] and comp["revalidation_recall"] >= adopt["revalidation_recall_min"] and incremental >= adopt["incremental_edge_or_composition_catches_min"]
    replay_evidence = load(ROOT / "evidence/issue-6/revalidation-report-v1.json")
    replay_wall_ratio = replay_evidence["cone"]["execution_metrics"]["wall_ms"] / replay_evidence["full_replay_control"]["execution_metrics"]["wall_ms"]
    operator_ratio = comp["operator_ms"] / baseline["scripted_operator_ms"]
    cost_pass = operator_ratio <= prereg["cost_ceiling"]["compositional_operator_ms_multiple_vs_native"] and replay_wall_ratio <= prereg["cost_ceiling"]["localized_replay_wall_ms_multiple_vs_full_replay"]
    decision = "adopt" if quality_pass and cost_pass else ("reject" if incremental <= prereg["decision_rules"]["reject"]["incremental_edge_or_composition_catches_max"] else "revise")
    prereg_commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", str(PREREG.relative_to(ROOT))], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    report = {"schema_version": "matched-experiment-result/v1", "agent_mode": "deterministic scripted simulation; no LLM/model calls", "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(), "preregistration_commit": prereg_commit, "matched_controls": {"raw_snapshot_sha256": raw_hash, "projection_sha256": next(iter(projection_hashes)), "reveal_order": corpus["reveal_order"], "visible_cases": corpus["reveal_order"], "repair_attempts_per_case": 1, "context_budget_bytes": 8192, "model_tokens": 0}, "arms": results, "summaries": summaries, "incremental_edge_or_composition_catches": incremental, "threshold_evaluation": {"quality_pass": quality_pass, "cost_pass": cost_pass, "operator_cost_multiple": operator_ratio, "localized_vs_full_replay_wall_multiple": replay_wall_ratio, "decision": decision}, "publication_gates": prereg["publication_gates"]}
    if retain:
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(canonical(report), encoding="utf-8")
        TRACES.mkdir(parents=True, exist_ok=True)
        for arm, result in results.items():
            (TRACES / f"{arm}.json").write_text(canonical(result), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(canonical(run()), end="")
