#!/usr/bin/env python3
"""L1 -> L2 machinery: parse the intent Sketch, fingerprint clauses, gate compiled semantic models, plan the cache.

S1 = sketches/l1-brokerage-intent-v1.md. K2 = chain/anchors/*. P1 = chain/l2/<job>/semantic-model.json (Developer-written).
G2 = this file's `check`. The cache manifest is chain/manifest.json. Jev decides invalidation above the hash floor.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
import os
L1 = ROOT / os.environ.get("CHAIN_L1", "sketches/l1-brokerage-intent-v1.md")
SCHEMA = ROOT / "chain/anchors/semantic-model-v2.schema.json"
WEAVE = ROOT / "chain/weave.json"
SOURCES = ROOT / "chain/anchors/sources-v1.json"
L2_DIR = ROOT / os.environ.get("CHAIN_L2_DIR", "chain/l2")
MANIFEST = ROOT / os.environ.get("CHAIN_MANIFEST", "chain/manifest.json")
L2_CONTRACT_VERSION = "l1-to-l2/v2"
JOB_ORDER = ["ownership-history", "trade-lifecycle", "positions"]
CLAUSE = re.compile(r"^- \*\*(L1\.(?!hole\.)[a-z0-9-]+)\*\* — (.+)$")
HOLE = re.compile(r"^- \*\*(L1\.hole\.[a-z0-9-]+)\*\* — (.+)$")
JOB = re.compile(r"^- \*\*job:([a-z0-9-]+)\*\* — (.+?) Clauses: (.+)$")
FEEDBACK = re.compile(r"^\s+- feedback: (.+)$")


def _mod(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


class L2Error(ValueError):
    pass


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_l1(path: Path = L1) -> dict:
    clauses, holes, jobs = {}, {}, {}
    last_job = None
    for line in path.read_text().splitlines():
        if m := CLAUSE.match(line):
            clauses[m.group(1)] = norm(m.group(2))
        elif m := HOLE.match(line):
            holes[m.group(1)] = norm(m.group(2))
        elif m := JOB.match(line):
            jobs[m.group(1)] = {"description": norm(m.group(2)), "clauses": [c.strip() for c in m.group(3).split(",")], "feedback": ""}
            last_job = m.group(1)
        elif m := FEEDBACK.match(line):
            jobs[last_job]["feedback"] = norm(m.group(1))
    if not clauses or not jobs:
        raise L2Error("L1 Sketch has no parseable clauses or jobs")
    for job, spec in jobs.items():
        for c in spec["clauses"]:
            if c not in clauses:
                raise L2Error(f"job {job} lists unknown clause {c}")
    return {"path": str(path.relative_to(ROOT)), "clauses": clauses, "holes": holes, "jobs": jobs,
            "clause_fingerprints": {c: sha(t) for c, t in clauses.items()}, "hole_fingerprints": {h: sha(t) for h, t in holes.items()}}


def check(job: str, l1: dict | None = None) -> dict:
    """Gate G2 for one compiled semantic model. Returns a report; raises nothing for model defects, lists them."""
    l1 = l1 or parse_l1()
    path = L2_DIR / job / "semantic-model.json"
    if not path.exists():
        return {"job": job, "status": "missing"}
    doc = json.loads(path.read_text())
    problems = []
    schema = json.loads(SCHEMA.read_text())
    for e in sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path)):
        problems.append(f"schema: {e.message} at {'/'.join(map(str, e.path))}")
    if doc.get("job") != job:
        problems.append(f"job field {doc.get('job')} does not match directory {job}")
    questions = list(doc.get("questions_for_authority") or [])
    allowed_clauses = set(l1["jobs"].get(job, {}).get("clauses", []))
    types = {t["id"]: t for t in doc.get("types", [])}
    GUARD = _mod("merge_guard", "scripts/merge_guard.py")
    frozen = GUARD.FROZEN

    def cites(elem, label):
        for c in elem.get("derived_from", []):
            if c not in l1["clauses"]:
                problems.append(f"{label} cites unknown clause {c}")
            elif c not in allowed_clauses:
                problems.append(f"{label} cites {c}, which job {job} does not list")

    for t in doc.get("types", []):
        cites(t, f"type {t['id']}")
        if t["mutation_role"] == frozen and t.get("disposition") != "rejected":
            texts = " ".join(l1["clauses"].get(c, "") for c in t["derived_from"]).lower()
            if not any(k in texts for k in ("do not move", "does not change", "leave", "never re-attributed", "as first recorded", "as that trade's ownership was recorded")):
                problems.append(f"type {t['id']} is frozen but no cited clause says the value does not change after first recording")
    entities = {e["id"]: e for e in doc.get("entities", [])}
    for e in doc.get("entities", []):
        cites(e, f"entity {e['id']}")
        names = set()
        for a in e["attributes"]:
            cites(a, f"attribute {e['id']}.{a['name']}")
            if a["semantic_type"] not in types:
                problems.append(f"attribute {e['id']}.{a['name']} uses undeclared type {a['semantic_type']}")
            elif types[a["semantic_type"]]["mutation_role"] == "none":
                problems.append(f"attribute {e['id']}.{a['name']} carries a type with mutation_role none")
            if "mutation_role" in a or "role" in a:
                problems.append(f"attribute {e['id']}.{a['name']} declares a role on a column; roles live on types")
            names.add(a["name"])
        for ident in e["identifiers"]:
            if ident not in names:
                problems.append(f"entity {e['id']} identifier {ident} is not an attribute")
            elif types.get(next(a["semantic_type"] for a in e["attributes"] if a["name"] == ident), {}).get("mutation_role") != "identity":
                problems.append(f"entity {e['id']} identifier {ident} must carry an identity-role type")
        if e["history"] == "incremental_by_identity":
            roles = {types[a["semantic_type"]]["mutation_role"] for a in e["attributes"] if a["semantic_type"] in types}
            if frozen not in roles:
                problems.append(f"entity {e['id']} is incremental_by_identity but carries no frozen attribute; if nothing is frozen the kind is wrong or a clause is missing")
    # handoffs: typing and containment
    sources = json.loads(SOURCES.read_text())
    source_fields = {f"{ent['name']}.{f['name']}": f["physical_type"] for ent in sources["entities"] for f in ent["fields"]}
    upstream = {}
    for up in doc.get("upstream_jobs", []):
        if JOB_ORDER.index(up) >= JOB_ORDER.index(job) if job in JOB_ORDER and up in JOB_ORDER else True:
            problems.append(f"upstream job {up} is not upstream of {job} in {JOB_ORDER}")
        up_path = L2_DIR / up / "semantic-model.json"
        if up_path.exists():
            up_doc = json.loads(up_path.read_text())
            up_types = {t["id"]: t for t in up_doc["types"]}
            for ue in up_doc["entities"]:
                for ua in ue["attributes"]:
                    upstream[f"{ue['id']}.{ua['name']}"] = up_types.get(ua["semantic_type"], {})
    for h in doc.get("handoffs", []):
        cites(h, f"handoff {h['from']} -> {h['to']}")
        to_entity, to_attr = h["to"].rsplit(".", 1)
        target = next((a for a in entities.get(to_entity, {}).get("attributes", []) if a["name"] == to_attr), None)
        if target is None:
            problems.append(f"handoff target {h['to']} is not an attribute of this job")
            continue
        if h["from"].startswith(("raw.", "ce.")):
            if h["from"] not in source_fields:
                problems.append(f"handoff source {h['from']} is not an anchored source field")
        else:
            from_entity, from_attr = h["from"].rsplit(".", 1)
            local = next((a for a in entities.get(from_entity, {}).get("attributes", []) if a["name"] == from_attr), None)
            if local is not None:
                if local["semantic_type"] != target["semantic_type"]:
                    lt, tt = types.get(local["semantic_type"], {}), types.get(target["semantic_type"], {})
                    same_meaning = (lt.get("semantic_kind"), lt.get("physical_type")) == (tt.get("semantic_kind"), tt.get("physical_type"))
                    if not (same_meaning and tt.get("mutation_role") in ("identity", "frozen_from_first_encounter")):
                        problems.append(f"handoff {h['from']} -> {h['to']} changes semantic type {local['semantic_type']} -> {target['semantic_type']} without a conversion clause; a same-job handoff may change the type id only when semantic_kind and physical_type match and the target role is identity or frozen (an aggregate key or a frozen copy)")
            elif h["from"] in upstream:
                up_t = upstream[h["from"]]
                my_t = types.get(target["semantic_type"], {})
                if (up_t.get("semantic_kind"), up_t.get("physical_type")) != (my_t.get("semantic_kind"), my_t.get("physical_type")):
                    problems.append(f"handoff {h['from']} -> {h['to']}: this job's type {target['semantic_type']} does not match the upstream type in meaning (semantic_kind) or physical type; mutation role may differ because it belongs to the consuming entity's lifecycle")
            else:
                problems.append(f"handoff source {h['from']} is neither a local attribute, an anchored source, nor an attribute of a listed upstream job")
    for inv in doc.get("invariants", []):
        cites(inv, f"invariant {inv['id']}")
        if inv["entity"] not in entities:
            problems.append(f"invariant {inv['id']} names unknown entity {inv['entity']}")
    for hole in doc.get("holes", []):
        if hole["derived_from_hole"] not in l1["holes"]:
            problems.append(f"hole {hole['id']} cites unknown L1 hole {hole['derived_from_hole']}")
    # every L1 hole whose text touches this job's domain words must be carried (cheap heuristic, reported not fatal)
    carried = {h["derived_from_hole"] for h in doc.get("holes", [])}
    # S&T structure: dispositions, rejected reasons, group membership, clause coverage
    steps = element_steps(doc)
    for eid, st in steps.items():
        if st.get("disposition") == "rejected" and not st.get("rejected_because"):
            problems.append(f"{eid} is rejected without rejected_because")
        if st.get("disposition") == "selected":
            problems.append(f"{eid} claims selected; only a reviewer selects, outside this file")
    groups = {g["id"]: g for g in doc.get("sufficiency_groups", [])}
    membership = {}
    for g in groups.values():
        for c in g["parent_clauses"]:
            if c not in allowed_clauses:
                problems.append(f"group {g['id']} claims clause {c}, which job {job} does not list")
        for mid in g["members"]:
            if mid not in steps:
                problems.append(f"group {g['id']} names unknown member {mid}")
            membership.setdefault(mid, []).append(g["id"])
    for eid, st in steps.items():
        if st.get("disposition") == "rejected":
            continue
        if st.get("sufficiency_group") not in groups:
            problems.append(f"{eid} names group {st.get('sufficiency_group')} that is not declared")
        if len(membership.get(eid, [])) != 1:
            problems.append(f"{eid} must be a member of exactly one group; found {membership.get(eid, [])}")
        elif membership[eid][0] != st.get("sufficiency_group"):
            problems.append(f"{eid} says group {st.get('sufficiency_group')} but is listed in {membership[eid][0]}")
    # cycle-1 mechanizations of reviewer findings
    time_types = {t["id"] for t in doc.get("types", []) if t["time_role"] in ("effective", "event")}
    flag_types = {t["id"] for t in doc.get("types", []) if t["physical_type"].lower() in ("boolean", "bool")}
    for e in doc.get("entities", []):
        if e["history"] != "versioned":
            continue
        content = []
        for a in e["attributes"]:
            role = types.get(a["semantic_type"], {}).get("mutation_role")
            if a["name"] not in e["identifiers"] and role == "mutable":
                problems.append(f"{e['id']}.{a['name']} is mutable inside a versioned entity; statement values are per_statement, never replaced in place")
            if a["name"] not in e["identifiers"] and a["semantic_type"] not in time_types and a["semantic_type"] not in flag_types and role != "identity":
                content.append(a["name"])
        if not content and not questions:
            problems.append(f"{e['id']} is versioned but carries no statement content and no question is filed; if the Sketch does not say what a statement carries, file the question rather than supply content from anchors")
        # handoffs into this entity: a source supplying no effective-time handoff cannot produce a dated statement
        sources_into = {}
        for h in doc.get("handoffs", []):
            if h["to"].startswith(e["id"] + "."):
                src_entity = h["from"].rsplit(".", 1)[0]
                sources_into.setdefault(src_entity, set()).add(h["to"].rsplit(".", 1)[1])
        effective_attrs = {a["name"] for a in e["attributes"] if a["semantic_type"] in time_types}
        for src, attrs in sources_into.items():
            if not attrs & effective_attrs:
                for h in doc.get("handoffs", []):
                    if h["to"].startswith(e["id"] + ".") and h["from"].startswith(src + ".") and h.get("disposition") == "candidate":
                        problems.append(f"handoff {h['from']}->{h['to']} is candidate but {src} supplies no effective time for {e['id']}; defer it under the hole that blocks it")
    # review-2 mechanizations: a projectable source must supply every non-nullable attribute; no dangling question references; non-nullable needs a source
    all_text = json.dumps(doc)
    if "questions_for_authority" in all_text.replace('"questions_for_authority"', "", 1) and not questions:
        problems.append("elements refer to questions_for_authority but no question is filed")
    for e in doc.get("entities", []):
        candidate_targets = {}
        for h in doc.get("handoffs", []):
            if h["to"].startswith(e["id"] + ".") and h.get("disposition") == "candidate":
                candidate_targets.setdefault(h["from"].rsplit(".", 1)[0], set()).add(h["to"].rsplit(".", 1)[1])
        any_candidate = set().union(*candidate_targets.values()) if candidate_targets else set()
        derived = {a["name"] for a in e["attributes"] if a.get("derivation")}
        for a in e["attributes"]:
            if not a["nullable"] and a["name"] not in any_candidate and a["name"] not in derived and a.get("disposition") == "candidate":
                problems.append(f"{e['id']}.{a['name']} is nullable false and candidate but has no candidate handoff from any source and no derivation")
        if e["history"] == "versioned":
            effective_attrs = {a["name"] for a in e["attributes"] if a["semantic_type"] in time_types}
            required = {a["name"] for a in e["attributes"] if not a["nullable"] and a.get("disposition") == "candidate"} - set(e["identifiers"]) - effective_attrs - derived
            for src, attrs in candidate_targets.items():
                if attrs & effective_attrs and not required <= attrs:
                    problems.append(f"source {src} can produce {e['id']} statements but supplies no candidate handoff for required {sorted(required - attrs)}; supply them, make them nullable with a note, or defer/reject with a reason")
    # review-3 mechanization: action-code enumerations in handoff justifications must agree per entity and match the anchored subjects
    meanings = sources.get("action_type_meanings", {})
    codes = set(meanings.get("codes", {}))
    subjects = meanings.get("subjects", {})
    entity_subjects = meanings.get("entity_subjects", {})
    per_entity = {}
    for h in doc.get("handoffs", []):
        if not h["from"].startswith("raw.customer_mgmt_action."):
            continue
        text = str(h.get("necessity", ""))  # enumerations are claims of necessity; notes and triggers may mention other codes
        named = {c for c in codes if re.search(rf"\b{c}\b", text)}
        if named:
            per_entity.setdefault(h["to"].rsplit(".", 1)[0], []).append((h["from"], named))
    for ent, items in per_entity.items():
        subject = entity_subjects.get(ent)
        sets = {frozenset(n) for _, n in items}
        if len(sets) > 1:
            problems.append(f"{ent}: handoffs enumerate different action-code sets {[sorted(n) for _, n in items]}; they must agree")
        for src, named in items:
            wrong = sorted(c for c in named if subject and subject not in subjects.get(c, []))
            if wrong:
                problems.append(f"handoff {src}->{ent} names {wrong}, which the anchors define as not about a {subject}")
    # L3-simulation mechanization: an action that omits a fact must not leave a non-nullable statement attribute empty
    fields_present = meanings.get("fields_present", {})
    for e in doc.get("entities", []):
        if e["history"] != "versioned":
            continue
        subject = entity_subjects.get(e["id"])
        producing = [c for c, subj in subjects.items() if subject in subj]
        by_attr = {}
        for h in doc.get("handoffs", []):
            if h["to"].startswith(e["id"] + ".") and h["from"].startswith("raw.customer_mgmt_action.") and h.get("disposition") == "candidate":
                by_attr.setdefault(h["to"].rsplit(".", 1)[1], set()).add(h["from"].rsplit(".", 1)[1])
        for a in e["attributes"]:
            fields = by_attr.get(a["name"], set())
            if not fields or a["nullable"] or a.get("derivation"):
                continue
            omitted_by = sorted(c for c in producing if isinstance(fields_present.get(c), list) and not fields <= set(fields_present[c]) and "action_type" not in fields)
            if omitted_by:
                problems.append(f"{e['id']}.{a['name']} is handed off from {sorted(fields)}, which actions {omitted_by} omit; declare carried_forward_from_previous_statement, or make it nullable with a note")
    for g in groups.values():
        gap = g["gap"].strip()
        if gap.lower() != "none" and not re.search(r"L1\.hole\.[a-z0-9-]+", gap):
            problems.append(f"group {g['id']} gap must be 'none' or name an L1 hole; anchor limitations belong in questions_for_authority")
        for mid in g["members"]:
            st = steps.get(mid)
            if st and not set(st.get("derived_from", [])) <= set(g["parent_clauses"]):
                problems.append(f"{mid} cites {sorted(set(st['derived_from']) - set(g['parent_clauses']))} outside its group's parent clauses; add the clause to the group's parent_clauses or move the member")
    deferred_groups = {steps[m].get("sufficiency_group") for m, st in steps.items() if st.get("disposition") == "deferred" for _ in [0]}
    for hole in doc.get("holes", []):
        blocks = set(hole.get("blocks", []))
        for gid in deferred_groups:
            if gid and gid not in blocks and any(steps[m].get("disposition") == "deferred" and steps[m].get("sufficiency_group") == gid and hole["derived_from_hole"] in " ".join(str(steps[m].get(k, "")) for k in ("necessity", "parallel_assumption", "note", "review_trigger")) for m in steps):
                problems.append(f"hole {hole['id']} blocks deferred members of {gid} but does not list it in blocks")
    # review-3 (trade-lifecycle) mechanization: holes' blocks and groups' gaps must agree in both directions
    for hole in doc.get("holes", []):
        for gid in hole.get("blocks", []) or []:
            if gid in groups and hole["derived_from_hole"] not in groups[gid]["gap"]:
                problems.append(f"hole {hole['id']} blocks {gid} but that group's gap does not name {hole['derived_from_hole']}")
    holes_by_l1 = {h["derived_from_hole"]: h for h in doc.get("holes", [])}
    for g in groups.values():
        for hid in re.findall(r"L1\.hole\.[a-z0-9-]+", g["gap"]):
            hole = holes_by_l1.get(hid)
            if hole is None:
                problems.append(f"group {g['id']} gap names {hid}, which the model does not carry as a hole")
            elif g["id"] not in (hole.get("blocks") or []):
                problems.append(f"group {g['id']} gap names {hid} but hole {hole['id']} does not list the group in blocks")
    covered = {c for g in groups.values() for c in g["parent_clauses"]}
    for c in sorted(allowed_clauses - covered):
        problems.append(f"clause {c} has no sufficiency group in job {job}: gap")
    status = "rejected" if problems else ("question" if questions else "ok")
    return {"job": job, "status": status, "problems": problems, "questions": questions, "holes_carried": sorted(carried),
            "groups": {g: {"parents": groups[g]["parent_clauses"], "gap": groups[g]["gap"]} for g in groups},
            "elements": {"types": len(types), "entities": len(entities), "handoffs": len(doc.get("handoffs", [])), "invariants": len(doc.get("invariants", []))}}


def element_steps(doc: dict) -> dict[str, dict]:
    """Flatten every element to its step id with its S&T fields."""
    steps = {}
    for t in doc.get("types", []):
        steps[f"type.{t['id']}"] = t
    for e in doc.get("entities", []):
        steps[e["id"]] = e
        for a in e.get("attributes", []):
            steps[f"{e['id']}.{a['name']}"] = a
    for h in doc.get("handoffs", []):
        steps[f"handoff.{h['from']}->{h['to']}"] = h
    for inv in doc.get("invariants", []):
        steps[inv["id"]] = inv
    return steps


def weave(l1: dict | None = None) -> dict:
    """Interweave sibling L2s: overlap, dependency, gap, contradiction across jobs. Written for review, not self-certifying."""
    l1 = l1 or parse_l1()
    docs = {j: json.loads((L2_DIR / j / "semantic-model.json").read_text()) for j in JOB_ORDER if (L2_DIR / j / "semantic-model.json").exists()}
    relations = []
    # overlap and contradiction: the same semantic kind (and physical type) realized in two jobs must carry one mutation role
    kinds = {}
    for j, d in docs.items():
        for t in d["types"]:
            kinds.setdefault((t["semantic_kind"], t["physical_type"]), []).append((j, t["id"], t["mutation_role"]))
    for key, uses in kinds.items():
        if len({u[0] for u in uses}) > 1:
            roles = {u[2] for u in uses}
            # role belongs to the consuming entity's lifecycle: a downstream job may freeze a copy of an upstream value or key an
            # aggregate on it (identity). A contradiction is a downstream `mutable` on a meaning that is fixed upstream, or `none` alongside a projected role.
            fixed = {"per_statement", "frozen_from_first_encounter", "identity"}
            contradiction = ("mutable" in roles and roles & fixed) or ("none" in roles and roles - {"none"})
            if len(roles) > 1 and not contradiction:
                relations.append({"relation": "overlap", "semantic_kind": key[0], "uses": uses, "note": "same meaning; roles differ by the consuming entity's lifecycle (statement value, frozen copy, aggregate key)"})
            else:
                relations.append({"relation": "contradiction" if len(roles) > 1 else "overlap", "semantic_kind": key[0], "uses": uses, "note": "a downstream mutable role on a meaning fixed upstream, or none beside a projected role" if len(roles) > 1 else "same meaning realized in several jobs; keep one definition"})
    # dependency: handoffs from upstream entities
    for j, d in docs.items():
        for h in d["handoffs"]:
            if h["from"].startswith("logical.") and not any(h["from"].startswith(e["id"] + ".") for e in d["entities"]):
                relations.append({"relation": "dependency", "from_job": next((uj for uj, ud in docs.items() if any(h["from"].startswith(e["id"] + ".") for e in ud["entities"])), None), "to_job": j, "handoff": f"{h['from']}->{h['to']}"})
    # gap: L1 clauses covered by no group in any job; L1 holes carried by no job
    covered = {c for d in docs.values() for g in d.get("sufficiency_groups", []) for c in g["parent_clauses"]}
    for c in l1["clauses"]:
        if c not in covered:
            relations.append({"relation": "gap", "clause": c, "note": "no job's sufficiency group covers this clause"})
    carried = {h["derived_from_hole"] for d in docs.values() for h in d.get("holes", [])}
    for h in l1["holes"]:
        if h not in carried:
            relations.append({"relation": "gap", "hole": h, "note": "no job carries this hole; either it touches no job or a job filled it silently"})
    # named gaps inside groups, surfaced for the reviewer
    for j, d in docs.items():
        for g in d.get("sufficiency_groups", []):
            if g["gap"].strip().lower() != "none":
                relations.append({"relation": "named-gap", "job": j, "group": g["id"], "gap": g["gap"]})
    out = {"schema_version": "l2-weave/v1", "jobs": list(docs), "relations": relations,
           "summary": {r: sum(1 for x in relations if x["relation"] == r) for r in ("overlap", "contradiction", "dependency", "gap", "named-gap")}}
    WEAVE.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def select(job: str, review: dict) -> dict:
    """Record a sketch review and derive the selected step set. Developers never write selected; this does, outside their file."""
    doc = json.loads((L2_DIR / job / "semantic-model.json").read_text())
    steps = element_steps(doc)
    rejected = set(review.get("rejected_element_ids", []))
    unknown = sorted(rejected - set(steps))
    if unknown:
        raise L2Error(f"review rejects unknown elements {unknown}")
    if review.get("verdict") not in ("pass", "fail", "needs-authority"):
        raise L2Error("review verdict must be pass, fail, or needs-authority")
    selected = sorted(e for e, st in steps.items() if st.get("disposition") == "candidate" and e not in rejected) if review["verdict"] == "pass" else []
    record = {"schema_version": "l2-review/v1", "job": job, "verdict": review["verdict"], "reviewer": review.get("reviewer", "unknown"), "model_sha256": sha((L2_DIR / job / "semantic-model.json").read_text()),
              "notes": review.get("notes", ""), "rejected_element_ids": sorted(rejected), "selected_element_ids": selected,
              "groups_selected": sorted(g["id"] for g in doc.get("sufficiency_groups", []) if all(m in selected for m in g["members"]))}
    (L2_DIR / job / "review.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    if review["verdict"] == "pass":
        # the selected snapshot is what L3 compiles from; later working-file edits do not move it until the next selection
        (L2_DIR / job / "selected-model.json").write_text((L2_DIR / job / "semantic-model.json").read_text())
    return record


HOLE_REF = re.compile(r"L1\.hole\.[a-z0-9-]+")


def holes_named(gap: str) -> set[str]:
    """The L1 holes a group's gap text names. 'none' names nothing."""
    return set(HOLE_REF.findall(gap or ""))


def fingerprints(job: str, l1: dict | None = None, selected: bool = False) -> dict:
    """Per-group fingerprints: hash of the clause fingerprints each group derives from, plus members and the contract version.
    With selected=True, fingerprint the selected snapshot (what L3 compiled from) rather than the working file."""
    l1 = l1 or parse_l1()
    path = L2_DIR / job / ("selected-model.json" if selected and (L2_DIR / job / "selected-model.json").exists() else "semantic-model.json")
    doc = json.loads(path.read_text())
    steps = element_steps(doc)
    out = {}
    for g in doc.get("sufficiency_groups", []):
        clauses = sorted((c, l1["clause_fingerprints"][c]) for c in g["parent_clauses"] if c in l1["clause_fingerprints"])
        # a hole named in the gap bounds this group's claim, so answering or amending it is as material as a clause change
        holes = sorted((h, l1["hole_fingerprints"][h]) for h in holes_named(g["gap"]) if h in l1["hole_fingerprints"])
        material = {"contract": L2_CONTRACT_VERSION, "job": job, "group": g["id"], "clauses": clauses, "holes": holes, "members": sorted(g["members"])}
        out[g["id"]] = {"fingerprint": sha(json.dumps(material, sort_keys=True)), "derived_from": sorted(g["parent_clauses"]), "members": sorted(g["members"]),
                        "bounded_by": sorted(h for h in holes_named(g["gap"]) if h in l1["hole_fingerprints"]),
                        "coverage_claim": g["coverage_claim"], "gap": g["gap"],
                        "justifications": {m: {"necessity": steps[m].get("necessity"), "parallel_assumption": steps[m].get("parallel_assumption")} for m in g["members"] if m in steps}}
    return out


def adjudication_for(group_id: str, clauses: list[str]) -> str | None:
    """Latest recorded adjudication for a group under one of the changed clauses: 'invalidate', 'keep', or None."""
    path = ROOT / "chain/cache-adjudications.jsonl"
    if not path.exists():
        return None
    verdict = None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("clause") not in clauses:
            continue
        note = entry.get("groups", {}).get(group_id)
        text = json.dumps(note).lower() if note is not None else ""
        if "invalidate" in text or "stale" in text:
            verdict = "invalidate"
        elif "keep" in text or "unchanged" in text:
            verdict = "keep"
    return verdict


def stamped_everywhere(job: str, group_id: str, fingerprint: str) -> bool:
    """True when every engine target's projection of the job attests this group: either its accepted manifest carries the
    fingerprint, or the projection derives nothing from the group (a group whose only member is a judgement invariant
    reaches no artifact and no audit, so no projection can attest it and its staleness has no L3 consequence)."""
    targets = [d for d in (ROOT / "chain/l3").iterdir() if d.is_dir()]
    manifests = [t / job / "manifest.json" for t in targets if (t / job / "manifest.json").exists()]
    if not manifests:
        return False
    doc = json.loads((L2_DIR / job / "selected-model.json").read_text()) if (L2_DIR / job / "selected-model.json").exists() else None
    members = set(next((g["members"] for g in doc.get("sufficiency_groups", []) if g["id"] == group_id), [])) if doc else set()
    for path in manifests:
        manifest = json.loads(path.read_text())
        if manifest.get("group_fingerprints", {}).get(group_id) == fingerprint:
            continue
        cited = {d for a in manifest.get("artifacts", []) for d in a.get("derived_from", [])} | {a["invariant"] for a in manifest.get("audits", [])}
        if members & cited:
            return False  # this projection does derive from the group and has not stamped the current fingerprint
    return True


def plan(previous: dict | None = None, use_jev: bool = True) -> dict:
    """Recompute fingerprints and report the stale set. Hash-unchanged never re-projects. Hash-changed asks Jev."""
    l1 = parse_l1()
    previous = previous if previous is not None else (json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {})
    prev_clauses = previous.get("l1", {}).get("clause_fingerprints", {})
    prev_texts = previous.get("l1", {}).get("clauses", {})
    changed_clauses = {c for c, f in l1["clause_fingerprints"].items() if prev_clauses.get(c) != f}
    prev_holes = previous.get("l1", {}).get("hole_fingerprints", {})
    prev_hole_texts = previous.get("l1", {}).get("holes", {})
    # a hole the business answered is gone from L1; a hole reworded has a new fingerprint. Both are policy moves.
    changed_holes = {h for h, f in l1["hole_fingerprints"].items() if prev_holes.get(h) != f} | {h for h in prev_holes if h not in l1["hole_fingerprints"]}
    prev_texts = {**prev_hole_texts, **prev_texts}
    JEV = _mod("jev_select", "scripts/jev_select.py") if use_jev else None
    report = {"l1": {"clauses": l1["clauses"], "clause_fingerprints": l1["clause_fingerprints"], "holes": l1["holes"], "hole_fingerprints": l1["hole_fingerprints"], "jobs": l1["jobs"]},
              "changed_clauses": sorted(changed_clauses), "changed_holes": sorted(changed_holes),
              "answered_holes": sorted(h for h in prev_holes if h not in l1["hole_fingerprints"]), "jobs": {}}
    for job in JOB_ORDER:
        if not (L2_DIR / job / "semantic-model.json").exists():
            report["jobs"][job] = {"status": "no-l2"}
            continue
        current = fingerprints(job, l1)
        prev = previous.get("jobs", {}).get(job, {}).get("elements", {})
        review_path = L2_DIR / job / "review.json"
        selected_sha = json.loads(review_path.read_text()).get("model_sha256") if review_path.exists() else None
        prev_selected_sha = previous.get("jobs", {}).get(job, {}).get("selected_model_sha256")
        elements = {}
        for eid, info in current.items():
            before = prev.get(eid, {}).get("fingerprint")
            if before == info["fingerprint"]:
                # an unchanged fingerprint is a hit, except that a pending decision persists: "review" until adjudicated,
                # "stale" until the job has been re-selected since it was recorded
                prior = prev.get(eid, {}).get("cache")
                touched_before = prev.get(eid, {}).get("touched_clauses") or []
                if prior == "review":
                    adjudicated = adjudication_for(eid, touched_before)
                    decision = "stale" if adjudicated == "invalidate" else ("hit-by-adjudication" if adjudicated == "keep" else "review")
                    elements[eid] = {**info, "cache": decision, "touched_clauses": touched_before, "jev": prev.get(eid, {}).get("jev")}
                    continue
                if prior in ("stale", "stale-new") and selected_sha == prev_selected_sha and not stamped_everywhere(job, eid, info["fingerprint"]):
                    # stale persists until the job is re-selected or every engine target has stamped this fingerprint
                    elements[eid] = {**info, "cache": prior, "touched_clauses": touched_before, "jev": prev.get(eid, {}).get("jev")}
                    continue
                elements[eid] = {**info, "cache": "hit"}
                continue
            touched = [c for c in info["derived_from"] if c in changed_clauses] + [h for h in info.get("bounded_by", []) if h in changed_holes]
            touched += [h for h in changed_holes if h not in l1["hole_fingerprints"] and h in (info.get("gap") or "")]  # a hole answered out of existence
            decision, jev = ("stale-new", None) if before is None else ("stale", None)
            if before is not None and touched and JEV is not None:
                verdicts = [JEV.invalidation(c, prev_texts.get(c, ""), l1["clauses"].get(c) or l1["holes"].get(c) or "(answered and removed)", {"id": eid, "kind": "sufficiency_group", "statement": info.get("coverage_claim"), "note": json.dumps(info.get("justifications"), sort_keys=True)[:3000]}) for c in touched]
                decisions = {v.get("decision") for v in verdicts}
                decision = "review" if "review" in decisions else ("stale" if "invalidate" in decisions else "hit-by-jev")
                if decision == "review":
                    # a reviewer's recorded adjudication (chain/cache-adjudications.jsonl) settles what Jev could not
                    adjudicated = adjudication_for(eid, touched)
                    if adjudicated == "invalidate":
                        decision = "stale"
                    elif adjudicated == "keep":
                        decision = "hit-by-adjudication"
                jev = [{k: v.get(k) for k in ("verdict", "p_behavior_changes", "confidence_band", "decision")} for v in verdicts]
            elements[eid] = {**info, "cache": decision, "touched_clauses": touched, "jev": jev}
        stale = sorted(e for e, i in elements.items() if i["cache"] in ("stale", "stale-new"))
        report["jobs"][job] = {"status": "ok", "elements": elements, "stale": stale, "l3_reprojection_required": bool(stale), "selected_model_sha256": selected_sha}
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("l1", "check", "fingerprints", "plan", "commit", "weave", "select"))
    p.add_argument("--review", type=Path, help="JSON file with verdict, reviewer, notes, rejected_element_ids")
    p.add_argument("job", nargs="?")
    p.add_argument("--no-jev", action="store_true")
    a = p.parse_args()
    try:
        if a.command == "l1":
            l1 = parse_l1(); print(json.dumps({"clauses": list(l1["clauses"]), "holes": list(l1["holes"]), "jobs": l1["jobs"]}, indent=2))
        elif a.command == "check":
            jobs = [a.job] if a.job else JOB_ORDER
            reports = [check(j) for j in jobs]; print(json.dumps(reports, indent=2)); return 0 if all(r["status"] == "ok" for r in reports) else 3
        elif a.command == "select":
            print(json.dumps(select(a.job, json.loads(a.review.read_text())), indent=2))
        elif a.command == "weave":
            print(json.dumps(weave(), indent=2))
        elif a.command == "fingerprints":
            print(json.dumps(fingerprints(a.job), indent=2))
        elif a.command == "plan":
            print(json.dumps(plan(use_jev=not a.no_jev), indent=2, default=str))
        elif a.command == "commit":
            report = plan(use_jev=not a.no_jev)
            MANIFEST.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"); print(f"manifest written: {MANIFEST.relative_to(ROOT)}")
    except (L2Error, OSError, json.JSONDecodeError) as error:
        print(f"l2 error: {error}", file=sys.stderr); return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
