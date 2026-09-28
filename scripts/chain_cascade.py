#!/usr/bin/env python3
"""What the current tree needs recompiled, and who does it. A report: it reads, runs gates, and writes nothing.

    .venv/bin/python scripts/chain_cascade.py            # human-readable
    .venv/bin/python scripts/chain_cascade.py --json     # the same, as one JSON document
    .venv/bin/python scripts/chain_cascade.py --no-jev   # skip Jev: every hash-changed group stays stale

1. L2: chain_l2.plan() fingerprints every sufficiency group against chain/manifest.json. A moved group is asked of
   Jev; per job this prints hit / hit-by-jev / hit-by-adjudication / review / stale, with Jev's probabilities.
2. A job with stale groups needs a Developer to recompile its L2. The handoff is printed; nothing is spawned.
3. A job whose L2 is selected and in sync is checked at L3 on every engine target: which artifacts and audits are
   stale or kept, the Developer handoff for stale ones, and the reviewer handoff for a projection awaiting a stamp.
4. Jobs run in JOB_ORDER. A job is blocked on a target while an upstream there is unaccepted.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def _mod(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


L2 = _mod("chain_l2", "scripts/chain_l2.py")
L3 = _mod("chain_l3", "scripts/chain_l3.py")
CACHE_STATES = ("hit", "hit-by-jev", "hit-by-adjudication", "review", "stale")


def targets() -> list[str]:
    return sorted(p.stem for p in (ROOT / "chain/profiles").glob("*.json"))


def l2_in_sync(job: str) -> tuple[bool, str]:
    """Selected (a passing review) and in sync (the working model is the text that review covered)."""
    review_path, model_path = L2.L2_DIR / job / "review.json", L2.L2_DIR / job / "semantic-model.json"
    if not review_path.exists():
        return False, "no L2 review"
    review = json.loads(review_path.read_text())
    if review.get("verdict") != "pass":
        return False, f"L2 review verdict is {review.get('verdict')}"
    if review.get("model_sha256") != hashlib.sha256(model_path.read_text().encode()).hexdigest():
        return False, "semantic-model.json changed since its review; the L2 awaits a sketch review and selection"
    return True, "selected and in sync"


def cascade(use_jev: bool = True) -> dict:
    previous = json.loads(L2.MANIFEST.read_text()) if L2.MANIFEST.exists() else {}
    plan = L2.plan(previous=previous, use_jev=use_jev)
    out = {"changed_clauses": plan["changed_clauses"], "changed_holes": plan["changed_holes"], "jobs": {}}
    accepted = {}  # (target, job) -> acceptance, filled in JOB_ORDER so a downstream job sees its upstreams
    for job in L3.JOB_ORDER:
        jp = plan["jobs"].get(job, {})
        if jp.get("status") != "ok":
            out["jobs"][job] = {"l2": {"status": jp.get("status", "missing")}, "l3": {}}
            continue
        groups = {s: [] for s in CACHE_STATES}
        jev = {}
        for gid, info in sorted(jp["elements"].items()):
            state = "stale" if info["cache"] in ("stale", "stale-new") else info["cache"]
            groups.setdefault(state, []).append(gid)
            if info.get("jev"):
                jev[gid] = [{"clause": c, "p_behavior_changes": v.get("p_behavior_changes"), "decision": v.get("decision")}
                            for c, v in zip(info.get("touched_clauses") or [], info["jev"])]
        in_sync, why = l2_in_sync(job)
        # A stale group whose fingerprint has not moved since the chain manifest recorded it, on a job selected at the
        # sha that manifest recorded, is stale because not every engine has stamped it yet -- the L2 was already
        # recompiled and selected. Only a group that moved now owes an L2 recompile.
        prev = previous.get("jobs", {}).get(job, {})
        persisted = [g for g in groups["stale"] if prev.get("elements", {}).get(g, {}).get("fingerprint") == jp["elements"][g]["fingerprint"]
                     and prev.get("selected_model_sha256") == jp.get("selected_model_sha256")]
        fresh = [g for g in groups["stale"] if g not in persisted]
        entry = {"l2": {"groups": groups, "jev": jev, "selected": in_sync, "selection": why, "stale_awaiting_l3_stamps": persisted}, "l3": {}}
        if fresh:
            entry["l2"]["handoff"] = {"to": "Developer (L2 recompile)", "job": job, "stale_groups": fresh,
                                      "touched_clauses": sorted({c for g in fresh for c in jp["elements"][g].get("touched_clauses") or []}),
                                      "command": f".venv/bin/python scripts/chain_l2.py check {job}"}
        if groups["review"]:
            entry["l2"]["adjudication_needed"] = groups["review"]
        for target in targets():
            blocked = [up for up in L3.JOB_ORDER[: L3.JOB_ORDER.index(job)] if not accepted.get((target, up), {}).get("accepted")]
            t = {}
            if not in_sync or fresh:
                t = {"status": "waiting-on-l2", "why": why if not in_sync else f"groups {fresh} need an L2 recompile"}
            else:
                r = L3.check(target, job)
                t = {"status": r["status"], **{k: r.get(k, []) for k in ("artifacts_stale", "artifacts_kept", "audits_stale", "audits_kept")},
                     "acceptance": r.get("acceptance")}
                acc = r.get("acceptance") or {}
                # stale files on a projection still exactly as accepted: nothing has been recompiled, a Developer owes it.
                # On one recompiled since, the Developer is done; the reviewer judges the stale files and may skip the kept.
                if (t["artifacts_stale"] or t["audits_stale"]) and acc.get("accepted"):
                    t["developer_handoff"] = {"to": f"Developer ({target})", "rebuild": t["artifacts_stale"] + t["audits_stale"],
                                              "groups": r.get("groups_moved_unresolved", []), "command": f".venv/bin/python scripts/chain_l3.py check {target} {job}"}
                if not acc.get("accepted"):
                    t["reviewer_handoff"] = {"to": f"L3 reviewer ({target})", "acceptance": acc, "judge": t["artifacts_stale"] + t["audits_stale"],
                                             "may_skip": t["artifacts_kept"] + t["audits_kept"], "questions": r.get("questions", [])}
            if blocked:
                t["blocked_by"] = blocked
            accepted[(target, job)] = L3.acceptance(target, job) if (L3.L3_DIR / target / job / "manifest.json").exists() else {"accepted": False}
            entry["l3"][target] = t
        out["jobs"][job] = entry
    stale_jobs = [j for j, e in out["jobs"].items() if e["l2"].get("groups", {}).get("stale")]
    rebuild = sum(len(t["artifacts_stale"]) for e in out["jobs"].values() for t in e["l3"].values() if "developer_handoff" in t)
    to_review = sum(len(t["artifacts_stale"]) for e in out["jobs"].values() for t in e["l3"].values() if "reviewer_handoff" in t)
    kept = sum(len(t.get("artifacts_kept", [])) for e in out["jobs"].values() for t in e["l3"].values())
    n_stale = sum(len(out["jobs"][j]["l2"]["groups"]["stale"]) for j in stale_jobs)
    out["summary"] = {"groups_stale": n_stale, "jobs_with_stale_groups": len(stale_jobs), "artifacts_to_rebuild": rebuild, "artifacts_kept": kept, "artifacts_awaiting_review": to_review,
                      "line": f"{n_stale} groups stale across {len(stale_jobs)} jobs, {rebuild} artifacts to rebuild, {kept} kept, {to_review} recompiled and awaiting review"}
    return out


def render(doc: dict) -> None:
    print(f"L1 changed since the chain manifest: clauses {doc['changed_clauses'] or '[]'}, holes {doc['changed_holes'] or '[]'}")
    for job, e in doc["jobs"].items():
        print(f"\n== {job}")
        l2 = e["l2"]
        if "groups" not in l2:
            print(f"  L2: {l2.get('status')}"); continue
        print("  L2 groups: " + "  ".join(f"{s} {len(g)}" for s, g in l2["groups"].items()) + f"   ({l2['selection']})")
        for s in ("hit-by-jev", "hit-by-adjudication", "review", "stale"):
            for gid in l2["groups"][s]:
                probs = ", ".join(f"{v['clause']} p={v['p_behavior_changes']}" for v in l2["jev"].get(gid, []))
                print(f"    {s:20} {gid}" + (f"  [Jev: {probs}]" if probs else ""))
        if l2["stale_awaiting_l3_stamps"]:
            print(f"  stale groups {l2['stale_awaiting_l3_stamps']} are already recompiled and selected at L2; they clear when every engine target stamps them")
        if "handoff" in l2:
            h = l2["handoff"]
            print(f"  -> {h['to']}: groups {h['stale_groups']} moved under {h['touched_clauses']}; run `{h['command']}`")
        if "adjudication_needed" in l2:
            print(f"  -> reviewer: adjudicate keep/invalidate for {l2['adjudication_needed']} (chain/cache-adjudications.jsonl)")
        for target, t in e["l3"].items():
            head = f"  L3 {target}: {t['status']}" + (f" -- {t['why']}" if "why" in t else "")
            if "blocked_by" in t:
                head += f"; BLOCKED: upstream {t['blocked_by']} not accepted on {target}, so `run` refuses this job"
            print(head)
            if "artifacts_stale" in t:
                print(f"    artifacts stale {t['artifacts_stale']}  kept {t['artifacts_kept']}")
                print(f"    audits stale {len(t['audits_stale'])}  kept {len(t['audits_kept'])}")
            if "developer_handoff" in t:
                print(f"    -> {t['developer_handoff']['to']}: rebuild {len(t['developer_handoff']['rebuild'])} files for groups {t['developer_handoff']['groups']}")
            if "reviewer_handoff" in t:
                h = t["reviewer_handoff"]
                print(f"    -> {h['to']}: awaiting stamp ({h['acceptance'].get('reason')}); judge {len(h['judge'])} files, may skip {len(h['may_skip'])}; run `chain_l3.py check {target} {job}` for the questions")
    print(f"\n{doc['summary']['line']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-jev", action="store_true", help="do not call Jev; hash-changed groups stay stale")
    a = p.parse_args()
    doc = cascade(use_jev=not a.no_jev)
    print(json.dumps(doc, indent=2, default=str)) if a.json else render(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
