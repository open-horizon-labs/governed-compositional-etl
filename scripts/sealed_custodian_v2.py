#!/usr/bin/env python3
"""Sealed v2 custody subprocess: emits aggregate counts, never case answers."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "custody/issue7-v2/fixtures.json"


def main() -> int:
    request = json.load(sys.stdin)
    if set(request) != {"visible_phase_complete", "layers", "run_nonce"}:
        return 2
    if not request["visible_phase_complete"] or request["run_nonce"] != "issue7-v2-run-20260813-a":
        return 3
    private = json.loads(PRIVATE.read_text())
    passed = sum(case["layer"] in request["layers"] for case in private["cases"])
    result = {
        "schema_version": "sealed-v2-aggregate/v1",
        "cases_scored": len(private["cases"]),
        "cases_passed": passed,
        "passed": passed == len(private["cases"]),
        "commitment": request["run_nonce"],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
