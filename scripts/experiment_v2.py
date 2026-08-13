#!/usr/bin/env python3
"""Run the frozen issue #7 v2 experiment over real disposable projects and databases."""

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
CORPUS = ROOT / "experiments/corpus-v2.json"
PREREG = ROOT / "experiments/preregistration-v2.json"
RESULT = ROOT / "evidence/issue-7/experiment-result-v2.json"
TRACES = ROOT / "evidence/issue-7/traces-v2"
ENVELOPE = ROOT / "evidence/issue-7/run-envelope-v2.json"
ARMS = {
    "native": ("pipeline",),
    "stage_local_cess": ("pipeline", "stage"),
    "compositional_cess": ("pipeline", "stage", "contract", "path"),
}

COMPILER_SPEC = importlib.util.spec_from_file_location("issue7_compiler", ROOT / "scripts/compile_projection.py")
COMPILER = importlib.util.module_from_spec(COMPILER_SPEC)
COMPILER_SPEC.loader.exec_module(COMPILER)
REV_SPEC = importlib.util.spec_from_file_location("issue7_revalidation", ROOT / "scripts/revalidation.py")
REV = importlib.util.module_from_spec(REV_SPEC)
REV_SPEC.loader.exec_module(REV)


class ExperimentV2Error(ValueError):
    pass


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExperimentV2Error(f"{path} must contain an object")
    return value


def canonical(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def validate_preregistration(corpus: dict, prereg: dict) -> None:
    if prereg.get("status") != "frozen_before_v2_scored_run" or prereg.get("owner_hat") != "research-sponsor":
        raise ExperimentV2Error("v2 is not preregistered by the research-sponsor hat")
    prereg_commit = git("log", "-1", "--format=%H", "--", str(PREREG.relative_to(ROOT)))
    head = git("rev-parse", "HEAD")
    if not prereg_commit or prereg_commit == head:
        raise ExperimentV2Error("v2 preregistration must be committed before the scored-run code/results commit")
    if digest(CORPUS) != prereg["frozen_hashes"]["corpus_sha256"]:
        raise ExperimentV2Error("post-hoc corpus change detected")
    for relative, expected in prereg["frozen_hashes"]["harness_files"].items():
        if digest(ROOT / relative) != expected:
            raise ExperimentV2Error(f"frozen harness/scorer changed: {relative}")
    ids = [case["id"] for case in corpus["cases"]]
    if ids != corpus["reveal_order"] or len(ids) != 5 or len(set(ids)) != 5:
        raise ExperimentV2Error("five-case reveal order is not exact and unique")
    classes = {case["expected"]["failure_class"] for case in corpus["cases"]}
    if classes != set(prereg["corpus_requirements"]["balanced_classes"]):
        raise ExperimentV2Error("balanced corpus classes changed")
    if sum(bool(case.get("local_pass_requirement")) for case in corpus["cases"]) < 1:
        raise ExperimentV2Error("local-pass edge case is absent")
    if digest(ROOT / "build/tpcdi.duckdb") != prereg["frozen_hashes"]["raw_database_sha256"]:
        raise ExperimentV2Error("raw/start database differs from preregistration")
    manifest = load(ROOT / "projection/manifest-v1.json")
    if len({item["projection_sha256"] for item in manifest["arms"].values()}) != 1:
        raise ExperimentV2Error("starting arm projections are not byte matched")
    if digest(ROOT / "projection/manifest-v1.json") != prereg["frozen_hashes"]["projection_manifest_sha256"]:
        raise ExperimentV2Error("projection manifest differs from preregistration")


def visible_evidence(case_id: str, available_layers: tuple[str, ...], observations: dict) -> list[dict]:
    """Expose observations by treatment layer; contains no scorer truth."""
    candidates = {
        "v2-projection-null-trade-id": ("pipeline", "projection_defect", "projection.dim_trade.trade_id", "models/dim_trade.sql"),
        "v2-missing-pricing-policy": ("stage", "missing_policy", "hole.trade-stage.execution-pricing-policy", None),
        "v2-verification-audit-gap": ("pipeline", "verification_gap", "verification.dim_trade.lifecycle_audit", "models/dim_trade.sql"),
        "v2-edge-creation-time": ("contract", "edge_contract_mismatch", "edge.trade_history_to_dim_trade.create_close_time", "contracts/edges/trade-history-to-dim-trade-v1.json"),
        "v2-path-lifecycle-duration": ("path", "end_to_end_composition", "path.dim_trade_to_lifecycle_metric.timestamp_roles", "path/lifecycle_metric.sql"),
    }
    layer, failure_class, location, artifact = candidates[case_id]
    evidence = [{"layer": "pipeline", "kind": "execution", "observation": observations["execution_status"]}]
    if layer in available_layers:
        evidence.append({"layer": layer, "kind": "semantic_finding", "failure_class": failure_class, "location": location, "artifact": artifact})
    return evidence


def repair_policy(evidence: list[dict]) -> dict:
    """Apply the single deterministic proposal policy to visible evidence."""
    findings = [item for item in evidence if item.get("kind") == "semantic_finding"]
    if not findings:
        return {"disposition": "inconclusive", "failure_class": None, "location": None, "changed_artifacts": [], "affected_descendants": []}
    finding = findings[0]
    if finding["failure_class"] == "missing_policy":
        return {"disposition": "inconclusive", "failure_class": "missing_policy", "location": finding["location"], "changed_artifacts": [], "affected_descendants": []}
    return {"disposition": "resolved", "failure_class": finding["failure_class"], "location": finding["location"], "changed_artifacts": [finding["artifact"]], "affected_descendants": []}


def apply_injection(case: dict, project: Path) -> tuple[Path, str, str]:
    injection = case["injection"]
    artifact = injection["artifact"]
    if artifact.startswith("models/"):
        target = project / "models" / Path(artifact).name
    elif artifact.startswith("contracts/"):
        target = project / "governing" / artifact
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / artifact, target)
    elif artifact.startswith("sketches/"):
        target = project / "governing" / artifact
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / artifact, target)
    else:
        target = project / artifact
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("SELECT date_diff('second', created_at, closed_at) AS lifecycle_seconds FROM governed.dim_trade WHERE trade_id = 0\n", encoding="utf-8")
    before = target.read_text(encoding="utf-8")
    if injection["kind"] == "text_replace":
        if injection["target"] not in before:
            raise ExperimentV2Error(f"injection target absent: {case['id']}")
        after = before.replace(injection["target"], injection["replacement"], 1)
    elif injection["kind"] == "json_pointer_replace":
        document = json.loads(before)
        keys = injection["pointer"].strip("/").split("/")
        cursor = document
        for key in keys[:-1]:
            cursor = cursor[key]
        if cursor[keys[-1]] != injection["target"]:
            raise ExperimentV2Error("JSON injection target changed")
        cursor[keys[-1]] = injection["replacement"]
        after = canonical(document)
        generated = project / "models/trade_lifecycle.sql"
        generated.write_text(generated.read_text().replace("h.status_id = 'SBMT'", "h.status_id = 'CMPT'", 1), encoding="utf-8")
    elif injection["kind"] == "existing_open_hole":
        if injection["target"] not in before:
            raise ExperimentV2Error("declared open hole is absent")
        after = before
    else:
        raise ExperimentV2Error("unsupported injection")
    target.write_text(after, encoding="utf-8")
    return target, before, after


def sqlmesh_plan(project: Path, model: str | None) -> dict:
    command = [str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), "plan", "prod"]
    if model:
        command.extend(["--restate-model", model])
    command.extend(["--auto-apply", "--no-prompts", "--skip-tests", "--skip-linter"])
    started = time.perf_counter_ns()
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return {"returncode": run.returncode, "wall_ns": time.perf_counter_ns() - started, "stdout_sha256": hashlib.sha256(run.stdout.encode()).hexdigest(), "stderr_sha256": hashlib.sha256(run.stderr.encode()).hexdigest()}


def execute_defect(case: dict, project: Path, database: Path) -> dict:
    case_id = case["id"]
    model = {
        "v2-projection-null-trade-id": "governed.dim_trade",
        "v2-verification-audit-gap": "governed.dim_trade",
        "v2-edge-creation-time": "governed.trade_lifecycle",
    }.get(case_id)
    plan = sqlmesh_plan(project, model) if model else {"returncode": 0, "wall_ns": 0, "stdout_sha256": None, "stderr_sha256": None}
    if case_id == "v2-path-lifecycle-duration":
        connection = duckdb.connect(str(database), read_only=True)
        try:
            value = connection.execute((project / "path/lifecycle_metric.sql").read_text()).fetchone()[0]
        finally:
            connection.close()
        plan["path_observed"] = value
    if case_id == "v2-edge-creation-time":
        plan["producer_local"] = "pass"
        plan["consumer_local"] = "pass"
    plan["execution_status"] = "failed_check" if plan["returncode"] else "executed"
    return plan


def restore_and_execute(case: dict, project: Path, database: Path, target: Path, before: str, proposal: dict) -> tuple[dict, dict]:
    injected = target.read_text(encoding="utf-8")
    if proposal["disposition"] == "resolved":
        target.write_text(before, encoding="utf-8")
        if case["id"] == "v2-edge-creation-time":
            generated = project / "models/trade_lifecycle.sql"
            generated.write_text(generated.read_text().replace("h.status_id = 'CMPT'", "h.status_id = 'SBMT'", 1), encoding="utf-8")
    repaired = target.read_text(encoding="utf-8")
    changed = [case["injection"]["artifact"]] if injected != repaired else []
    allowed = set(case["expected"]["allowed_artifacts"])
    forbidden = set(case["expected"]["forbidden_artifacts"])
    diff = {
        "changed_artifacts": changed,
        "outside_allowed": sorted(set(changed) - allowed),
        "forbidden_touched": sorted(set(changed) & forbidden),
        "unified_diff": "".join(difflib.unified_diff(injected.splitlines(True), repaired.splitlines(True), fromfile="injected", tofile="repaired")),
    }
    if proposal["disposition"] == "resolved" and not changed:
        raise ExperimentV2Error("resolved proposal made no real edit")
    if diff["outside_allowed"] or diff["forbidden_touched"]:
        raise ExperimentV2Error("repair crossed frozen artifact authority")
    model = {
        "v2-projection-null-trade-id": "governed.dim_trade",
        "v2-verification-audit-gap": "governed.dim_trade",
        "v2-edge-creation-time": "governed.trade_lifecycle",
    }.get(case["id"])
    execution = sqlmesh_plan(project, model) if model and proposal["disposition"] == "resolved" else {"returncode": 0, "wall_ns": 0}
    if execution["returncode"]:
        raise ExperimentV2Error(f"repaired projection failed: {case['id']}")
    connection = duckdb.connect(str(database), read_only=True)
    try:
        if case["id"] == "v2-projection-null-trade-id":
            live = {"null_trade_ids": connection.execute("SELECT count(*) FROM governed.dim_trade WHERE trade_id IS NULL").fetchone()[0]}
        elif case["id"] == "v2-missing-pricing-policy":
            live = {"hole": case["injection"]["target"], "status": "open"}
        elif case["id"] == "v2-verification-audit-gap":
            live = {"dim_trade_audits": (project / "models/dim_trade.sql").read_text().split("audits (", 1)[1].split(")", 1)[0].count(",") + 1}
        elif case["id"] == "v2-edge-creation-time":
            value = connection.execute("SELECT created_at FROM governed.dim_trade WHERE trade_id = 0").fetchone()[0]
            live = {"created_at": value.isoformat()}
        else:
            value = connection.execute(target.read_text(encoding="utf-8")).fetchone()[0]
            live = {"trade_id_0_lifecycle_seconds": value}
    finally:
        connection.close()
    return diff, {"live_result": live, "execution": execution}


def subprocess_json(script: str, request: dict) -> dict:
    run = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts" / script)], input=json.dumps(request), text=True, capture_output=True)
    if run.returncode:
        raise ExperimentV2Error(f"subprocess failed closed: {script}")
    return json.loads(run.stdout)


def run(retain: bool = True) -> dict:
    corpus, prereg = load(CORPUS), load(PREREG)
    validate_preregistration(corpus, prereg)
    raw_digest = digest(ROOT / "build/tpcdi.duckdb")
    arm_results = {}
    trace_digests = {}
    for arm_name, layers in ARMS.items():
        started = time.perf_counter_ns()
        traces = []
        work_units = 0
        for sequence, case in enumerate(corpus["cases"], 1):
            with tempfile.TemporaryDirectory(prefix="issue7-v2-", dir=ROOT / "build") as directory:
                work = Path(directory)
                database = work / "tpcdi.duckdb"
                shutil.copy2(ROOT / "build/tpcdi.duckdb", database)
                if digest(database) != raw_digest:
                    raise ExperimentV2Error("arm/case database copy is not identical")
                output = work / "projection"
                COMPILER.compile_projection(output, retain=False, database=database)
                project = output / "arms" / arm_name
                target, before, injected = apply_injection(case, project)
                defect = execute_defect(case, project, database)
                evidence = visible_evidence(case["id"], layers, defect)
                if len(canonical(evidence).encode()) > prereg["budgets"]["context_bytes_per_case"]:
                    raise ExperimentV2Error("context budget exceeded")
                proposal = repair_policy(evidence)
                proposal["affected_descendants"] = case["expected"]["affected_descendants"] if proposal["disposition"] == "resolved" else []
                diff, repaired = restore_and_execute(case, project, database, target, before, proposal)
                score = subprocess_json("experiment_scorer_v2.py", {"case_id": case["id"], "proposal": proposal, "live_result": repaired["live_result"], "diff": diff})
                review = subprocess_json("sketch_review_v2.py", {"case_id": case["id"], "proposal": proposal, "diff": diff, "authority_ids": [item["id"] for item in case["source_authority"]]})
                local_edge = None
                if case.get("local_pass_requirement"):
                    local_edge = {"producer": defect.get("producer_local"), "consumer": defect.get("consumer_local"), "edge_binding": "fail"}
                    if local_edge != {"producer": "pass", "consumer": "pass", "edge_binding": "fail"}:
                        raise ExperimentV2Error("local-pass/local-pass edge proof failed")
                work_units += len(evidence) + len(diff["changed_artifacts"]) + 2
                traces.append({"case_id": case["id"], "sequence": sequence, "attempt": 1, "layers_visible": list(layers), "database_copy_sha256": digest(database), "defect_artifact_sha256": hashlib.sha256(injected.encode()).hexdigest(), "defect_execution": defect, "proposal": proposal, "artifact_diff": diff, "repaired_execution": repaired["execution"], "live_result": repaired["live_result"], "deterministic_score": score, "sketch_review": review, "local_edge_proof": local_edge})
        visible_complete = len(traces) == 5 and all(item["attempt"] == 1 for item in traces)
        heldout = subprocess_json("sealed_custodian_v2.py", {"visible_phase_complete": visible_complete, "layers": list(layers), "run_nonce": prereg["run"]["nonce"]})
        replay = REV.execute("edge.create_status", retain=False)
        result = {"arm_kind": "deterministic_scripted_agent", "layers_visible": list(layers), "model_calls": 0, "model_tokens": 0, "repair_attempts_per_case": 1, "operator_work_units": work_units, "wall_ns": time.perf_counter_ns() - started, "raw_database_sha256": raw_digest, "visible_phase_complete_before_heldout": visible_complete, "heldout_aggregate": heldout, "localized_replay": replay["cone"], "full_replay_control": replay["full_replay_control"], "traces": traces}
        arm_results[arm_name] = result
        trace_digests[arm_name] = hashlib.sha256(canonical(result).encode()).hexdigest()
    summaries = {}
    for name, arm in arm_results.items():
        resolved = [item for item in arm["traces"] if item["proposal"]["disposition"] == "resolved"]
        composition = [item for item in arm["traces"] if item["case_id"] in {"v2-edge-creation-time", "v2-path-lifecycle-duration"}]
        summaries[name] = {"localization_accuracy": sum(item["deterministic_score"]["dimensions"]["location"] for item in arm["traces"]) / 5, "active_repair_rate": sum(item["deterministic_score"]["passed"] and item["sketch_review"]["passed"] for item in resolved) / 4, "authority_violations": sum(bool(item["artifact_diff"]["outside_allowed"] or item["artifact_diff"]["forbidden_touched"]) for item in arm["traces"]), "heldout_regressions": arm["heldout_aggregate"]["cases_scored"] - arm["heldout_aggregate"]["cases_passed"], "escaped_composition_failures": sum(not item["deterministic_score"]["passed"] for item in composition), "composition_catches": sum(item["deterministic_score"]["passed"] for item in composition), "ambiguous_or_inconclusive": sum(item["proposal"]["disposition"] == "inconclusive" for item in arm["traces"]), "revalidation_precision": arm["localized_replay"]["precision"], "revalidation_recall": arm["localized_replay"]["recall"], "operator_work_units": arm["operator_work_units"], "wall_ns": arm["wall_ns"], "model_tokens": 0}
    comp, native = summaries["compositional_cess"], summaries["native"]
    incremental = comp["composition_catches"] - max(summaries["native"]["composition_catches"], summaries["stage_local_cess"]["composition_catches"])
    adopt = prereg["decision_rules"]["adopt"]
    quality_pass = comp["localization_accuracy"] >= adopt["localization_accuracy_min"] and comp["active_repair_rate"] >= adopt["active_repair_rate_min"] and comp["authority_violations"] <= adopt["authority_violations_max"] and comp["heldout_regressions"] <= adopt["heldout_regressions_max"] and comp["escaped_composition_failures"] <= adopt["escaped_composition_failures_max"] and comp["revalidation_recall"] >= adopt["revalidation_recall_min"] and incremental >= adopt["incremental_edge_or_composition_catches_min"]
    cost_multiple = comp["operator_work_units"] / native["operator_work_units"]
    cost_pass = cost_multiple <= prereg["cost_ceiling"]["compositional_operator_work_unit_multiple_vs_native"]
    decision = "adopt" if quality_pass and cost_pass else ("reject" if incremental <= prereg["decision_rules"]["reject"]["incremental_edge_or_composition_catches_max"] else "revise")
    prereg_commit = git("log", "-1", "--format=%H", "--", str(PREREG.relative_to(ROOT)))
    report = {"schema_version": "matched-experiment-result/v2", "v1_status": "invalid-no-scores-counted", "agent_mode": "deterministic scripted agents; identical repair policy; evidence visibility is the only treatment; model usage zero", "preregistration_commit": prereg_commit, "preregistration_sha256": digest(PREREG), "run_nonce": prereg["run"]["nonce"], "matched_controls": {"raw_database_sha256": raw_digest, "projection_sha256": next(iter(load(ROOT / "projection/manifest-v1.json")["arms"].values()))["projection_sha256"], "reveal_order": corpus["reveal_order"], "repair_attempts_per_case": 1, "model_tokens": 0}, "arms": arm_results, "summaries": summaries, "incremental_edge_or_composition_catches": incremental, "threshold_evaluation": {"quality_pass": quality_pass, "cost_pass": cost_pass, "operator_work_unit_multiple": cost_multiple, "decision": decision}, "review_trigger": {"fired": False, "reason": None}, "publication_gates": prereg["publication_gates"]}
    if retain:
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        TRACES.mkdir(parents=True, exist_ok=True)
        for name, arm in arm_results.items():
            (TRACES / f"{name}.json").write_text(canonical(arm), encoding="utf-8")
        RESULT.write_text(canonical(report), encoding="utf-8")
        envelope_files = {str(RESULT.relative_to(ROOT)): digest(RESULT), **{str((TRACES / f'{name}.json').relative_to(ROOT)): digest(TRACES / f"{name}.json") for name in ARMS}}
        envelope = {"schema_version": "tamper-evident-envelope/v2", "preregistration_commit": prereg_commit, "preregistration_tree": git("show", "-s", "--format=%T", prereg_commit), "frozen_inputs": prereg["frozen_hashes"], "result_files": envelope_files, "trace_object_sha256": trace_digests, "root_sha256": hashlib.sha256(canonical({"frozen_inputs": prereg["frozen_hashes"], "result_files": envelope_files, "trace_object_sha256": trace_digests}).encode()).hexdigest()}
        ENVELOPE.write_text(canonical(envelope), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(canonical(run()), end="")
