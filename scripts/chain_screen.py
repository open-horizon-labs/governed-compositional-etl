#!/usr/bin/env python3
"""The cheap reader. Jev screens a compiled cycle before a capable reviewer is spent on it.

Per changed element it asks whether the element restates what its clauses say or decides something they do not, and
notes mechanically when an element sits under a hole its own text never names. Per cycle it asks whether the diff stayed
inside the change contract and how deeply the change must be read.

It decides nothing, and it is calibrated rather than trusted (evidence/jev/calibration.json). Contract scope and review
depth separate cleanly and are reported as signals. Restatement ranks well and calibrates poorly (45 invariants that all
passed a capable review score 0.16 to 0.82, median 0.50), so it is reported as a ranking against that baseline, not a
verdict. A capable reviewer still reads; the screen says where to start and whether to start.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evidence/jev/restatement-baseline.json"


def _mod(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


L2 = _mod("chain_l2", "scripts/chain_l2.py")
JEV = _mod("jev_select", "scripts/jev_select.py")


def changed_elements(job: str) -> dict:
    """What this cycle changed, against the selection the projections compiled from."""
    base = ROOT / "chain/l2" / job
    working = json.loads((base / "semantic-model.json").read_text())
    selected = json.loads((base / "selected-model.json").read_text()) if (base / "selected-model.json").exists() else {"types": [], "entities": [], "handoffs": [], "invariants": [], "holes": [], "sufficiency_groups": []}
    now, before = L2.element_steps(working), L2.element_steps(selected)
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    changed = sorted(e for e in set(now) & set(before) if any(now[e].get(k) != before[e].get(k) for k in set(now[e]) | set(before[e])))
    return {"working": working, "added": added, "removed": removed, "changed": changed}


def relevant_holes(model: dict, element_id: str, holes: dict) -> list[str]:
    """The holes worth asking about for one element: those its own group's gap names. A group's gap is the declared
    statement of what bounds its claim, so it is also the list of questions its members could wrongly answer."""
    for group in model.get("sufficiency_groups", []):
        if element_id in group.get("members", []):
            return [h for h in L2.holes_named(group.get("gap", "")) if h in holes]
    return []


def settled_this_cycle(l1: dict) -> dict:
    """What the business just settled: holes gone from L1 since the manifest was baselined, and clauses whose text moved.
    A field left treating one of these as open is the defect a diff-scoped screen is blind to."""
    manifest = ROOT / "chain/manifest.json"
    if not manifest.exists():
        return {}
    previous = json.loads(manifest.read_text()).get("l1", {})
    settled = {h: t for h, t in (previous.get("holes") or {}).items() if h not in l1["holes"]}
    for c, t in (previous.get("clauses") or {}).items():
        if c in l1["clauses"] and l1["clauses"][c] != t:
            settled[c] = f"{t}\n\nThis has since been amended to: {l1['clauses'][c]}"
    return settled


def screen(job: str, contract: Path | None = None) -> dict:
    l1 = L2.parse_l1()
    settled = settled_this_cycle(l1)
    delta = changed_elements(job)
    working = delta["working"]
    by_id = {e["id"]: e for e in working.get("invariants", [])}
    for entity in working.get("entities", []):
        by_id[entity["id"]] = entity
        for attr in entity.get("attributes", []):
            by_id[f"{entity['id']}.{attr['name']}"] = attr
    for handoff in working.get("handoffs", []):
        by_id[f"handoff.{handoff['from']}->{handoff['to']}"] = handoff
    selected_path = ROOT / "chain/l2" / job / "selected-model.json"
    before_by_id = {}
    if selected_path.exists():
        selected = json.loads(selected_path.read_text())
        for inv in selected.get("invariants", []):
            before_by_id[inv["id"]] = inv
        for ent in selected.get("entities", []):
            before_by_id[ent["id"]] = ent
            for attr in ent.get("attributes", []):
                before_by_id[f"{ent['id']}.{attr['name']}"] = attr
        for h in selected.get("handoffs", []):
            before_by_id[f"handoff.{h['from']}->{h['to']}"] = h
    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else {"p90": 0.74, "max": 0.82, "median": 0.5}
    holes = {h: l1["holes"][h] for h in l1["holes"]}

    findings = []
    for eid in delta["added"] + delta["changed"]:
        element = by_id.get(eid)
        if not element or not element.get("statement") and not element.get("derivation"):
            continue
        cited = {c: l1["clauses"][c] for c in element.get("derived_from", []) if c in l1["clauses"]}
        entry = {"element": eid, "state": "added" if eid in delta["added"] else "changed"}
        if cited:
            r = JEV.restates_or_adds(cited, element)
            if r.get("verdict") == "ran":
                entry["p_adds_a_decision"] = round(r["p_adds_a_decision"], 3)
                entry["rank_against_reviewed"] = ("above every reviewed element" if r["p_adds_a_decision"] > baseline["max"]
                                                  else "top decile" if r["p_adds_a_decision"] >= baseline["p90"]
                                                  else "typical" if r["p_adds_a_decision"] >= baseline["median"] else "low")
        # mechanical, not judged: an element inside a group a hole bounds, whose own text never names that hole, is
        # where an unauthorized answer has historically hidden. Whether it actually answers the question is for a
        # runnable counterexample and a capable reader, not for a selector that reads rather than derives.
        # A hint, not a finding. Only fields this cycle left alone, on elements it did touch: an element written fresh
        # against the answer discusses the settled subject by design. Even so it scores on subject overlap rather than on
        # staleness, and its first live flag was a false positive (a frozen-reference trigger that never mentions closure,
        # flagged because its element gained the clause). Worth a reviewer's eye over a handful of fields; never a verdict.
        previous = before_by_id.get(eid) or {}
        for question, text in settled.items() if eid in delta["changed"] else []:
            for field in ("statement", "necessity", "parallel_assumption", "review_trigger"):
                if not element.get(field) or element.get(field) != previous.get(field):
                    continue
                r = JEV.treats_a_settled_question_as_open(text, field, element[field])
                if r.get("verdict") == "ran" and r["flag"]:
                    entry.setdefault("fields_worth_rereading_against_the_answer", []).append({"question": question, "field": field, "p": round(r["p_treats_as_open"], 2)})
        bounding = relevant_holes(working, eid, holes)
        silent = [h for h in bounding if h.replace("L1.hole.", "").replace("-", "_") not in json.dumps(element)]
        if silent:
            entry["bounded_by_holes_it_never_names"] = silent
        findings.append(entry)

    findings.sort(key=lambda f: (-len(f.get("fields_worth_rereading_against_the_answer", [])), -len(f.get("bounded_by_holes_it_never_names", [])), -f.get("p_adds_a_decision", 0)))
    out = {"job": job, "added": delta["added"], "removed": delta["removed"], "changed": delta["changed"], "findings": findings}

    if contract and contract.exists():
        w = JEV.within_contract(contract.read_text(), delta["added"] + delta["changed"] + delta["removed"])
        if w.get("verdict") == "ran":
            out["contract_scope"] = {"p_outside_scope": round(w["p_outside_scope"], 3), "confidence": w["confidence_band"]}
    summary = {"job": job, "added": len(delta["added"]), "removed": len(delta["removed"]), "changed": len(delta["changed"]),
               "elements": (delta["added"] + delta["changed"])[:12],
               "top_flags": [f["element"] for f in findings[:3] if f.get("rank_against_reviewed") in ("top decile", "above every reviewed element") or f.get("fields_worth_rereading_against_the_answer") or f.get("bounded_by_holes_it_never_names")]}
    t = JEV.review_needed(summary)
    if t.get("verdict") == "ran":
        out["triage"] = {"depth": t["depth"], "confidence": t.get("confidence"), "probabilities": {k: round(v, 2) for k, v in (t.get("probabilities") or {}).items()}}
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("job")
    p.add_argument("--contract", type=Path)
    a = p.parse_args()
    print(json.dumps(screen(a.job, a.contract), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
