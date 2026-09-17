#!/usr/bin/env python3
"""CESS harness for the chain: renders anchors K, runs gate G, and computes the revalidation profile.

Roles (see skills/cess): the Sketches under sketches/ are S; contracts under contracts/incremental
plus this harness's rendered scaffold are K; the governed model SQL under <project>/models/ is P,
written by a Developer under an explicit change contract; audits, the AST guard, and the CE run
are G. This file never writes governed SELECT bodies.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import duckdb
from jsonschema import Draft202012Validator
from sqlglot import exp, parse, parse_one

ROOT = Path(__file__).resolve().parents[1]
C = "contracts/incremental"
TYPES = f"{C}/semantic-types/dim-trade-incremental-types-v1.json"
SKETCHES = ["sketches/chain-index-v1.md", "sketches/dim-customer-scd2-v1.md", "sketches/dim-account-scd2-v1.md", "sketches/trade-dim-incremental-v1.md", "sketches/fact-holdings-v1.md", "sketches/position-metrics-v1.md"]
LOGICAL = {m: f"{C}/logical-models/{f}" for m, f in {
    "dim_customer": "dim-customer-v1.json", "dim_account": "dim-account-v1.json", "dim_trade_incremental": "dim-trade-incremental-v1.json",
    "fact_holdings": "fact-holdings-v1.json", "position_by_account": "position-by-account-v1.json", "position_by_customer": "position-by-customer-v1.json"}.items()}
STAGES = [f"{C}/stages/{f}" for f in ("customer-mgmt-action-v1.json", "account-cdc-v1.json", "customer-cdc-v1.json", "account-change-ce-v1.json", "trade-cdc-v1.json", "holding-history-v1.json")]
EDGES = [f"{C}/edges/{f}" for f in ("change-feeds-to-dim-customer-v1.json", "change-feeds-to-dim-account-v1.json", "trade-cdc-to-dim-trade-incremental-v1.json", "holding-history-to-fact-holdings-v1.json", "fact-holdings-to-position-metrics-v1.json")]
REPAIRS = [f"{C}/repair-authority/{f}" for f in ("dim-account-scd2-edge-v1.json", "dim-trade-incremental-edge-v1.json", "fact-holdings-edge-v1.json")]
MERGE_MODELS = {"dim_trade_incremental": "dim_trade_key_binding", "fact_holdings": "fact_holdings_key_binding"}
FULL_AUDITS = {
    "dim_customer": ["dim_customer_one_current_version"],
    "dim_account": ["dim_account_one_current_version", "dim_account_versions_do_not_overlap"],
    "position_by_account": ["position_by_account_nonnegative"],
    "position_by_customer": ["position_by_customer_nonnegative"],
}
FORBIDDEN_CONTEXT = ("oracle/", "counterexamples/archive/")
REFERENCE_NODES = {"reference.dim_account_as_of": "logical.dim_account", "reference.dim_customer_as_of": "logical.dim_customer", "reference.dim_trade_incremental": "logical.dim_trade_incremental"}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


GUARD = _load("merge_guard", "scripts/merge_guard.py")
CONTRACTS = _load("governed_contracts", "scripts/contracts.py")
LOADER = _load("chain_load", "scripts/chain_load.py")


class HarnessError(ValueError):
    pass


def J(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def validate(schema_name: str, instance: dict, label: str) -> None:
    schema_dir = ROOT / (f"{C}/schema" if "v2" in schema_name else "contracts/schema")
    schema = json.loads((schema_dir / schema_name).read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        raise HarnessError(f"{label} violates {schema_name}: {errors[0].message} at {list(errors[0].path)}")


def anchors() -> dict:
    """Validate K and derive everything the Developer may not choose: columns, roles, headers, audits."""
    types = J(TYPES)
    validate("semantic-types-v2.schema.json", types, "semantic types")
    roles = GUARD.load_roles(types)
    physical = {t["id"]: t["physical_type"] for t in types["types"]}
    logical = {m: J(p) for m, p in LOGICAL.items()}
    for m, doc in logical.items():
        validate("logical-model-v1.schema.json", doc, m)
    stages = [J(p) for p in STAGES]
    for s in stages:
        validate("stage-contract-v2.schema.json", s, s["contract_id"])
    edges = [J(p) for p in EDGES]
    for e in edges:
        validate("edge-contract-v2.schema.json", e, e["contract_id"])
        if e["history_policy"].get("mutation_policy_source") != "semantic type mutation_role; the edge restates no column list":
            raise HarnessError(f"{e['contract_id']} must defer mutation policy to semantic types")
        for key in ("mutable_columns", "frozen_columns", "update_set"):
            if key in e or key in e["history_policy"]:
                raise HarnessError(f"{e['contract_id']} restates a column list")
        if e["rule_order"] != [r["id"] for r in e["rules"]]:
            raise HarnessError(f"{e['contract_id']} rule order mismatch")
        for r in e["rules"]:
            if r["status"] == "assumed" and not r["authority"].startswith("issue-8-"):
                raise HarnessError(f"{e['contract_id']} assumed rule lacks a recorded adjudication")
    for p in REPAIRS:
        rec = J(p)
        validate("repair-authority-v1.schema.json", rec, p)
        try:
            CONTRACTS.validate_repair_authority(rec)
        except CONTRACTS.ContractError as error:
            raise HarnessError(f"{p}: {error}") from error
        if "materialization.governed_merge" not in rec["forbidden_adjacent_policy"]:
            raise HarnessError(f"{p} must forbid editing the workaround materialization")
    for s in SKETCHES:
        text = (ROOT / s).read_text()
        if "status: incomplete" not in text or "## Explicit holes" not in text and "chain-index" not in s:
            raise HarnessError(f"{s} must be an incomplete Sketch with explicit holes")
    for s in ("sketches/trade-dim-incremental-v1.md", "sketches/fact-holdings-v1.md"):
        if "## Projection workaround (not policy)" not in (ROOT / s).read_text():
            raise HarnessError(f"{s} must name the MERGE workaround as projection")
    holes = [h for doc in [*logical.values(), *stages, *edges] for h in doc.get("holes", [])]
    for required in ("incremental.authority-locator", "fact-holdings.key-resolution-authority"):
        if not any(h["id"] == required and h["status"] == "open" for h in holes):
            raise HarnessError(f"hole {required} must stay open until the specification is read")

    column_roles = {m: GUARD.column_roles(doc, roles) for m, doc in logical.items()}
    # Seam 1: handoff binding. Every mapping source resolves to a producer attribute of identical semantic type.
    stage_out = {s["stage_id"]: {f["name"]: f["semantic_type"] for f in s["output"]["fields"]} for s in stages}
    logical_attrs = {doc["model_id"]: {a["name"]: a["semantic_type"] for a in doc["attributes"]} for doc in logical.values()}
    stage_entities = {s["stage_id"]: f"governed.{s['stage_id'].split('.')[-1]}_stage" for s in stages}
    allowed_reads = {}
    for e in edges:
        reads = set()
        for m in e["mappings"]:
            src, name = m["from"].rsplit(".", 1)
            if src.startswith("stage."):
                producer = stage_out.get(src)
                reads.add(stage_entities.get(src, ""))
            elif src in REFERENCE_NODES:
                producer = logical_attrs.get(REFERENCE_NODES[src])
                reads.add("governed." + REFERENCE_NODES[src].split(".")[-1])
            elif src.startswith("logical."):
                producer = logical_attrs.get(src)
                reads.add("governed." + src.split(".")[-1])
            else:
                raise HarnessError(f"{e['contract_id']}: unknown producer {src}")
            if producer is None or name not in producer:
                raise HarnessError(f"{e['contract_id']}: handoff {m['from']} names no producer attribute")
            if producer[name] != m["source_semantic_type"]:
                raise HarnessError(f"{e['contract_id']}: handoff {m['from']} declares {m['source_semantic_type']} but the producer emits {producer[name]}")
            target_model, target_col = m["to"].rsplit(".", 1)
            if logical_attrs.get(target_model, {}).get(target_col) != m["target_semantic_type"]:
                raise HarnessError(f"{e['contract_id']}: mapping target {m['to']} disagrees with the consumer logical model")
        for consumer in re.findall(r"logical\.[a-z_]+", e["consumer"]["contract"]):
            allowed_reads[consumer.split(".")[-1]] = reads
    surfaces = {m: GUARD.update_surface(column_roles[m]) for m in MERGE_MODELS}
    for m, surface in surfaces.items():
        if len(surface["frozen"]) < 2:
            raise HarnessError(f"{m}: frozen role must cover at least two columns")
    frozen_types = {t["id"] for t in types["types"] if t["mutation_role"] == GUARD.FROZEN}
    consumers = {m for m, doc in logical.items() if any(a["semantic_type"] in frozen_types for a in doc["attributes"])}
    if len(consumers & set(MERGE_MODELS)) < 2:
        raise HarnessError("the frozen role must be consumed by at least two governed merge models")
    columns = {m: {a["name"]: physical[a["semantic_type"]] for a in doc["attributes"]} for m, doc in logical.items()}
    headers = {}
    for m in logical:
        cols = ", ".join(f"{c} {t}" for c, t in columns[m].items())
        if m in MERGE_MODELS:
            s = surfaces[m]
            binding = MERGE_MODELS[m]
            headers[m] = (
                f"MODEL (\n  name governed.{m},\n  kind CUSTOM (\n    materialization 'governed_merge',\n    materialization_properties (\n"
                f"      'unique_key' = '{', '.join(s['identity'])}',\n      'mutable_columns' = '{', '.join(s['mutable'])}',\n      'frozen_columns' = '{', '.join(s['frozen'])}'\n    )\n  ),\n"
                f"  dialect duckdb,\n  columns ({cols}),\n  depends_on (governed.{binding}),\n  audits ({m}_frozen_keys_bound_once, {m}_identity_not_null)\n);"
            )
        else:
            headers[m] = f"MODEL (\n  name governed.{m},\n  kind FULL,\n  dialect duckdb,\n  columns ({cols}),\n  audits ({', '.join([*FULL_AUDITS[m], f'{m}_identity_not_null'])})\n);"
    return {"types": types, "roles": roles, "physical": physical, "logical": logical, "stages": stages, "edges": edges, "column_roles": column_roles, "surfaces": surfaces, "columns": columns, "headers": headers, "allowed_reads": allowed_reads}


MATERIALIZATION = '''"""governed_merge: SQLMesh CUSTOM materialization executing a role-derived native MERGE.

Workaround for SQLMesh's missing native DuckDB MERGE (see each Sketch's projection-workaround
section). Classified as sqlmesh_model projection. It carries no policy: the column lists it
receives were derived from mutation roles by the harness, and it re-checks them here.
"""
from __future__ import annotations

from sqlglot import exp
from sqlmesh import CustomMaterialization
from sqlmesh.core.model import Model


class GovernedMergeMaterialization(CustomMaterialization):
    NAME = "governed_merge"

    def insert(self, table_name: str, query_or_df, model: Model, is_first_insert: bool, render_kwargs, **kwargs) -> None:
        props = model.kind.materialization_properties
        keys = [c.strip() for c in props["unique_key"].split(",") if c.strip()]
        mutable = [c.strip() for c in props.get("mutable_columns", "").split(",") if c.strip()]
        frozen = [c.strip() for c in props.get("frozen_columns", "").split(",") if c.strip()]
        offending = sorted((set(mutable) & set(frozen)) | (set(mutable) & set(keys)))
        if offending:
            raise ValueError(f"frozen_from_first_encounter or identity column in matched update: {offending}")
        columns = list(model.columns_to_types)
        whens = []
        if mutable:
            whens.append(exp.When(matched=True, then=exp.Update(expressions=[
                exp.EQ(this=exp.column(c), expression=exp.column(c, "src")) for c in mutable])))
        whens.append(exp.When(matched=False, then=exp.Insert(
            this=exp.Tuple(expressions=[exp.column(c) for c in columns]),
            expression=exp.Tuple(expressions=[exp.column(c, "src") for c in columns]))))
        merge = exp.Merge(
            this=exp.alias_(exp.to_table(table_name), "tgt", table=True),
            using=exp.Subquery(this=query_or_df, alias=exp.TableAlias(this=exp.to_identifier("src"))),
            on=exp.and_(*[exp.EQ(this=exp.column(k, "tgt"), expression=exp.column(k, "src")) for k in keys]),
            whens=exp.Whens(expressions=whens),
        )
        for when in merge.args["whens"].expressions:
            then = when.args.get("then")
            if when.args.get("matched") and isinstance(then, exp.Update):
                written = {e.this.name for e in then.expressions}
                if written & set(frozen):
                    raise ValueError(f"guard: matched update writes frozen column {sorted(written & set(frozen))}")
        self.adapter.execute(merge)
'''


def stage_model(contract: dict) -> str:
    name = contract["stage_id"].split(".")[-1] + "_stage"
    sql = "SELECT " + ", ".join(f"{f['source']} AS {f['name']}" for f in contract["output"]["fields"]) + f" FROM {contract['input']['entity']}"
    if contract["stage_id"] == "stage.account_change_ce":
        sql += " WHERE provenance = 'controlled_counterexample'"
    audits = ", audits (account_change_ce_stage_rows_labeled)" if contract["stage_id"] == "stage.account_change_ce" else ""
    return f"MODEL (\n  name governed.{name},\n  kind FULL,\n  dialect duckdb{audits}\n);\n\n" + parse_one(sql, dialect="duckdb").sql(dialect="duckdb", pretty=True) + "\n"


def audits(k: dict) -> dict[str, str]:
    out = {}
    for m, surface in k["surfaces"].items():
        binding = MERGE_MODELS[m]
        keys, frozen = surface["identity"], surface["frozen"]
        on = " AND ".join(f"d.{c} = b.{c}" for c in keys)
        out[f"{m}_frozen_keys_bound_once.sql"] = (f"AUDIT (name {m}_frozen_keys_bound_once);\n\nSELECT " + ", ".join(f"d.{c}" for c in keys) + ", " +
            ", ".join(f"d.{c} AS current_{c}, b.{c} AS bound_{c}" for c in frozen) + f"\nFROM @this_model AS d JOIN governed.{binding} AS b ON {on}\nWHERE " +
            " OR ".join(f"d.{c} IS DISTINCT FROM b.{c}" for c in frozen) + "\n")
    for m, doc in k["logical"].items():
        ids = doc["identifiers"]
        out[f"{m}_identity_not_null.sql"] = f"AUDIT (name {m}_identity_not_null);\n\nSELECT * FROM @this_model WHERE " + " OR ".join(f"{c} IS NULL" for c in ids) + "\n"
    for dim, nat in (("dim_customer", "customer_id"), ("dim_account", "account_id")):
        out[f"{dim}_one_current_version.sql"] = f"AUDIT (name {dim}_one_current_version);\n\nSELECT {nat}, COUNT(*) FILTER (WHERE is_current) AS current_versions FROM @this_model GROUP BY {nat} HAVING current_versions <> 1\n"
    out["dim_account_versions_do_not_overlap.sql"] = ("AUDIT (name dim_account_versions_do_not_overlap);\n\nSELECT * FROM (SELECT account_id, effective_from, effective_to, "
        "LEAD(effective_from) OVER (PARTITION BY account_id ORDER BY effective_from) AS next_from FROM @this_model) WHERE next_from IS NOT NULL AND (effective_to <> next_from OR effective_from >= effective_to)\n")
    for m in ("position_by_account", "position_by_customer"):
        out[f"{m}_nonnegative.sql"] = f"AUDIT (name {m}_nonnegative);\n\nSELECT * FROM @this_model WHERE position < 0\n"
    out["account_change_ce_stage_rows_labeled.sql"] = "AUDIT (name account_change_ce_stage_rows_labeled);\n\nSELECT * FROM @this_model WHERE provenance IS DISTINCT FROM 'controlled_counterexample'\n"
    return out


def scaffold(project: Path, database: Path, k: dict | None = None) -> dict:
    """Render K into the project. Governed model bodies under models/ are the Developer's and are preserved."""
    k = k or anchors()
    (project / "models").mkdir(parents=True, exist_ok=True)
    (project / "audits").mkdir(exist_ok=True)
    (project / "materializations").mkdir(exist_ok=True)
    for stage in k["stages"]:
        (project / "models" / (stage["stage_id"].split(".")[-1] + "_stage.sql")).write_text(stage_model(stage))
    for name, sql in audits(k).items():
        (project / "audits" / name).write_text(sql)
    (project / "materializations/governed_merge.py").write_text(MATERIALIZATION)
    (project / "config.yaml").write_text(
        "gateways:\n  duckdb:\n    connection:\n      type: duckdb\n" f"      database: '{database.as_posix()}'\n"
        "default_gateway: duckdb\nmodel_defaults:\n  dialect: duckdb\n  start: '2012-01-01'\n  cron: '@daily'\nlinter:\n  enabled: false\n")
    (project / "required-headers.json").write_text(json.dumps({"note": "Each governed model file must begin with exactly this header (whitespace-insensitive), followed by one SELECT.", "headers": k["headers"], "column_roles": k["column_roles"]}, indent=2, sort_keys=True) + "\n")
    return k


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def split_model(text: str) -> tuple[str, str]:
    idx = text.find(");")
    if not text.lstrip().startswith("MODEL") or idx < 0:
        raise HarnessError("model file must start with a MODEL (...) header")
    return text[: idx + 2], text[idx + 2:].strip()


def check(project: Path, k: dict | None = None) -> dict:
    """Header conformance, guard over every statement, and binding-model regeneration. Reports per model."""
    k = k or anchors()
    report = {}
    for m, header in k["headers"].items():
        path = project / "models" / f"{m}.sql"
        if not path.exists():
            report[m] = {"status": "missing"}
            continue
        head, body = split_model(path.read_text())
        problems = []
        if _norm(head) != _norm(header):
            problems.append("header differs from required header (see required-headers.json)")
        statements = [s for s in parse(body, dialect="duckdb") if s is not None]
        if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union, exp.Query)):
            problems.append("body must be exactly one SELECT query")
        for s in statements:
            verdict = GUARD.guard_statement(s, k["column_roles"][m], m)
            if not verdict.ok:
                problems.append("guard: " + json.dumps(verdict.attempted_writes))
            # Seam 2: read containment. The body may reference only its edge's declared producers.
            allowed = k["allowed_reads"].get(m, set())
            ctes = {c.alias_or_name.lower() for c in s.find_all(exp.CTE)}
            reads = {f"{t.db}.{t.name}".lower() if t.db else t.name.lower() for t in s.find_all(exp.Table) if t.name.lower() not in ctes}
            illegal = sorted(r for r in reads if r not in {a.lower() for a in allowed})
            if illegal:
                problems.append(f"reads outside declared producers {sorted(allowed)}: {illegal}")
        if not problems and m in MERGE_MODELS:
            binding = MERGE_MODELS[m]
            s = k["surfaces"][m]
            cols = [*s["identity"], *s["frozen"]]
            bcols = ", ".join(f"{c} {k['columns'][m][c]}" for c in cols)
            (project / "models" / f"{binding}.sql").write_text(
                f"MODEL (\n  name governed.{binding},\n  kind CUSTOM (\n    materialization 'governed_merge',\n    materialization_properties (\n"
                f"      'unique_key' = '{', '.join(s['identity'])}',\n      'mutable_columns' = '',\n      'frozen_columns' = '{', '.join(s['frozen'])}'\n    )\n  ),\n  dialect duckdb,\n  columns ({bcols})\n);\n\n"
                f"SELECT {', '.join(cols)} FROM (\n{statements[0].sql(dialect='duckdb', pretty=True)}\n) AS first_encounter\n")
        report[m] = {"status": "ok" if not problems else "rejected", "problems": problems}
    return report


def sqlmesh(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), *args], cwd=ROOT, text=True, capture_output=True)


def plan(project: Path, restate_stages: bool = False) -> str:
    shutil.rmtree(project / ".cache", ignore_errors=True)
    args = ["plan", "prod", "--auto-apply", "--no-prompts", "--skip-tests", "--skip-linter"]
    if restate_stages:
        for stage in [J(p) for p in STAGES]:
            args += ["--restate-model", f"governed.{stage['stage_id'].split('.')[-1]}_stage"]
    result = sqlmesh(project, *args)
    if result.returncode or "Failed models" in result.stdout:
        raise HarnessError(f"SQLMesh plan failed:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}")
    return result.stdout


def audit(project: Path) -> tuple[bool, str]:
    result = sqlmesh(project, "audit")
    return (result.returncode == 0 and "0 audit errors" in result.stdout), result.stdout + result.stderr


def q(database: Path, sql: str) -> list[dict]:
    con = duckdb.connect(str(database), read_only=True)
    try:
        cur = con.execute(sql)
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]
    finally:
        con.close()


def run_counterexample(project: Path, database: Path, ce_path: Path = ROOT / "counterexamples/archive/ce-account-428-rollover-v1.json") -> dict:
    """Two-phase simulation of the labeled CE. Reads the CE only here; the scaffold never does."""
    ce = json.loads(ce_path.read_text())
    fixture = J(ce["fixture"]["raw_anchor"])
    changes = [{k: v for k, v in row.items() if k != "note"} for row in ce["fixture"]["ce_account_changes"]]
    LOADER.load_fixture(database, fixture, "first_encounter")
    plan(project)
    trade = ce["expected"]["trade_id"]
    before = q(database, f"SELECT * FROM governed.dim_trade_incremental WHERE trade_id = {trade}")
    LOADER.load_fixture(database, fixture, "rollover", changes)
    plan(project, restate_stages=True)
    after = q(database, f"SELECT * FROM governed.dim_trade_incremental WHERE trade_id = {trade}")
    versions = q(database, "SELECT sk_account_id, effective_from, effective_to, is_current FROM governed.dim_account WHERE account_id = 428 ORDER BY effective_from")
    first_encounter_ts = [r["t_dts"] for r in fixture["raw"]["trade_cdc"] if r["t_id"] == trade and r["cdc_flag"] == "I"][0]
    as_of = q(database, f"SELECT sk_account_id FROM governed.dim_account WHERE account_id = 428 AND TIMESTAMP '{first_encounter_ts}' >= effective_from AND TIMESTAMP '{first_encounter_ts}' < effective_to")
    holdings = q(database, "SELECT * FROM governed.fact_holdings ORDER BY current_trade_id")
    positions = q(database, "SELECT * FROM governed.position_by_account ORDER BY sk_account_id")
    ok, audit_text = audit(project)
    return {"before": before, "after": after, "account_428_versions": versions, "sk_as_of_first_encounter": as_of, "fact_holdings": holdings, "position_by_account": positions, "audit_ok": ok, "audit_text": audit_text[-3000:], "expected": ce["expected"]}


def revalidation_profile(k: dict | None = None) -> dict:
    """Typed semantic edges from the edge contracts. The AFFECTED list is computed here, never a constant."""
    k = k or anchors()
    edges = []
    for e in k["edges"]:
        for m in e["mappings"]:
            src = m["from"]
            for ref, node in REFERENCE_NODES.items():
                if src.startswith(ref + "."):
                    src = node + "." + src.rsplit(".", 1)[-1]
            edges.append({"from": src, "to": m["to"], "role": k["roles"].get(m["target_semantic_type"], "none"), "semantic_type": m["target_semantic_type"], "edge_contract": e["contract_id"]})
    return {"schema_version": "revalidation-profile/v2", "nodes": sorted({x for e in edges for x in (e["from"], e["to"])}), "edges": edges}


def affected(profile: dict, node: str) -> dict:
    seen, frontier = set(), [node]
    while frontier:
        current = frontier.pop()
        for e in profile["edges"]:
            if e["from"] == current and e["to"] not in seen:
                seen.add(e["to"])
                frontier.append(e["to"])
    models = sorted({".".join(n.split(".")[:2]) for n in seen})
    return {"columns": sorted(seen), "models": models}


GATES_BY_MODEL = {**{m: [f"{m}_frozen_keys_bound_once", f"{m}_identity_not_null"] for m in MERGE_MODELS}, **{m: [*a, f"{m}_identity_not_null"] for m, a in FULL_AUDITS.items()}}


def cone(project: Path, profile: dict, violated_node: str) -> dict:
    """Seam 3: run only the gates of models downstream of the violated node."""
    hit = affected(profile, violated_node)
    selected = {m.split(".")[-1]: GATES_BY_MODEL.get(m.split(".")[-1], []) for m in hit["models"]}
    results = {}
    for model, gates in selected.items():
        result = sqlmesh(project, "audit", "--model", f"governed.{model}")
        results[model] = {"gates": gates, "ok": result.returncode == 0 and "0 audit errors" in result.stdout, "output": (result.stdout + result.stderr)[-1500:]}
    return {"violated_node": violated_node, "affected": hit, "results": results}


def acceptance_matrix(project: Path, database: Path, reviews: dict[str, dict] | None = None) -> dict:
    """Seam 4: accepted(chain, case) = every link passes G and sketch review. Reviews are supplied by a judge per link."""
    rows = []
    for model, gates in GATES_BY_MODEL.items():
        result = sqlmesh(project, "audit", "--model", f"governed.{model}")
        gate_ok = result.returncode == 0 and "0 audit errors" in result.stdout
        review = (reviews or {}).get(model, {"verdict": "not-run"})
        rows.append({"model": model, "gates": gates, "deterministic_gate": "pass" if gate_ok else "fail", "sketch_review": review.get("verdict", "not-run"), "review_notes": review.get("notes", "")})
    accepted = all(r["deterministic_gate"] == "pass" and r["sketch_review"] == "pass" for r in rows)
    return {"accepted": accepted, "rows": rows, "rule": "accepted(case, P, S) = gate_passes AND sketch_review_passes for every link; a missing review is not a pass"}


def diagnosis(verdict, profile: dict, model: str) -> str:
    descendants = sorted({m for w in verdict.attempted_writes for m in affected(profile, f"logical.{model}.{w['column']}")["models"]})
    return GUARD.diagnosis(verdict, descendants)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("scaffold", "check", "plan", "audit", "ce", "guard", "profile", "cone", "accept"))
    p.add_argument("--node", default="logical.dim_trade_incremental.sk_account_id")
    p.add_argument("--project", type=Path, default=ROOT / "build/chain-projection")
    p.add_argument("--database", type=Path, default=ROOT / "build/chain.duckdb")
    p.add_argument("--restate", action="store_true")
    p.add_argument("--model", default="dim_trade_incremental")
    p.add_argument("path", nargs="?")
    a = p.parse_args()
    try:
        if a.command == "scaffold":
            scaffold(a.project, a.database); print(json.dumps({"scaffolded": str(a.project), "required_headers": str(a.project / "required-headers.json")}))
        elif a.command == "check":
            report = check(a.project); print(json.dumps(report, indent=2)); return 0 if all(r["status"] == "ok" for r in report.values()) else 3
        elif a.command == "plan":
            print(plan(a.project, a.restate)[-3000:])
        elif a.command == "audit":
            ok, text = audit(a.project); print(text[-3000:]); return 0 if ok else 3
        elif a.command == "ce":
            print(json.dumps(run_counterexample(a.project, a.database), indent=2, default=str))
        elif a.command == "guard":
            k = anchors(); verdict = GUARD.guard_sql(Path(a.path).read_text(), k["column_roles"][a.model], a.model)
            print(diagnosis(verdict, revalidation_profile(k), a.model)); return 0 if verdict.ok else 3
        elif a.command == "cone":
            print(json.dumps(cone(a.project, revalidation_profile(), a.node), indent=2))
        elif a.command == "accept":
            print(json.dumps(acceptance_matrix(a.project, a.database), indent=2))
        elif a.command == "profile":
            prof = revalidation_profile(); print(json.dumps({"edges": len(prof["edges"]), "affected_by_dim_trade_sk_account_id": affected(prof, "logical.dim_trade_incremental.sk_account_id")}, indent=2))
    except (HarnessError, GUARD.GuardError) as error:
        print(f"harness error: {error}", file=sys.stderr); return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
