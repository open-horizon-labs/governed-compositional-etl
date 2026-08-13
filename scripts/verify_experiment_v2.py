#!/usr/bin/env python3
"""Fail-closed verifier for the retained issue #7 v2 run envelope."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ENVELOPE = ROOT / "evidence/issue-7/run-envelope-v2.4.json"
RESULT = ROOT / "evidence/issue-7/experiment-result-v2.4.json"


class VerificationError(ValueError):
    pass


def canonical(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(envelope: dict, result: dict, root: Path = ROOT) -> None:
    expected_keys = {"schema_version", "preregistration_commit", "preregistration_tree", "frozen_inputs", "result_files", "trace_object_sha256", "root_sha256"}
    if set(envelope) != expected_keys or envelope["schema_version"] != "tamper-evident-envelope/v2":
        raise VerificationError("envelope shape/version is invalid")
    for relative, expected in envelope["frozen_inputs"]["harness_files"].items():
        if digest(root / relative) != expected:
            raise VerificationError(f"frozen harness tampered: {relative}")
    if digest(root / "experiments/corpus-v2.json") != envelope["frozen_inputs"]["corpus_sha256"]:
        raise VerificationError("corpus changed after preregistration")
    for relative, expected in envelope["result_files"].items():
        if digest(root / relative) != expected:
            raise VerificationError(f"retained result/trace tampered: {relative}")
    tree = subprocess.run(["git", "show", "-s", "--format=%T", envelope["preregistration_commit"]], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    if tree != envelope["preregistration_tree"]:
        raise VerificationError("preregistration tree does not match commit")
    for name, expected in envelope["trace_object_sha256"].items():
        trace = json.loads((root / f"evidence/issue-7/traces-v2.4/{name}.json").read_text())
        if hashlib.sha256(canonical(trace).encode()).hexdigest() != expected:
            raise VerificationError(f"trace object tampered: {name}")
        replay = trace["localized_replay"]
        if replay["recall"] != 1.0 or replay["escaped_regressions"] or not replay["execution"]["executed_models"]:
            raise VerificationError("fake or incomplete localized replay metrics")
        full = trace["full_replay_control"]
        if full["recall"] != 1.0 or len(full["execution"]["executed_models"]) != 6:
            raise VerificationError("fake or incomplete full replay control")
        if any(item["start_database_sha256"] != result["matched_controls"]["raw_database_sha256"] for item in trace["traces"]):
            raise VerificationError("arm did not start from identical database copies")
        if any(item["attempt"] != 1 or not item["live_result"] for item in trace["traces"]):
            raise VerificationError("attempt budget or live output evidence is invalid")
        edge = next(item for item in trace["traces"] if item["case_id"] == "v2-edge-creation-time")
        edge_changed = edge["defect_execution"]["observed_output"]["trade_id_0_created_at"] != edge["repaired_execution"]["observed_output"]["trade_id_0_created_at"]
        if edge_changed != (edge["proposal"]["disposition"] == "resolved"):
            raise VerificationError("edge materialization does not match resolved/inconclusive proposal")
        path = next(item for item in trace["traces"] if item["case_id"] == "v2-path-lifecycle-duration")
        path_changed = path["defect_execution"]["path_observed"] != path["live_result"]["trade_id_0_lifecycle_seconds"]
        if path_changed != (path["proposal"]["disposition"] == "resolved"):
            raise VerificationError("path materialization does not match resolved/inconclusive proposal")
    summary = {
        "frozen_inputs": envelope["frozen_inputs"],
        "result_files": envelope["result_files"],
        "trace_object_sha256": envelope["trace_object_sha256"],
    }
    if hashlib.sha256(canonical(summary).encode()).hexdigest() != envelope["root_sha256"]:
        raise VerificationError("envelope root digest is invalid")
    for name, arm in result["arms"].items():
        retained = json.loads((root / f"evidence/issue-7/traces-v2.4/{name}.json").read_text())
        if retained != arm:
            raise VerificationError("result embeds a trace different from retained evidence")


def main() -> int:
    try:
        verify(json.loads(ENVELOPE.read_text()), json.loads(RESULT.read_text()))
    except (OSError, json.JSONDecodeError, VerificationError, subprocess.CalledProcessError) as error:
        print(f"v2 verification error: {error}", file=sys.stderr)
        return 2
    print("issue #7 v2 envelope verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
