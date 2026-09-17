#!/usr/bin/env python3
"""L2 -> L3 gate and runner. P2 = chain/l3/<target>/<job>/ (Developer-written SQL + manifest). G3 = check + run.

check: layout, manifest schema, provenance (derived_from ids exist and are selected), read containment
(only handoff sources and upstream entities), write-surface guard (frozen and per_statement columns
never updated in place). run: load the fixture into DuckDB, execute upstream jobs' projections, then
this job's, then its audits; every audit must return zero rows.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import duckdb
from jsonschema import Draft202012Validator
from sqlglot import exp, parse

ROOT = Path(__file__).resolve().parents[1]
L2_DIR = ROOT / "chain/l2"
L3_DIR = ROOT / "chain/l3"
JOB_ORDER = ["ownership-history", "trade-lifecycle", "positions"]


def _mod(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


GUARD = _mod("merge_guard", "scripts/merge_guard.py")
LOADER = _mod("chain_load", "scripts/chain_load.py")
L2 = _mod("chain_l2", "scripts/chain_l2.py")


class L3Error(ValueError):
    pass


def load_job(job: str) -> tuple[dict, dict]:
    snapshot = L2_DIR / job / "selected-model.json"
    model_path = snapshot if snapshot.exists() else L2_DIR / job / "semantic-model.json"
    if not model_path.exists():
        raise L3Error(f"{job} has no L2 model; L3 compiles only from a selected L2")
    model = json.loads(model_path.read_text())  # L3 compiles from the selected snapshot, not from a model mid-cycle
    review_path = L2_DIR / job / "review.json"
    if not review_path.exists():
        raise L3Error(f"{job} has no review; L3 compiles only from a selected L2")
    review = json.loads(review_path.read_text())
    if review["verdict"] != "pass":
        raise L3Error(f"{job} review verdict is {review['verdict']}; L3 compiles only from a passed L2")
    return model, review


def containment(model: dict, selected: set[str]) -> dict[str, set[str]]:
    """Per entity: the schema-qualified tables its SQL may read, from handoffs (sources and upstream entities)."""
    allowed = {e["id"]: set() for e in model["entities"]}
    for h in model["handoffs"]:
        hid = f"handoff.{h['from']}->{h['to']}"
        if hid not in selected or h.get("disposition") != "candidate":
            continue
        entity = h["to"].rsplit(".", 1)[0]
        src = h["from"].rsplit(".", 1)[0]
        if src.startswith(("raw.", "ce.")):
            allowed[entity].add(src)
        else:
            allowed[entity].add("governed." + src.split(".")[-1])
    return allowed


def is_sqlmesh(profile: dict) -> bool:
    return str(profile.get("orchestrator", "")).startswith("sqlmesh")


def materialization_problems(sql: str, roles: dict[str, str]) -> list[str]:
    """On SQLMesh targets a governed_merge model declares its write surface in MODEL header properties.
    unique_key must be the entity's identity columns; mutable_columns may name only mutable attributes;
    frozen_columns may name only frozen_from_first_encounter attributes. Mirrors the native MERGE guard."""
    text = sql.lstrip()
    if not text.startswith("MODEL"):
        return []
    header = text[: text.find(");") + 2] if ");" in text else text
    if "governed_merge" not in header:
        return []
    props = {k: {c.strip() for c in v.split(",") if c.strip()} for k, v in re.findall(r"'(unique_key|mutable_columns|frozen_columns)'\s*=\s*'([^']*)'", header)}
    by_role = {}
    for col, role in roles.items():
        by_role.setdefault(role, set()).add(col)
    out = []
    if props.get("unique_key", set()) != by_role.get("identity", set()):
        out.append(f"declares unique_key {sorted(props.get('unique_key', set()))} but the entity's identity columns are {sorted(by_role.get('identity', set()))}")
    stray_mutable = sorted(props.get("mutable_columns", set()) - by_role.get("mutable", set()))
    if stray_mutable:
        out.append(f"declares mutable_columns {stray_mutable} whose L2 mutation role is not mutable")
    stray_frozen = sorted(props.get("frozen_columns", set()) - by_role.get("frozen_from_first_encounter", set()))
    if stray_frozen:
        out.append(f"declares frozen_columns {stray_frozen} whose L2 mutation role is not frozen_from_first_encounter")
    return out


def body_of(sql: str, sqlmesh_target: bool) -> str:
    """For SQLMesh targets, strip the MODEL (...) or AUDIT (...) header and resolve @this_model for parsing."""
    if not sqlmesh_target:
        return sql
    text = sql.lstrip()
    if text.startswith(("MODEL", "AUDIT")):
        idx = text.find(");")
        text = text[idx + 2:] if idx >= 0 else text
    return text.replace("@this_model", "this_model_placeholder")


def groups_of(model: dict, element_ids: list[str]) -> set[str]:
    steps = L2.element_steps(model)
    return {steps[e]["sufficiency_group"] for e in element_ids if e in steps and steps[e].get("sufficiency_group")}


def projection_digest(base: Path) -> str:
    """What the reviewer judged: every SQL file of the projection, by content, so a touched-but-identical file is the same
    projection and an edited one is not."""
    files = sorted(list(base.glob("*.sql")) + list(base.glob("models/*.sql")) + list(base.glob("audits/*.sql")))
    material = json.dumps([[f.relative_to(base).as_posix(), hashlib.sha256(f.read_bytes()).hexdigest()] for f in files], sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()


def acceptance(target: str, job: str) -> dict:
    """Whether this projection is the one a review accepted: a passed review whose recorded content digest is the content
    on disk now. Well-formed and accepted are different questions, and the gate answers both, because a projection
    mid-cycle is not wrong, it is simply not yet the accepted one."""
    base = L3_DIR / target / job
    path = base / "review.json"
    if not path.exists():
        return {"reviewed": False, "accepted": False, "reason": "no projection review"}
    record = json.loads(path.read_text())
    verdict = record.get("verdict")
    if verdict != "pass":
        return {"reviewed": True, "accepted": False, "verdict": verdict, "reason": f"review verdict is {verdict}"}
    stamped = record.get("projection_sha256")
    if not stamped:
        return {"reviewed": True, "accepted": False, "verdict": verdict, "reason": "the review records no accepted content"}
    if stamped != projection_digest(base):
        return {"reviewed": True, "accepted": False, "verdict": verdict, "reason": "the projection changed after the review that accepted it"}
    return {"reviewed": True, "accepted": True, "verdict": verdict}


def stamp(target: str, job: str) -> dict:
    """After a passed projection review: record the fingerprints of the L2 groups this projection derives from.
    Stamping is the acceptance step, so it is the reviewer's, not the Developer's: it refuses when the projection has
    changed since the review that judged it, which is exactly the case where a Developer would be accepting its own work."""
    model, review = load_job(job)
    base = L3_DIR / target / job
    projection_review = base / "review.json"
    if not projection_review.exists():
        raise L3Error(f"{target}/{job} has no projection review; stamping is acceptance and needs one")
    verdict = json.loads(projection_review.read_text()).get("verdict")
    if verdict != "pass":
        raise L3Error(f"{target}/{job} review verdict is {verdict}; only a passed projection is stamped")
    record = json.loads(projection_review.read_text())
    digest = projection_digest(base)
    if record.get("projection_sha256") and record["projection_sha256"] != digest:
        raise L3Error(f"{target}/{job} changed after the review that judged it; review the change, then stamp")
    manifest = json.loads((base / "manifest.json").read_text())
    # a projection derives from the groups its artifacts cite and from the groups whose invariants its audits check;
    # a group with only an invariant member (like sg.unknown-codes) reaches L3 through an audit alone
    derived = groups_of(model, [d for a in manifest["artifacts"] for d in a["derived_from"]] + [a["invariant"] for a in manifest.get("audits", [])])
    current = {gid: info["fingerprint"] for gid, info in L2.fingerprints(job, selected=True).items() if gid in derived}
    manifest["group_fingerprints"] = current
    manifest["derived_from_model"]["review_sha256"] = review["model_sha256"]
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    record["projection_sha256"] = digest  # what this acceptance covers; a later edit no longer passes as reviewed
    projection_review.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return {"target": target, "job": job, "groups": sorted(current)}


def column_roles(model: dict, entity_id: str) -> dict[str, str]:
    types = {t["id"]: t["mutation_role"] for t in model["types"]}
    entity = next(e for e in model["entities"] if e["id"] == entity_id)
    return {a["name"]: types[a["semantic_type"]] for a in entity["attributes"]}


def check(target: str, job: str) -> dict:
    model, review = load_job(job)
    selected = set(review["selected_element_ids"])
    steps = L2.element_steps(model)
    base = L3_DIR / target / job
    problems, questions = [], []
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        return {"target": target, "job": job, "status": "missing"}
    manifest = json.loads(manifest_path.read_text())
    schema = json.loads((ROOT / "chain/anchors/l3-manifest-v1.schema.json").read_text())
    for e in sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda e: list(e.path)):
        problems.append(f"manifest: {e.message} at {'/'.join(map(str, e.path))}")
    questions = list(manifest.get("questions_for_authority") or [])
    # Provenance is two independent questions, and the gate must ask both every time. Does this projection compile from
    # the L2 text that is selected now (the review sha)? And do the groups it derives from still fingerprint the way they
    # did when it was stamped? An L1 clause or hole can move under an unchanged L2, so a matching sha proves nothing
    # about staleness; asking only on a sha mismatch once reported a stale projection as accepted.
    provenance_note = None
    stamped = manifest.get("group_fingerprints") or {}
    current = {gid: info["fingerprint"] for gid, info in L2.fingerprints(job, selected=True).items()}
    derived_groups = groups_of(model, [d for a in manifest.get("artifacts", []) for d in a["derived_from"]] + [a["invariant"] for a in manifest.get("audits", [])])
    chain_manifest = json.loads((ROOT / "chain/manifest.json").read_text()) if (ROOT / "chain/manifest.json").exists() else {}
    cache = {gid: info.get("cache") for gid, info in chain_manifest.get("jobs", {}).get(job, {}).get("elements", {}).items()}
    sha_matches = manifest.get("derived_from_model", {}).get("review_sha256") == review["model_sha256"]
    moved = sorted(gid for gid in derived_groups if stamped.get(gid) != current.get(gid))
    # a moved fingerprint is still valid when the chain manifest records Jev's keep or an adjudicated keep for that group
    kept = sorted(gid for gid in moved if cache.get(gid) in ("hit-by-jev", "hit-by-adjudication"))
    awaiting = sorted(gid for gid in moved if cache.get(gid) == "review")
    unresolved = [gid for gid in moved if gid not in kept and gid not in awaiting]
    if awaiting:
        problems.append(f"groups {awaiting} moved under an L1 change that Jev routed to review; adjudicate (keep or invalidate) before this projection can be accepted or re-projected")
    if unresolved:
        problems.append(f"groups {unresolved} moved since this projection was stamped; re-project the stale artifacts")
    elif not stamped and not sha_matches:
        problems.append("manifest review_sha256 does not match the selected L2 model and no group fingerprints are stamped; re-project")
    elif kept:
        provenance_note = f"groups {kept} moved only under a change judged behavior-neutral (kept); projection remains valid"
    elif not sha_matches:
        provenance_note = "review sha superseded by an L2 change that left every derived group's fingerprint unchanged; projection remains valid"
    if manifest.get("target") != target or manifest.get("job") != job:
        problems.append("manifest target/job do not match the directory")
    profile = json.loads((ROOT / "chain/profiles" / f"{target}.json").read_text())
    sqlmesh_target = is_sqlmesh(profile)
    allowed_reads = containment(model, selected)
    entities_selected = {e["id"] for e in model["entities"] if e["id"] in selected}
    projected = {a["entity"] for a in manifest.get("artifacts", [])}
    for missing in sorted(entities_selected - projected):
        if not questions:
            problems.append(f"selected entity {missing} has no artifact and no question filed")
    listed_files = {a["file"] for a in manifest.get("artifacts", [])} | {a["file"] for a in manifest.get("audits", [])} | {"manifest.json"}
    governance = re.compile(r"^(change-contract-\d+\.md|review(-\d+)?\.(md|json)|adjudication-.*\.md|mutation-findings-\d+\.md)$")
    actual = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file() and not governance.match(p.relative_to(base).as_posix())}
    for extra in sorted(actual - listed_files):
        problems.append(f"file {extra} is not listed in the manifest")
    for art in manifest.get("artifacts", []):
        path = base / art["file"]
        if not path.exists():
            problems.append(f"artifact {art['file']} missing"); continue
        if art["entity"] not in entities_selected:
            problems.append(f"artifact {art['file']} projects {art['entity']}, which is not a selected entity")
        for did in art["derived_from"]:
            if did not in steps:
                problems.append(f"artifact {art['file']} derives from unknown element {did}")
            elif did not in selected:
                problems.append(f"artifact {art['file']} derives from {did}, which is not selected (deferred or rejected)")
        sql = path.read_text()
        if sqlmesh_target and not sql.lstrip().startswith("MODEL"):
            problems.append(f"artifact {art['file']} must be a SQLMesh MODEL file on target {target}")
        if sqlmesh_target and f"name governed.{art['entity'].split('.')[-1]}" not in sql:
            problems.append(f"artifact {art['file']} MODEL name must be governed.{art['entity'].split('.')[-1]}")
        try:
            statements = [s for s in parse(body_of(sql, sqlmesh_target), dialect="duckdb") if s is not None]
        except Exception as error:  # noqa: BLE001
            problems.append(f"artifact {art['file']} does not parse: {error}"); continue
        target_table = "governed." + art["entity"].split(".")[-1]
        allowed = allowed_reads.get(art["entity"], set()) | {target_table, "this_model_placeholder"}
        roles = column_roles(model, art["entity"])
        for s in statements:
            ctes = {c.alias_or_name.lower() for c in s.find_all(exp.CTE)}
            reads = {(f"{t.db}.{t.name}" if t.db else t.name).lower() for t in s.find_all(exp.Table) if t.name.lower() not in ctes}
            illegal = sorted(r for r in reads if r not in {a.lower() for a in allowed})
            if illegal:
                problems.append(f"artifact {art['file']} reads {illegal}, outside its handoffs {sorted(allowed)}")
            verdict = GUARD.guard_statement(s, roles, art["entity"].split(".")[-1])
            if not verdict.ok:
                problems.append(f"artifact {art['file']} writes protected columns: {json.dumps(verdict.attempted_writes)}")
        if sqlmesh_target:
            # the write surface of a governed_merge model lives in its header, which the SQL guard never sees
            problems.extend(f"artifact {art['file']} {p}" for p in materialization_problems(sql, roles))
        # tempting wrong resolution: joining an upstream versioned entity on is_current when the model's selector is as-of
        as_of_sources = {h["from"].rsplit(".", 1)[0] for h in model["handoffs"] if h.get("selector") == "as_of_event_time" and h["from"].startswith("logical.")}
        for s in statements:
            for col in s.find_all(exp.Column):
                if col.name.lower() == "is_current" and as_of_sources:
                    problems.append(f"artifact {art['file']} references is_current; the model resolves {sorted(as_of_sources)} as of an event time, not as of now")
                    break
        declared = {r.lower() for r in art.get("reads", [])}
        observed = set()
        for s in statements:
            ctes = {c.alias_or_name.lower() for c in s.find_all(exp.CTE)}
            observed |= {(f"{t.db}.{t.name}" if t.db else t.name).lower() for t in s.find_all(exp.Table) if t.name.lower() not in ctes} - {target_table.lower(), "this_model_placeholder"}
        if declared != observed:
            problems.append(f"artifact {art['file']} declares reads {sorted(declared)} but the SQL reads {sorted(observed)}")
    invariants = {inv["id"]: inv for inv in model["invariants"] if inv["id"] in selected and inv["deterministic"]}
    audited = {a["invariant"] for a in manifest.get("audits", [])}
    for inv in sorted(set(invariants) - audited):
        problems.append(f"deterministic invariant {inv} has no audit")
    upstream_tables = {"governed." + e["id"].split(".")[-1] for j in JOB_ORDER[: JOB_ORDER.index(job)] if (L2_DIR / j / "semantic-model.json").exists() for e in json.loads((L2_DIR / j / "semantic-model.json").read_text())["entities"]}
    own_tables = {"governed." + e["id"].split(".")[-1] for e in model["entities"]}
    for a in manifest.get("audits", []):
        if a["invariant"] not in invariants:
            problems.append(f"audit {a['file']} names {a['invariant']}, not a selected deterministic invariant")
        if not (base / a["file"]).exists():
            problems.append(f"audit {a['file']} missing")
        else:
            # audits read only the entity itself (@this_model), the job's other entities, upstream entities, and the entity's declared sources
            try:
                audit_statements = [s for s in parse(body_of((base / a["file"]).read_text(), sqlmesh_target), dialect="duckdb") if s is not None]
            except Exception as error:  # noqa: BLE001
                problems.append(f"audit {a['file']} does not parse: {error}"); audit_statements = []
            allowed_audit = own_tables | upstream_tables | allowed_reads.get(a["entity"], set()) | {"this_model_placeholder"}
            for s in audit_statements:
                ctes = {c.alias_or_name.lower() for c in s.find_all(exp.CTE)}
                reads = {(f"{t.db}.{t.name}" if t.db else t.name).lower() for t in s.find_all(exp.Table) if t.name.lower() not in ctes}
                illegal = sorted(r for r in reads if r not in {x.lower() for x in allowed_audit})
                if illegal:
                    problems.append(f"audit {a['file']} reads {illegal}, outside its entity's sources and governed entities")
            if sqlmesh_target and not (base / a["file"]).read_text().lstrip().startswith("AUDIT"):
                problems.append(f"audit {a['file']} must be a SQLMesh AUDIT file on target {target}")
    status = "rejected" if problems else ("question" if questions else "ok")
    return {"target": target, "job": job, "status": status, "problems": problems, "questions": questions, "profile": profile["target"], "provenance": provenance_note,
            "acceptance": acceptance(target, job),
            "artifacts": len(manifest.get("artifacts", [])), "audits": len(manifest.get("audits", []))}


def execute(con, base: Path, manifest: dict) -> None:
    for art in manifest["artifacts"]:
        con.execute((base / art["file"]).read_text())


def run_sqlmesh(target: str, job: str, database: Path, fixture_report: dict) -> dict:
    """Assemble one SQLMesh project from this job's and its upstream jobs' model files, plan it, audit it."""
    import shutil
    import subprocess
    project = ROOT / f"build/chain-{target}-{job}"
    if project.exists():
        shutil.rmtree(project)
    (project / "models").mkdir(parents=True)
    (project / "audits").mkdir()
    (project / "materializations").mkdir()
    HARNESS = _mod("chain_harness", "scripts/chain_harness.py")
    (project / "materializations/governed_merge.py").write_text(HARNESS.MATERIALIZATION)
    (project / "config.yaml").write_text(
        "gateways:\n  duckdb:\n    connection:\n      type: duckdb\n" f"      database: '{database.as_posix()}'\n"
        "default_gateway: duckdb\nmodel_defaults:\n  dialect: duckdb\n  start: '2012-01-01'\n  cron: '@daily'\nlinter:\n  enabled: false\n")
    jobs = JOB_ORDER[: JOB_ORDER.index(job) + 1]
    for j in jobs:
        base = L3_DIR / target / j
        manifest_path = base / "manifest.json"
        if not manifest_path.exists():
            raise L3Error(f"job {j} has no {target} projection")
        manifest = json.loads(manifest_path.read_text())
        for art in manifest["artifacts"]:
            shutil.copy(base / art["file"], project / "models" / Path(art["file"]).name)
        for a in manifest["audits"]:
            shutil.copy(base / a["file"], project / "audits" / Path(a["file"]).name)
    result = subprocess.run([str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), "plan", "prod", "--auto-apply", "--no-prompts", "--skip-tests", "--skip-linter"], cwd=ROOT, text=True, capture_output=True)
    manifest = json.loads((L3_DIR / target / job / "manifest.json").read_text())
    # SQLMesh audits block promotion: a failing audit aborts the plan. That is a projection result, not a harness error,
    # so read the failures off the plan output and report them the way a native run reports violating rows.
    blocking = {name: int(n) for name, n in re.findall(r"'([^']+)' audit error: (\d+) rows? failed", result.stdout)}
    if blocking:
        for a in manifest["audits"]:
            fixture_report["audits"][a["invariant"]] = {"violations": blocking.get(a["invariant"], 0), "via": "sqlmesh plan (blocking audit)", "sample": []}
        fixture_report["sqlmesh"] = {"plan_tail": result.stdout[-800:], "audit_ok": False, "blocking_failures": blocking}
        fixture_report["ok"] = False
        return fixture_report
    if result.returncode or "Failed models" in result.stdout:
        raise L3Error(f"SQLMesh plan failed:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}")
    audit = subprocess.run([str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), "audit"], cwd=ROOT, text=True, capture_output=True)
    fixture_report["sqlmesh"] = {"plan_tail": result.stdout[-800:], "audit_ok": audit.returncode == 0 and "0 audit errors" in audit.stdout, "audit_tail": (audit.stdout + audit.stderr)[-1500:]}
    con = duckdb.connect(str(database), read_only=True)
    try:
        for a in manifest["audits"]:
            fixture_report["audits"][a["invariant"]] = {"violations": 0 if fixture_report["sqlmesh"]["audit_ok"] else None, "via": "sqlmesh audit"}
        for art in manifest["artifacts"]:
            table = "governed." + art["entity"].split(".")[-1]
            cur = con.execute(f"SELECT * FROM {table} ORDER BY 1, 2 LIMIT 12")
            fixture_report["samples"][table] = {"columns": [d[0] for d in cur.description], "rows": [list(map(str, r)) for r in cur.fetchall()], "count": con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]}
    finally:
        con.close()
    fixture_report["ok"] = fixture_report["sqlmesh"]["audit_ok"]
    return fixture_report


WATCH = {"ownership-history": "SELECT account_number, effective_from, is_current, provenance FROM governed.account WHERE account_number = 428 ORDER BY effective_from",
         "trade-lifecycle": "SELECT * FROM governed.trade WHERE trade_number = 372101",
         "positions": "SELECT * FROM governed.holding_change ORDER BY 1, 2"}


def run_two_phase(target: str, job: str, database: Path | None = None, watch: str | None = None) -> dict:
    """The counterexample as a simulation: project the first-encounter batch, then load the later batch and the labeled
    constructed change without dropping governed tables, project again, and report what changed on the watched row."""
    fixture = json.loads((ROOT / "oracle/fixtures/public/chain-fixture-v1.json").read_text())
    ce = json.loads((ROOT / "counterexamples/archive/ce-account-428-rollover-v1.json").read_text())
    changes = [{k: v for k, v in row.items() if k != "note"} for row in ce["fixture"]["ce_account_changes"]]
    database = database or ROOT / f"build/chain-{target}-twophase.duckdb"
    watch = watch or WATCH.get(job, WATCH["trade-lifecycle"])  # the watched row belongs to the job being simulated
    profile = json.loads((ROOT / "chain/profiles" / f"{target}.json").read_text())
    if database.exists():
        database.unlink()  # a two-phase simulation starts from nothing; leftovers from another job would mask a missing upstream
    first = run(target, job, "first_encounter", database=database)
    if not first["ok"]:
        raise L3Error("first-encounter phase failed its audits")
    con = duckdb.connect(str(database), read_only=True)
    try:
        cur = con.execute(watch); cols = [d[0] for d in cur.description]; before = [dict(zip(cols, map(str, r))) for r in cur.fetchall()]
    finally:
        con.close()
    LOADER.reload_sources(database, fixture, "rollover", changes)
    report = {"target": target, "job": job, "phase": "two-phase", "upstream": [], "audits": {}, "samples": {}}
    if is_sqlmesh(profile):
        second = run_sqlmesh_replan(target, job, database, report)
    else:
        con = duckdb.connect(str(database))
        try:
            for up in JOB_ORDER[: JOB_ORDER.index(job)]:
                execute(con, L3_DIR / target / up, json.loads((L3_DIR / target / up / "manifest.json").read_text()))
            base = L3_DIR / target / job
            manifest = json.loads((base / "manifest.json").read_text())
            execute(con, base, manifest)
            for a in manifest["audits"]:
                rows = con.execute((base / a["file"]).read_text()).fetchall()
                report["audits"][a["invariant"]] = {"violations": len(rows)}
        finally:
            con.close()
        report["ok"] = all(v["violations"] == 0 for v in report["audits"].values())
        second = report
    con = duckdb.connect(str(database), read_only=True)
    try:
        cur = con.execute(watch); cols = [d[0] for d in cur.description]; after = [dict(zip(cols, map(str, r))) for r in cur.fetchall()]
        versions = [list(map(str, r)) for r in con.execute("SELECT account_number, effective_from, is_current, provenance FROM governed.account WHERE account_number = 428 ORDER BY effective_from").fetchall()]
    finally:
        con.close()
    changed = sorted(k for k in (after[0] if after else {}) if before and after and before[0].get(k) != after[0].get(k))
    return {"target": target, "job": job, "first_phase_ok": first["ok"], "second_phase_ok": second["ok"], "watched_before": before, "watched_after": after, "changed_columns": changed, "account_428_statements_after": versions}


def run_sqlmesh_replan(target: str, job: str, database: Path, report: dict) -> dict:
    """Second phase on a SQLMesh target: restate the stage-free FULL upstream and re-run the custom-materialized model against the reloaded sources."""
    import subprocess
    project = ROOT / f"build/chain-{target}-{job}"
    import shutil
    shutil.rmtree(project / ".cache", ignore_errors=True)
    restate = []
    for j in JOB_ORDER[: JOB_ORDER.index(job) + 1]:
        manifest = json.loads((L3_DIR / target / j / "manifest.json").read_text())
        for art in manifest["artifacts"]:
            restate += ["--restate-model", "governed." + art["entity"].split(".")[-1]]
    result = subprocess.run([str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), "plan", "prod", "--auto-apply", "--no-prompts", "--skip-tests", "--skip-linter", *restate], cwd=ROOT, text=True, capture_output=True)
    if result.returncode or "Failed models" in result.stdout:
        raise L3Error(f"SQLMesh second-phase plan failed:\n{result.stdout[-3000:]}\n{result.stderr[-1500:]}")
    audit = subprocess.run([str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), "audit"], cwd=ROOT, text=True, capture_output=True)
    report["ok"] = audit.returncode == 0 and "0 audit errors" in audit.stdout
    report["sqlmesh"] = {"audit_tail": (audit.stdout + audit.stderr)[-800:]}
    return report


DEFAULT_CE = "counterexamples/archive/ce-account-428-rollover-v1.json"


def ce_rows(ce: dict) -> tuple[list[dict], dict[str, list[dict]]]:
    """A counterexample document's constructed rows: labeled ce.account_changes rows and any raw additions."""
    changes = [{k: v for k, v in row.items() if k != "note"} for row in ce["fixture"].get("ce_account_changes", [])]
    additions = {t: [{k: v for k, v in r.items() if k != "note"} for r in rows] for t, rows in ce["fixture"].get("raw_additions", {}).items()}
    # ce.account_changes rows carry their own provenance column (the loader checks it); raw tables do not, so raw
    # additions are admitted only from a document labeled controlled_counterexample at the top level
    if additions and ce.get("provenance") != "controlled_counterexample":
        raise L3Error("a counterexample document that adds raw rows must be labeled controlled_counterexample")
    return changes, additions


def run(target: str, job: str, phase: str = "rollover", database: Path | None = None, ce: dict | None = None) -> dict:
    """Load the fixture (and labeled CE rows for the rollover phase), run upstream jobs' projections, then this job, then audits.
    A job may be mid-cycle, but what it compiles on top of may not: an unaccepted upstream is refused before anything runs."""
    for up in JOB_ORDER[: JOB_ORDER.index(job)]:
        state = acceptance(target, up)
        if not state["accepted"]:
            raise L3Error(f"upstream job {up} on {target} is not accepted ({state['reason']}); a projection is not compiled on top of one no review has accepted")
    fixture = json.loads((ROOT / "oracle/fixtures/public/chain-fixture-v1.json").read_text())
    ce = ce if ce is not None else json.loads((ROOT / DEFAULT_CE).read_text())
    changes, additions = ce_rows(ce)
    database = database or ROOT / f"build/chain-{target}.duckdb"
    LOADER.load_fixture(database, fixture, phase, changes if phase == "rollover" else None, additions if phase == "rollover" else None)
    report = {"target": target, "job": job, "phase": phase, "upstream": [], "audits": {}, "samples": {}}
    profile = json.loads((ROOT / "chain/profiles" / f"{target}.json").read_text())
    if is_sqlmesh(profile):
        return run_sqlmesh(target, job, database, report)
    con = duckdb.connect(str(database))
    try:
        for up in JOB_ORDER[: JOB_ORDER.index(job)]:
            up_manifest = L3_DIR / target / up / "manifest.json"
            if not up_manifest.exists():
                raise L3Error(f"upstream job {up} has no {target} projection")
            execute(con, L3_DIR / target / up, json.loads(up_manifest.read_text()))
            report["upstream"].append(up)
        base = L3_DIR / target / job
        manifest = json.loads((base / "manifest.json").read_text())
        execute(con, base, manifest)
        for a in manifest["audits"]:
            rows = con.execute((base / a["file"]).read_text()).fetchall()
            report["audits"][a["invariant"]] = {"violations": len(rows), "sample": [list(map(str, r)) for r in rows[:3]]}
        for art in manifest["artifacts"]:
            table = "governed." + art["entity"].split(".")[-1]
            cur = con.execute(f"SELECT * FROM {table} ORDER BY 1, 2 LIMIT 12")
            report["samples"][table] = {"columns": [d[0] for d in cur.description], "rows": [list(map(str, r)) for r in cur.fetchall()], "count": con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]}
    finally:
        con.close()
    report["ok"] = all(v["violations"] == 0 for v in report["audits"].values())
    return report


def simulate(target: str, job: str, ce_path: Path) -> dict:
    """Run one counterexample document against a projection: fixture plus the CE's constructed rows, then report which
    audits fire and on what. A proposed CE runs the same way as an accepted one; acceptance changes the archive, not the harness."""
    ce = json.loads((ROOT / ce_path).read_text())
    database = ROOT / f"build/chain-{target}-sim-{Path(ce_path).stem}.duckdb"
    if database.exists():
        database.unlink()
    report = run(target, job, "rollover", database=database, ce=ce)
    fired = {inv: info for inv, info in report["audits"].items() if info["violations"]}
    return {"target": target, "job": job, "counterexample": ce.get("id", Path(ce_path).stem), "status": ce.get("status"), "ok": report["ok"],
            "fired": fired, "silent": not fired, "deterministic_assertion": ce.get("deterministic_assertion"), "samples": {t: s["count"] for t, s in report.get("samples", {}).items()},
            "note": "SQLMesh audits block promotion, so a fired audit here means the plan was refused and no table was written" if report.get("sqlmesh", {}).get("blocking_failures") else None}


def mutate(target: str, job: str, database: Path | None = None) -> dict:
    """Audit sensitivity on native targets: corrupt one protected value at a time on a scratch copy and require an audit to fire.
    Mutations: for every frozen_from_first_encounter or per_statement attribute, null one row's value and, where two
    distinct values exist, swap one row's value for another row's; for every attribute derived within the entity, swap and
    perturb (a different value of the same type); for every other non-nullable, non-identity attribute, null.
    Reports mutations no audit catches as unprotected."""
    import shutil
    profile = json.loads((ROOT / "chain/profiles" / f"{target}.json").read_text())
    sqlmesh_target = is_sqlmesh(profile)
    model, review = load_job(job)
    base = L3_DIR / target / job
    manifest = json.loads((base / "manifest.json").read_text())
    database = database or ROOT / f"build/chain-{target}-mutate.duckdb"
    run(target, job, "rollover", database=database)
    scratch_dir = database.parent / "mutate-scratch"
    scratch_dir.mkdir(exist_ok=True)
    scratch = scratch_dir / database.name  # same file stem: SQLMesh views embed the catalog name
    types = {t["id"]: t["mutation_role"] for t in model["types"]}
    audits = [(a["invariant"], body_of((base / a["file"]).read_text(), sqlmesh_target).replace("this_model_placeholder", "governed." + a["entity"].split(".")[-1])) for a in manifest["audits"]]

    def physical(con, view: str) -> str:
        """On SQLMesh targets governed.<entity> is a view over a versioned physical table; mutate that table."""
        if not sqlmesh_target:
            return view
        schema, name = view.split(".")
        row = con.execute("SELECT sql FROM duckdb_views() WHERE schema_name = ? AND view_name = ?", [schema, name]).fetchone()
        if not row:
            return view
        m = re.search(r'FROM\s+("[^"]+"\.|[\w-]+\.)?("?[\w]+"?)\.("?[\w]+"?)', row[0], re.IGNORECASE)
        if not m:
            return view
        return f"{m.group(2)}.{m.group(3)}".replace('"', "")

    results = []
    for entity in model["entities"]:
        table = "governed." + entity["id"].split(".")[-1]
        ids = entity["identifiers"]
        for attr in entity["attributes"]:
            role = types.get(attr["semantic_type"])
            if role in ("frozen_from_first_encounter", "per_statement"):
                kinds, klass = ("null", "swap"), "protected-role"
            elif (attr.get("derivation") or {}).get("kind") == "computed_within_entity":
                kinds, klass = ("swap", "perturb"), "derived"
            elif attr.get("nullable") is False and role != "identity":
                kinds, klass = ("null",), "non-nullable"
            else:
                continue
            for kind in kinds:
                if scratch.exists():
                    scratch.unlink()
                shutil.copy(database, scratch)
                con = duckdb.connect(str(scratch))
                try:
                    target_table = physical(con, table)
                    rows = con.execute(f"SELECT {', '.join(ids)}, {attr['name']} FROM {target_table} ORDER BY 1, 2").fetchall()
                    candidates = [r for r in rows if r[-1] is not None] if kind == "null" else rows
                    if not candidates:
                        continue
                    target_row = candidates[-1]
                    where = " AND ".join(f"{c} = ?" for c in ids)
                    if kind == "null":
                        con.execute(f"UPDATE {target_table} SET {attr['name']} = NULL WHERE {where}", list(target_row[:-1]))
                    elif kind == "perturb":
                        col_type = con.execute(f"SELECT typeof({attr['name']}) FROM {target_table} WHERE {attr['name']} IS NOT NULL LIMIT 1").fetchone()
                        if not col_type:
                            continue
                        t = col_type[0].upper()
                        expr = (f"NOT {attr['name']}" if t == "BOOLEAN" else f"{attr['name']} + INTERVAL 1 DAY" if t.startswith(("TIMESTAMP", "DATE"))
                                else f"{attr['name']} || 'x'" if t.startswith(("VARCHAR", "STRING")) else f"{attr['name']} + 1")
                        con.execute(f"UPDATE {target_table} SET {attr['name']} = {expr} WHERE {where}", list(target_row[:-1]))
                    else:
                        others = [r[-1] for r in rows if r[-1] != target_row[-1] and r[-1] is not None]
                        if not others:
                            continue
                        con.execute(f"UPDATE {target_table} SET {attr['name']} = ? WHERE {where}", [others[0], *target_row[:-1]])
                    fired = [inv for inv, sql in audits if con.execute(sql).fetchall()]
                finally:
                    con.close()
                results.append({"entity": entity["id"], "attribute": attr["name"], "role": role, "class": klass, "mutation": kind, "fired": fired, "protected": bool(fired)})
    unprotected = [r for r in results if not r["protected"]]
    return {"target": target, "job": job, "mutations": len(results), "unprotected": unprotected, "results": results}


def compare(job: str, target_a: str, target_b: str, phase: str = "rollover") -> dict:
    """Engine independence: the same selected L2 projected on two targets must yield identical tables."""
    ra = run(target_a, job, phase, database=ROOT / f"build/chain-compare-{target_a}.duckdb")
    rb = run(target_b, job, phase, database=ROOT / f"build/chain-compare-{target_b}.duckdb")
    model, _ = load_job(job)
    tables = ["governed." + e["id"].split(".")[-1] for e in model["entities"]]
    out = {"job": job, "targets": [target_a, target_b], "both_ok": ra["ok"] and rb["ok"], "tables": {}}
    ca = duckdb.connect(str(ROOT / f"build/chain-compare-{target_a}.duckdb"), read_only=True)
    cb = duckdb.connect(str(ROOT / f"build/chain-compare-{target_b}.duckdb"), read_only=True)
    try:
        for table in tables:
            try:
                a_rows = ca.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
                b_rows = cb.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
            except duckdb.Error as error:
                out["tables"][table] = {"identical": False, "error": str(error)}
                continue
            a_cols = [d[0] for d in ca.execute(f"SELECT * FROM {table} LIMIT 0").description]
            b_cols = [d[0] for d in cb.execute(f"SELECT * FROM {table} LIMIT 0").description]
            out["tables"][table] = {"identical": a_rows == b_rows and a_cols == b_cols, "rows": [len(a_rows), len(b_rows)], "columns_match": a_cols == b_cols}
    finally:
        ca.close(); cb.close()
    out["identical"] = out["both_ok"] and all(v.get("identical") for v in out["tables"].values())
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("check", "run", "stamp", "compare", "twophase", "mutate", "simulate"))
    p.add_argument("--ce", type=Path, help="simulate: a counterexample document (fixture.ce_account_changes and/or fixture.raw_additions)")
    p.add_argument("target")
    p.add_argument("job")
    p.add_argument("--against", help="compare: the second target")
    p.add_argument("--phase", default="rollover", choices=("first_encounter", "rollover"))
    a = p.parse_args()
    try:
        if a.command == "check":
            r = check(a.target, a.job); print(json.dumps(r, indent=2)); return 0 if r["status"] == "ok" else 3
        if a.command == "stamp":
            print(json.dumps(stamp(a.target, a.job), indent=2)); return 0
        if a.command == "simulate":
            if not a.ce:
                raise L3Error("simulate needs --ce <counterexample document>")
            r = simulate(a.target, a.job, a.ce); print(json.dumps(r, indent=2)); return 0 if not r["silent"] else 4
        if a.command == "mutate":
            r = mutate(a.target, a.job); print(json.dumps(r, indent=2)); return 0 if not r["unprotected"] else 3
        if a.command == "twophase":
            r = run_two_phase(a.target, a.job); print(json.dumps(r, indent=2)); return 0 if r["first_phase_ok"] and r["second_phase_ok"] else 3
        if a.command == "compare":
            r = compare(a.job, a.target, a.against, a.phase); print(json.dumps(r, indent=2)); return 0 if r["identical"] else 3
        r = run(a.target, a.job, a.phase); print(json.dumps(r, indent=2)); return 0 if r["ok"] else 3
    except (L3Error, OSError, json.JSONDecodeError, duckdb.Error) as error:
        print(f"l3 error: {error}", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
