#!/usr/bin/env python3
"""Compile the incremental DimTrade slice: roles -> SQLGlot MERGE -> guarded SQLMesh projection.

Governing inputs: the incremental Sketch, semantic types v2 (mutation roles), the logical
model, the Trade CDC stage contract, the CDC-to-DimTrade edge contract, and the repair
authority. Everything rendered here is replaceable projection. The ``governed_merge``
materialization is a workaround for SQLMesh's missing native DuckDB MERGE; the Sketch says so.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import duckdb
from jsonschema import Draft202012Validator
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build/incremental-projection"
RETAINED_MANIFEST = ROOT / "projection/manifest-incremental-v1.json"
SKETCH = "sketches/trade-dim-incremental-v1.md"
TYPES = "contracts/incremental/semantic-types/dim-trade-incremental-types-v1.json"
LOGICAL = "contracts/incremental/logical-models/dim-trade-incremental-v1.json"
STAGE = "contracts/incremental/stages/trade-cdc-v1.json"
EDGE = "contracts/incremental/edges/trade-cdc-to-dim-trade-incremental-v1.json"
REPAIR = "contracts/incremental/repair-authority/dim-trade-incremental-edge-v1.json"
GOVERNING_INPUTS = (SKETCH, TYPES, LOGICAL, STAGE, EDGE, REPAIR)
FORBIDDEN_CONTEXT = ("oracle/", "counterexamples/archive/", "oracle/fixtures/held-out/", "oracle/submissions/held-out/")
TARGET_MODEL = "dim_trade_incremental"
BINDING_MODEL = "dim_trade_key_binding"
DESCENDANTS = ["logical.fact_holdings", "metric.position_by_account", "metric.position_by_customer"]

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

GUARD = _load_module("merge_guard", ROOT / "scripts/merge_guard.py")
CONTRACTS = _load_module("governed_contracts", ROOT / "scripts/contracts.py")


class ProjectionError(ValueError):
    """The generated incremental projection is inconsistent with its governing inputs."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def load_inputs() -> dict[str, object]:
    inputs: dict[str, object] = {}
    for relative in GOVERNING_INPUTS:
        path = ROOT / relative
        if any(relative.startswith(prefix) for prefix in FORBIDDEN_CONTEXT):
            raise ProjectionError(f"compiler input {relative} is forbidden context")
        text = path.read_text(encoding="utf-8")
        inputs[relative] = json.loads(text) if relative.endswith(".json") else text
    return inputs


def _validate(schema_name: str, instance: dict, label: str) -> None:
    schema_dir = ROOT / ("contracts/incremental/schema" if "v2" in schema_name else "contracts/schema")
    schema = json.loads((schema_dir / schema_name).read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        raise ProjectionError(f"{label} violates {schema_name}: {errors[0].message}")


def preflight(inputs: dict[str, object]) -> dict[str, str]:
    sketch = inputs[SKETCH]
    for required in (
        "status: incomplete",
        "extends: trade-dim-v1",
        "## Known rules in order",
        "**Mutation roles govern the update surface.**",
        "**Emit the incremental write as a MERGE whose matched-update set is exactly the mutable-role columns.**",
        "**Verify twice, mechanically then at run time.**",
        "## Projection workaround (not policy)",
        "Retirement trigger:",
        "## Explicit holes",
        "`incremental.authority-locator`",
    ):
        if required not in sketch:
            raise ProjectionError(f"governing incremental Sketch lacks: {required}")
    _validate("semantic-types-v2.schema.json", inputs[TYPES], "semantic types")
    _validate("logical-model-v1.schema.json", inputs[LOGICAL], "logical model")
    _validate("stage-contract-v1.schema.json", inputs[STAGE], "stage contract")
    _validate("edge-contract-v2.schema.json", inputs[EDGE], "edge contract")
    _validate("repair-authority-v1.schema.json", inputs[REPAIR], "repair authority")
    try:
        roles = GUARD.column_roles(inputs[LOGICAL], GUARD.load_roles(inputs[TYPES]))
        surface = GUARD.update_surface(roles)
    except GUARD.GuardError as error:
        raise ProjectionError(str(error)) from error
    if len(surface["frozen"]) < 2:
        raise ProjectionError("frozen role must be reused on at least two columns or it is per-case policy")
    edge = inputs[EDGE]
    if edge["history_policy"].get("mutation_policy_source") != "semantic type mutation_role; the edge restates no column list":
        raise ProjectionError("edge contract must defer mutation policy to semantic types")
    for key in ("mutable_columns", "frozen_columns", "update_set"):
        if key in edge or key in edge["history_policy"]:
            raise ProjectionError("edge contract restates a column list; policy belongs on semantic types")
    if edge["rule_order"] != [rule["id"] for rule in edge["rules"]]:
        raise ProjectionError("edge rule order mismatch")
    if not any(rule["id"] == "edge.emit-merge-surface-from-roles" and rule["status"] == "known" for rule in edge["rules"]):
        raise ProjectionError("edge must name the role-derived MERGE surface rule")
    for rule in edge["rules"]:
        if rule["status"] == "assumed" and not rule["authority"].startswith("issue-8-"):
            raise ProjectionError("assumed rules must rest on the recorded adjudication")
    stage_types = {f["name"]: f["semantic_type"] for f in inputs[STAGE]["output"]["fields"]}
    for mapping in edge["mappings"]:
        source_name = mapping["from"].rsplit(".", 1)[-1]
        if mapping["from"].startswith("stage.trade_cdc.") and stage_types.get(source_name) != mapping["source_semantic_type"]:
            raise ProjectionError(f"edge mapping {mapping['to']} disagrees with the stage contract type")
        if mapping["source_semantic_type"] != mapping["target_semantic_type"]:
            raise ProjectionError(f"edge mapping {mapping['to']} converts semantic type without a conversion rule")
    repair = inputs[REPAIR]
    try:
        CONTRACTS.validate_repair_authority(repair)
    except CONTRACTS.ContractError as error:
        raise ProjectionError(f"invalid repair authority: {error}") from error
    if "materialization.governed_merge" not in repair["forbidden_adjacent_policy"]:
        raise ProjectionError("repair authority must forbid editing the workaround materialization")
    holes = [h for doc in inputs.values() if isinstance(doc, dict) for h in doc.get("holes", [])]
    if not any(h["id"] == "incremental.authority-locator" and h["status"] == "open" for h in holes):
        raise ProjectionError("authority-locator hole must stay open until the specification is read")
    return roles


def source_query(inputs: dict[str, object], roles: dict[str, str]) -> str:
    edge = inputs[EDGE]
    stage_sources = {m["to"].rsplit(".", 1)[-1]: m for m in edge["mappings"]}
    selections = []
    for column in roles:
        mapping = stage_sources[column]
        origin, name = mapping["from"].rsplit(".", 1)
        alias = "a" if origin.startswith("reference.") else "c"
        selections.append(f"{alias}.{name} AS {column}")
    key = edge["producer"]["identity_join"]
    predicate = edge["history_policy"]["current_version_predicate"].split(".")[-1]
    return (
        f"SELECT {', '.join(selections)} FROM governed.trade_cdc_stage AS c "
        f"JOIN governed.dim_account AS a ON a.account_id = c.account_id AND a.{predicate} "
        f"QUALIFY ROW_NUMBER() OVER (PARTITION BY c.{key} ORDER BY c.cdc_sequence DESC) = 1"
    )


def model_header(name: str, kind: str, columns: dict[str, str] | None = None, audits: tuple[str, ...] = (), depends_on: tuple[str, ...] = ()) -> str:
    parts = [f"  name governed.{name}", f"  kind {kind}", "  dialect duckdb"]
    if columns:
        parts.append("  columns (" + ", ".join(f"{c} {t}" for c, t in columns.items()) + ")")
    if depends_on:
        parts.append(f"  depends_on ({', '.join(depends_on)})")
    if audits:
        parts.append(f"  audits ({', '.join(audits)})")
    return "MODEL (\n" + ",\n".join(parts) + "\n);\n\n"


MATERIALIZATION = '''"""governed_merge: SQLMesh CUSTOM materialization executing a role-derived native MERGE.

Workaround for SQLMesh's missing native DuckDB MERGE (see the Sketch's projection-workaround
section). Classified as sqlmesh_model projection. It carries no policy: the column lists it
receives were derived from mutation roles by the compiler, and it re-checks them here.
"""
from __future__ import annotations

from sqlglot import exp
from sqlmesh import CustomMaterialization
from sqlmesh.core.model import Model


class GovernedMergeMaterialization(CustomMaterialization):
    NAME = "governed_merge"

    def insert(self, table_name: str, query_or_df, model: Model, is_first_insert: bool, render_kwargs, **kwargs) -> None:
        props = model.kind.materialization_properties
        key = props["unique_key"]
        mutable = [c.strip() for c in props.get("mutable_columns", "").split(",") if c.strip()]
        frozen = [c.strip() for c in props.get("frozen_columns", "").split(",") if c.strip()]
        offending = sorted(set(mutable) & set(frozen))
        if offending or key in mutable:
            raise ValueError(f"frozen_from_first_encounter column in matched update: {offending or [key]}")
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
            on=exp.EQ(this=exp.column(key, "tgt"), expression=exp.column(key, "src")),
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


def render_project(inputs: dict[str, object], database: Path) -> tuple[dict[str, str], dict]:
    roles = preflight(inputs)
    surface = GUARD.update_surface(roles)
    types = {t["id"]: t for t in inputs[TYPES]["types"]}
    logical = inputs[LOGICAL]
    physical = {a["name"]: types[a["semantic_type"]]["physical_type"] for a in logical["attributes"]}
    query = source_query(inputs, roles)
    merge = GUARD.build_merge(f"governed.{TARGET_MODEL}", query, roles)
    verdict = GUARD.guard_merge(merge, roles)
    if not verdict.ok:
        raise ProjectionError("compiler-built MERGE failed its own guard: " + json.dumps(verdict.to_dict()))
    merge_sql = merge.sql(dialect="duckdb", pretty=True)

    stage = inputs[STAGE]
    stage_sql = "SELECT " + ", ".join(f"{f['source']} AS {f['name']}" for f in stage["output"]["fields"]) + f" FROM {stage['input']['entity']}"
    frozen_props = ", ".join(surface["frozen"])
    mutable_props = ", ".join(surface["mutable"])
    key = surface["identity"][0]
    binding_columns = {c: physical[c] for c in [key, *surface["frozen"]]}
    files = {
        f"models/trade_cdc_stage.sql": model_header("trade_cdc_stage", "FULL") + exp.maybe_parse(stage_sql, dialect="duckdb").sql(dialect="duckdb", pretty=True) + "\n",
        f"models/{TARGET_MODEL}.sql": model_header(
            TARGET_MODEL,
            "CUSTOM (\n    materialization 'governed_merge',\n    materialization_properties (\n"
            f"      'unique_key' = '{key}',\n      'mutable_columns' = '{mutable_props}',\n      'frozen_columns' = '{frozen_props}'\n    )\n  )",
            {c: physical[c] for c in roles}, ("frozen_keys_bound_once", "not_null_identity"), (f"governed.{BINDING_MODEL}",),
        ) + exp.maybe_parse(query, dialect="duckdb").sql(dialect="duckdb", pretty=True) + "\n",
        f"models/{BINDING_MODEL}.sql": model_header(
            BINDING_MODEL,
            "CUSTOM (\n    materialization 'governed_merge',\n    materialization_properties (\n"
            f"      'unique_key' = '{key}',\n      'mutable_columns' = '',\n      'frozen_columns' = '{frozen_props}'\n    )\n  )",
            binding_columns,
        ) + exp.maybe_parse(
            f"SELECT {', '.join(binding_columns)} FROM ({query}) AS first_encounter", dialect="duckdb"
        ).sql(dialect="duckdb", pretty=True) + "\n",
        "audits/frozen_keys_bound_once.sql": "AUDIT (name frozen_keys_bound_once);\n\n"
            f"SELECT d.{key}, " + ", ".join(f"d.{c} AS current_{c}, b.{c} AS bound_{c}" for c in surface["frozen"]) + "\n"
            f"FROM @this_model AS d JOIN governed.{BINDING_MODEL} AS b ON d.{key} = b.{key}\n"
            "WHERE " + " OR ".join(f"d.{c} IS DISTINCT FROM b.{c}" for c in surface["frozen"]) + "\n",
        "audits/not_null_identity.sql": f"AUDIT (name not_null_identity);\n\nSELECT * FROM @this_model WHERE {key} IS NULL\n",
        "materializations/governed_merge.py": MATERIALIZATION,
        "config.yaml": (
            "gateways:\n  duckdb:\n    connection:\n      type: duckdb\n"
            f"      database: '{database.as_posix()}'\n"
            "default_gateway: duckdb\nmodel_defaults:\n  dialect: duckdb\n  start: '2012-01-01'\n  cron: '@daily'\nlinter:\n  enabled: false\n"
        ),
        "generated/dim_trade_incremental.merge.sql": merge_sql + "\n",
    }
    manifest_extra = {
        "column_roles": roles,
        "update_surface": surface,
        "merge_ast": {"ast_class": merge.__class__.__name__, "sha256": sha256_bytes(merge.sql(dialect="duckdb").encode())},
        "guard": verdict.to_dict(),
        "workaround": {"reason": "SQLMesh DuckDB adapter has no native MERGE (logical_merge; when_matched raises)", "artifact": "materializations/governed_merge.py", "classification": "sqlmesh_model projection", "retire_when": "SQLMesh supports native DuckDB merge with when_matched"},
    }
    return files, manifest_extra


def build_manifest(files: dict[str, str], extra: dict) -> dict:
    hashes = {p: sha256_bytes(c.encode()) for p, c in sorted(files.items())}
    return {
        "schema_version": "projection-manifest-incremental/v1",
        "classification": "replaceable_projection_evidence",
        "compiler_inputs": [{"path": p, "sha256": sha256_bytes((ROOT / p).read_bytes())} for p in GOVERNING_INPUTS],
        "excluded_context": list(FORBIDDEN_CONTEXT),
        "dependencies": {n: importlib.metadata.version(n) for n in ("duckdb", "sqlglot", "sqlmesh")},
        "files": hashes,
        "projection_sha256": sha256_bytes(canonical_json(hashes).encode()),
        "acceptance": {"guard": "guard.dim_trade_incremental.merge_surface", "deterministic_audits": ["frozen_keys_bound_once", "not_null_identity"], "sketch_review": f"required_separately_against_{SKETCH}"},
        **extra,
    }


def compile_projection(output: Path = DEFAULT_OUTPUT, database: Path | None = None, retain: bool = True) -> dict:
    database = database or ROOT / "build/tpcdi-incremental.duckdb"
    files, extra = render_project(load_inputs(), database)
    if output.exists():
        shutil.rmtree(output)
    for relative, content in sorted(files.items()):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest = build_manifest(files, extra)
    (output / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8")
    if retain:
        RETAINED_MANIFEST.write_text(canonical_json(manifest), encoding="utf-8")
    return manifest


def sqlmesh(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), *args], cwd=ROOT, text=True, capture_output=True)


def plan(project: Path, restate: bool = False) -> None:
    args = ["plan", "prod", "--auto-apply", "--no-prompts", "--skip-tests", "--skip-linter"]
    if restate:
        args += ["--restate-model", "governed.trade_cdc_stage"]  # cascades to the key binding and target models
    result = sqlmesh(project, *args)
    if result.returncode or "Failed models" in result.stdout:
        raise ProjectionError(f"SQLMesh plan failed:\n{result.stdout}\n{result.stderr}")


def audit(project: Path) -> subprocess.CompletedProcess:
    return sqlmesh(project, "audit")


def load_counterexample_database(database: Path, fixture: dict, phase: str) -> None:
    """Seed a disposable database from the labeled counterexample fixture. Test scaffolding, not policy."""
    if database.exists():
        database.unlink()
    con = duckdb.connect(str(database))
    try:
        con.execute("CREATE SCHEMA raw; CREATE SCHEMA governed;")
        con.execute("CREATE TABLE governed.dim_account(sk_account_id BIGINT, account_id BIGINT, sk_customer_id BIGINT, effective_from TIMESTAMP, effective_to TIMESTAMP, is_current BOOLEAN)")
        con.execute("CREATE TABLE raw.trade_cdc(cdc_flag VARCHAR, cdc_dsn BIGINT, t_id BIGINT, t_dts TIMESTAMP, t_st_id VARCHAR, t_tt_id VARCHAR, t_is_cash BOOLEAN, t_s_symb VARCHAR, t_qty BIGINT, t_bid_price DECIMAL(8,2), t_ca_id BIGINT, t_exec_name VARCHAR, t_trade_price DECIMAL(8,2), t_chrg DECIMAL(10,2), t_comm DECIMAL(10,2), t_tax DECIMAL(10,2))")
        versions = fixture["dim_account"]
        if phase == "first_encounter":
            versions = [dict(v, is_current=True, effective_to="9999-12-31 00:00:00") for v in versions if not v["is_current"]]
        for v in versions:
            con.execute("INSERT INTO governed.dim_account VALUES (?,?,?,?,?,?)", [v["sk_account_id"], v["account_id"], v["sk_customer_id"], v["effective_from"], v["effective_to"], v["is_current"]])
        rows = fixture["trade_cdc_batch2"] if phase == "rollover" else [
            {"cdc_flag": "I", "cdc_dsn": 0, "t_id": r["trade_id"], "t_dts": "2017-04-10 19:28:01", "t_st_id": r["status_id"], "t_tt_id": "TLS", "t_is_cash": False, "t_s_symb": "AAAAAAAAAAAABFV",
             "t_qty": r["quantity"], "t_bid_price": r["bid_price"], "t_ca_id": 428, "t_exec_name": "990", "t_trade_price": r["trade_price"], "t_chrg": r["fee"], "t_comm": r["commission"], "t_tax": r["tax"]}
            for r in fixture["dim_trade_first_encounter"]]
        for r in rows:
            con.execute("INSERT INTO raw.trade_cdc VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [r[k] for k in ("cdc_flag","cdc_dsn","t_id","t_dts","t_st_id","t_tt_id","t_is_cash","t_s_symb","t_qty","t_bid_price","t_ca_id","t_exec_name","t_trade_price","t_chrg","t_comm","t_tax")])
    finally:
        con.close()


def swap_cdc(database: Path, fixture: dict) -> None:
    """Replace the CDC source and account versions for the rollover phase without touching governed.dim_trade_*."""
    con = duckdb.connect(str(database))
    try:
        con.execute("DELETE FROM raw.trade_cdc")
        for r in fixture["trade_cdc_batch2"]:
            con.execute("INSERT INTO raw.trade_cdc VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [r[k] for k in ("cdc_flag","cdc_dsn","t_id","t_dts","t_st_id","t_tt_id","t_is_cash","t_s_symb","t_qty","t_bid_price","t_ca_id","t_exec_name","t_trade_price","t_chrg","t_comm","t_tax")])
        con.execute("DELETE FROM governed.dim_account")
        for v in fixture["dim_account"]:
            con.execute("INSERT INTO governed.dim_account VALUES (?,?,?,?,?,?)", [v["sk_account_id"], v["account_id"], v["sk_customer_id"], v["effective_from"], v["effective_to"], v["is_current"]])
    finally:
        con.close()


def read_row(database: Path, trade_id: int) -> dict:
    con = duckdb.connect(str(database), read_only=True)
    try:
        cursor = con.execute(f"SELECT * FROM governed.{TARGET_MODEL} WHERE trade_id = ?", [trade_id])
        names = [d[0] for d in cursor.description]
        row = cursor.fetchone()
    finally:
        con.close()
    return dict(zip(names, row)) if row else {}


def run_counterexample(ce_path: Path, workdir: Path) -> dict:
    """Execute the CE end to end: first encounter, then rollover + CMPT. Reads the CE only here, never in compile."""
    ce = json.loads(ce_path.read_text())
    database = workdir / "ce.duckdb"
    project = workdir / "projection"
    load_counterexample_database(database, ce["fixture"], "first_encounter")
    compile_projection(project, database=database, retain=False)
    plan(project)
    before = read_row(database, ce["expected"]["trade_id"])
    swap_cdc(database, ce["fixture"])
    plan(project, restate=True)
    after = read_row(database, ce["expected"]["trade_id"])
    audited = audit(project)
    return {"before": before, "after": after, "audit_stdout": audited.stdout, "audit_ok": audited.returncode == 0 and "0 audit errors" in audited.stdout, "expected": ce["expected"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compile", "guard", "ce"))
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    try:
        if args.command == "compile":
            print(canonical_json(compile_projection()), end="")
        elif args.command == "guard":
            inputs = load_inputs()
            roles = preflight(inputs)
            verdict = GUARD.guard_sql(Path(args.path).read_text(), roles, TARGET_MODEL)
            print(GUARD.diagnosis(verdict, DESCENDANTS))
            return 0 if verdict.ok else 3
        else:
            workdir = ROOT / "build/incremental-ce"
            workdir.mkdir(parents=True, exist_ok=True)
            print(canonical_json(run_counterexample(Path(args.path or "counterexamples/archive/ce-account-428-rollover-v1.json"), workdir)), end="")
    except (ProjectionError, GUARD.GuardError, OSError) as error:
        print(f"projection error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
