#!/usr/bin/env python3
"""Arm-neutral v2 scorer. Reads frozen truth only after a proposal exists."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "experiments/corpus-v2.json"


def main() -> int:
    request = json.load(sys.stdin)
    if "arm" in request or set(request) != {"case_id", "proposal", "live_result", "diff"}:
        return 2
    corpus = json.loads(CORPUS.read_text())
    case = next(item for item in corpus["cases"] if item["id"] == request["case_id"])
    proposal = request["proposal"]
    changed = set(request["diff"]["changed_artifacts"])
    dimensions = {
        "class": proposal["failure_class"] == case["expected"]["failure_class"],
        "location": proposal["location"] == case["expected"]["location"],
        "disposition": proposal["disposition"] == case["expected"]["disposition"],
        "authority": changed <= set(case["expected"]["allowed_artifacts"]) and not changed & set(case["expected"]["forbidden_artifacts"]),
        "live_result": request["live_result"] == case["expected"]["live_result"],
        "affected_descendants": proposal["affected_descendants"] == case["expected"]["affected_descendants"],
        "real_diff": bool(changed) if case["expected"]["disposition"] == "resolved" else not changed,
    }
    print(json.dumps({"schema_version": "v2-score/v1", "dimensions": dimensions, "passed": all(dimensions.values())}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
