#!/usr/bin/env python3
"""Independent rule review of proposal/diff against current Sketch and authority."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    request = json.load(sys.stdin)
    if set(request) != {"case_id", "proposal", "diff", "authority_ids"}:
        return 2
    sketch = (ROOT / "sketches/trade-dim-v1.md").read_text()
    proposal, diff = request["proposal"], request["diff"]
    reasons = []
    if diff["outside_allowed"] or diff["forbidden_touched"]:
        reasons.append("diff crosses frozen authority")
    if proposal["disposition"] == "inconclusive":
        passed = not diff["changed_artifacts"] and "explicit holes" in sketch.lower()
        if not passed:
            reasons.append("inconclusive policy hole was edited")
    else:
        passed = bool(diff["unified_diff"]) and bool(request["authority_ids"])
        if not passed:
            reasons.append("repair lacks real diff or named authority")
    print(json.dumps({"schema_version": "sketch-review-v2/v1", "passed": passed, "reasons": reasons, "review_basis_sha256": __import__("hashlib").sha256(sketch.encode()).hexdigest()}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
