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


def restates_or_adds(clause_texts: dict[str, str], element: dict) -> dict:
    """The question every L2 review asks first: does this element restate what its cited clauses already say, or does it
    decide something they do not? Cheap enough to ask of every changed element before a capable reviewer is spent."""
    state = {"cited_clauses": clause_texts, "element": {k: element.get(k) for k in ("id", "statement", "necessity", "derivation", "parallel_assumption", "review_trigger") if element.get(k) is not None}}
    try:
        from typesafe_sdk import Noul
        q = {"adds_a_decision": Noul(instructions="Does the element decide something the cited clauses do not state? Answer no when it only restates, narrows to, or makes checkable what the clauses already require. Answer yes when it settles a case the clauses leave open, picks among readings, or supplies a default.")}
    except ImportError:
        return {"verdict": "not-run"}
    result = _call("restates_or_adds", state, q)
    if result["verdict"] != "ran":
        return result
    p_add = result["answers"]["adds_a_decision"]["noul"]
    return {**result, "p_adds_a_decision": p_add, "confidence_band": _band(p_add), "flag": p_add >= 0.5 or _band(p_add) != "high"}


# Deliberately absent: a selector for "does this element decide the question an L1 hole reserves". It was built,
# calibrated and withdrawn. Jev scores 0.71 when the element SAYS the outcome for the case ("...so a market order first
# reported PNDG is true") and 0.15 when the element states only the rule that implies it, which is the form every real
# element takes. The question needs derivation, and Jev reads rather than derives. The chain already answers it exactly:
# a runnable counterexample carrying that case, run through the projection, reports what the compiled thing does. Ask
# the selector what a text says; ask the counterexample what the code does; ask a capable model what a rule implies.


def treats_a_settled_question_as_open(settled_question: str, field_name: str, field_text: str) -> dict:
    """Suggested by a capable reviewer that caught what the screen missed: when a business answers a question, one field
    of an element is updated to drop it and a sibling field is left still treating it as open. A diff-scoped screen cannot
    see a field that did not change, but it can read every field of a changed element against what was just settled.

    The settled question must be IN the state. Asked without it ("does this sibling still treat the retired condition as
    open") the selector scored 0.73 on the real case and 0.72 on a control; given the settled text it scores 0.76 and 0.42.
    """
    state = {"settled_question": settled_question, "field": {"name": field_name, "text": field_text}}
    try:
        from typesafe_sdk import Noul
        q = {"treats_as_open": Noul(instructions="The settled_question has been answered by the business and is no longer open. Does the text in field still treat that same question as a reason to reassess, revisit, or flag for review?")}
    except ImportError:
        return {"verdict": "not-run"}
    result = _call("treats_a_settled_question_as_open", state, q)
    if result["verdict"] != "ran":
        return result
    p_open = result["answers"]["treats_as_open"]["noul"]
    return {**result, "field": field_name, "p_treats_as_open": p_open, "confidence_band": _band(p_open), "flag": p_open >= 0.5}


def within_contract(contract_text: str, changed: list[str]) -> dict:
    """Did the Developer stay inside what the change contract enumerated? A cheap screen before a capable reviewer reads
    a diff that turns out to be in scope, and a cheap catch when it is not."""
    state = {"change_contract": contract_text, "elements_changed": changed}
    try:
        from typesafe_sdk import Noul
        q = {"outside_scope": Noul(instructions="Does elements_changed include anything the change_contract did not authorize? The contract enumerates what may change; anything else is outside scope.")}
    except ImportError:
        return {"verdict": "not-run"}
    result = _call("within_contract", state, q)
    if result["verdict"] != "ran":
        return result
    p_out = result["answers"]["outside_scope"]["noul"]
    return {**result, "p_outside_scope": p_out, "confidence_band": _band(p_out), "flag": p_out >= 0.5 or _band(p_out) != "high"}


def review_needed(summary: dict) -> dict:
    """Is a capable reviewer owed, or is this bookkeeping a coordinator records? The triage that decides where the
    expensive reader goes."""
    state = {"cycle": summary}
    try:
        from typesafe_sdk import Choice
        q = {"depth": Choice(instructions="How deeply must this change be read? bookkeeping: prose or reference edits a prior review already prescribed, deciding nothing new. scoped: a bounded change to named elements that a reviewer should judge against the clauses. deep: new or restated rules, anything touching an open question, or a change whose scope is unclear.",
                             criteria={"bookkeeping": None, "scoped": None, "deep": None})}
    except ImportError:
        return {"verdict": "not-run"}
    result = _call("review_needed", state, q)
    if result["verdict"] != "ran":
        return result
    ans = result["answers"]["depth"]
    return {**result, "depth": ans.get("choice"), "probabilities": ans.get("probabilities"), "confidence": ans.get("confidence")}


def anchor_is_shape_only(entry: dict) -> dict:
    """Anchors constrain shape and authorize no rule. An anchor that states a meaning licenses a Developer to derive
    policy from it, which is how a counterfactual round recovered a removed clause."""
    state = {"anchor_entry": entry}
    try:
        from typesafe_sdk import Noul
        q = {"states_policy": Noul(instructions="Does anchor_entry state a rule, meaning, or consequence the business must decide, rather than only the shape of the received records (which fields exist, which codes appear, how rows are ordered)?")}
    except ImportError:
        return {"verdict": "not-run"}
    result = _call("anchor_is_shape_only", state, q)
    if result["verdict"] != "ran":
        return result
    p_policy = result["answers"]["states_policy"]["noul"]
    return {**result, "p_states_policy": p_policy, "confidence_band": _band(p_policy), "flag": p_policy >= 0.5 or _band(p_policy) != "high"}


def _band(p: float) -> str:
    return "high" if abs(p - 0.5) >= 0.3 else ("low" if abs(p - 0.5) < 0.15 else "medium")


if __name__ == "__main__":
    print(json.dumps({"available": available()}))
