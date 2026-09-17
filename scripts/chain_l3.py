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
    model_path = L2_DIR / job / "semantic-model.json"
    if not model_path.exists():
        raise L3Error(f"{job} has no L2 model; L3 compiles only from a selected L2")
    model = json.loads(model_path.read_text())
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


def body_of(sql: str, sqlmesh_target: bool) -> str:
    """For SQLMesh targets, strip the MODEL (...) or AUDIT (...) header and resolve @this_model for parsing."""
    if not sqlmesh_target:
        return sql
    text = sql.lstrip()
    if text.startswith(("MODEL", "AUDIT")):
        idx = text.find(");")
        text = text[idx + 2:] if idx >= 0 else text
    return text.replace("@this_model", "this_model_placeholder")


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
    if manifest.get("derived_from_model", {}).get("review_sha256") != review["model_sha256"]:
        problems.append("manifest review_sha256 does not match the selected L2 model; recompile from the current review")
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
    governance = re.compile(r"^(change-contract-\d+\.md|review(-\d+)?\.(md|json)|adjudication-.*\.md)$")
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
    for a in manifest.get("audits", []):
        if a["invariant"] not in invariants:
            problems.append(f"audit {a['file']} names {a['invariant']}, not a selected deterministic invariant")
        if not (base / a["file"]).exists():
            problems.append(f"audit {a['file']} missing")
        elif sqlmesh_target and not (base / a["file"]).read_text().lstrip().startswith("AUDIT"):
            problems.append(f"audit {a['file']} must be a SQLMesh AUDIT file on target {target}")
    status = "rejected" if problems else ("question" if questions else "ok")
    return {"target": target, "job": job, "status": status, "problems": problems, "questions": questions, "profile": profile["target"],
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
    if result.returncode or "Failed models" in result.stdout:
        raise L3Error(f"SQLMesh plan failed:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}")
    audit = subprocess.run([str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), "audit"], cwd=ROOT, text=True, capture_output=True)
    fixture_report["sqlmesh"] = {"plan_tail": result.stdout[-800:], "audit_ok": audit.returncode == 0 and "0 audit errors" in audit.stdout, "audit_tail": (audit.stdout + audit.stderr)[-1500:]}
    manifest = json.loads((L3_DIR / target / job / "manifest.json").read_text())
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


def run(target: str, job: str, phase: str = "rollover", database: Path | None = None) -> dict:
    """Load the fixture (and labeled CE rows for the rollover phase), run upstream jobs' projections, then this job, then audits."""
    fixture = json.loads((ROOT / "oracle/fixtures/public/chain-fixture-v1.json").read_text())
    ce = json.loads((ROOT / "counterexamples/archive/ce-account-428-rollover-v1.json").read_text())
    changes = [{k: v for k, v in row.items() if k != "note"} for row in ce["fixture"]["ce_account_changes"]]
    database = database or ROOT / f"build/chain-{target}.duckdb"
    LOADER.load_fixture(database, fixture, phase, changes if phase == "rollover" else None)
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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("check", "run"))
    p.add_argument("target")
    p.add_argument("job")
    p.add_argument("--phase", default="rollover", choices=("first_encounter", "rollover"))
    a = p.parse_args()
    try:
        if a.command == "check":
            r = check(a.target, a.job); print(json.dumps(r, indent=2)); return 0 if r["status"] == "ok" else 3
        r = run(a.target, a.job, a.phase); print(json.dumps(r, indent=2)); return 0 if r["ok"] else 3
    except (L3Error, OSError, json.JSONDecodeError, duckdb.Error) as error:
        print(f"l3 error: {error}", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
