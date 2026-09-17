#!/usr/bin/env python3
"""Jev (TypeSafe System One) as the chain's typed selector. Judge over code-built state; never a generator.

Decisions:
- invalidation: Noul "does this clause change alter the behavior this element must produce?"
- ce_level: Choice over {l1_gap, l2_gap, l3_defect}
- review_triage: Noul per clause "does the observed output follow this clause?"
Every call is logged to evidence/jev/calls.jsonl with request/response hashes, probabilities, confidence, tokens.
Without TYPESAFE_API_KEY the selector returns verdict not-run; callers must treat that conservatively.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evidence/jev/calls.jsonl"
HIGH, LOW = 0.8, 0.5


def _load_env() -> None:
    env = ROOT / ".env"
    if env.exists() and not os.environ.get("TYPESAFE_API_KEY"):
        for line in env.read_text().splitlines():
            if line.startswith("TYPESAFE_API_KEY=") and line.split("=", 1)[1].strip():
                os.environ["TYPESAFE_API_KEY"] = line.split("=", 1)[1].strip()


def available() -> bool:
    _load_env()
    try:
        import typesafe_sdk  # noqa: F401
    except ImportError:
        return False
    return bool(os.environ.get("TYPESAFE_API_KEY"))


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _call(purpose: str, state: dict, questions: dict) -> dict:
    if not available():
        return {"verdict": "not-run", "reason": "typesafe_sdk or TYPESAFE_API_KEY unavailable", "purpose": purpose}
    from typesafe_sdk import TypeSafeClient
    client = TypeSafeClient()
    started = time.perf_counter_ns()
    response = client.system_one(state, questions)
    elapsed = time.perf_counter_ns() - started
    raw = _to_builtins(response)
    entry = {"purpose": purpose, "model": raw.get("model"), "request_sha256": _sha({"state": state, "questions": {k: str(v) for k, v in questions.items()}}),
             "response_sha256": _sha(raw), "usage": raw.get("usage"), "answers": raw.get("answers"), "wall_ns": elapsed, "ts": time.time()}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return {"verdict": "ran", **entry}


def _to_builtins(response) -> dict:
    try:
        import msgspec
        return msgspec.to_builtins(response, builtin_types=(bytes,), str_keys=True)
    except Exception:  # pragma: no cover - fallback path
        answers = {}
        for name, a in response.answers.items():
            answers[name] = {k: getattr(a, k) for k in ("type", "noul", "choice", "score", "probabilities", "confidence", "legend") if hasattr(a, k)}
        usage = response.usage
        return {"model": response.model, "usage": {k: getattr(usage, k) for k in dir(usage) if k.endswith("tokens")}, "answers": answers}


def _gate(p: float) -> str:
    return "high" if p >= HIGH or p <= 1 - HIGH else ("low" if 1 - LOW < p < LOW or abs(p - 0.5) < (LOW - 0.5) else "medium")


def invalidation(clause_id: str, old_text: str, new_text: str, element: dict) -> dict:
    """Should a cached element be re-projected after this clause change? Hash change is the floor; this is the ceiling."""
    from_state = {"clause_id": clause_id, "clause_before": old_text, "clause_after": new_text,
                  "derived_element": {k: element.get(k) for k in ("id", "kind", "statement", "mutation_role", "history", "note") if element.get(k) is not None}}
    try:
        from typesafe_sdk import Noul
        q = {"behavior_changes": Noul(instructions="Does the change from clause_before to clause_after alter the behavior that derived_element must produce? Answer no for wording, typo, or clarification changes that leave the required behavior identical.")}
    except ImportError:
        return {"verdict": "not-run", "decision": "invalidate", "reason": "sdk unavailable"}
    result = _call("invalidation", from_state, q)
    if result["verdict"] != "ran":
        return {**result, "decision": "invalidate"}
    p = result["answers"]["behavior_changes"]["noul"]
    gate = "high" if abs(p - 0.5) >= 0.3 else ("low" if abs(p - 0.5) < 0.15 else "medium")
    decision = ("invalidate" if p >= 0.5 else "keep") if gate == "high" else "review"
    return {**result, "p_behavior_changes": p, "confidence_band": gate, "decision": decision}


def ce_level(clauses: dict[str, str], element: dict, observed: dict, corrected: dict) -> dict:
    state = {"l1_clauses": clauses, "l2_element": element, "observed_output": observed, "corrected_output": corrected}
    try:
        from typesafe_sdk import Choice
        q = {"level": Choice(instructions="At which level was the meaning lost? l1_gap: no clause states the rule needed for corrected_output. l2_gap: a clause states it but l2_element does not derive it. l3_defect: l2_element derives it and the projection failed to implement it.",
                             criteria={"l1_gap": None, "l2_gap": None, "l3_defect": None})}
    except ImportError:
        return {"verdict": "not-run"}
    result = _call("ce_level", state, q)
    if result["verdict"] != "ran":
        return result
    ans = result["answers"]["level"]
    return {**result, "level": ans.get("choice"), "probabilities": ans.get("probabilities"), "confidence": ans.get("confidence")}


def review_triage(clauses: dict[str, str], observed: dict) -> dict:
    state = {"observed_output": observed, "clauses": clauses}
    try:
        from typesafe_sdk import Noul
        q = {cid: Noul(instructions=f"Does observed_output follow clause {cid} (text under clauses.{cid})?") for cid in clauses}
    except ImportError:
        return {"verdict": "not-run"}
    result = _call("review_triage", state, q)
    if result["verdict"] != "ran":
        return result
    flags = {cid: result["answers"][cid]["noul"] for cid in clauses}
    return {**result, "follows": flags, "needs_review": sorted(c for c, p in flags.items() if p < HIGH)}


if __name__ == "__main__":
    print(json.dumps({"available": available()}))
