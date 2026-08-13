#!/usr/bin/env python3
"""Compile the bounded governing inputs into disposable SQLMesh projections."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

import duckdb
from sqlglot import exp, parse_one


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build/issue5-projection"
RETAINED_MANIFEST = ROOT / "projection/manifest-v1.json"
ARMS = ("native", "stage_local_cess", "compositional_cess")
GOVERNING_INPUTS = (
    "sketches/trade-dim-v1.md",
    "evidence/issue-3/source-anchors-v1.json",
    "contracts/sources/tpcdi-trade-source-v1.json",
    "contracts/logical-models/dim-trade-v1.json",
    "contracts/semantic-types/trade-types-v1.json",
    "contracts/stages/trade-v1.json",
    "contracts/stages/trade-history-v1.json",
    "contracts/stages/trade-type-reference-v1.json",
    "contracts/stages/dim-trade-consumer-v1.json",
    "contracts/edges/trade-history-to-dim-trade-v1.json",
    "contracts/repair-authority/trade-lifecycle-edge-v1.json",
    "contracts/artifact-classification-v1.json",
)
FORBIDDEN_CONTEXT = (
    "oracle/",
    "counterexamples/archive/",
    "oracle/fixtures/held-out/",
    "oracle/submissions/held-out/",
)


class ProjectionError(ValueError):
    """The generated projection is inconsistent with its governing inputs."""


def canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_inputs() -> dict[str, object]:
    loaded = {}
    for relative in GOVERNING_INPUTS:
        if relative.startswith(FORBIDDEN_CONTEXT):
            raise ProjectionError("compiler input allowlist contains forbidden context")
        path = ROOT / relative
        if not path.is_file():
            raise ProjectionError(f"missing governing input: {relative}")
        text = path.read_text(encoding="utf-8")
        loaded[relative] = json.loads(text) if path.suffix == ".json" else text
    return loaded


def model(name: str, query: str, audits: tuple[str, ...] = ()) -> str:
    audit_sql = f",\n  audits ({', '.join(audits)})" if audits else ""
    return (
        "MODEL (\n"
        f"  name governed.{name},\n"
        "  kind FULL,\n"
        "  dialect duckdb"
        f"{audit_sql}\n"
        ");\n\n"
        f"{parse_one(query, dialect='duckdb').sql(dialect='duckdb', pretty=True)}\n"
    )


def policy_expression(sql: str) -> tuple[str, dict]:
    expression = parse_one(sql, dialect="duckdb")
    if not isinstance(expression, exp.Expression):
        raise ProjectionError("SQLGlot did not produce an expression AST")
    rendered = expression.sql(dialect="duckdb")
    return rendered, {
        "ast_class": expression.__class__.__name__,
        "rendered_sql": rendered,
        "sha256": sha256_bytes(rendered.encode()),
    }


def render_project(inputs: dict[str, object]) -> tuple[dict[str, str], dict]:
    edge = inputs["contracts/edges/trade-history-to-dim-trade-v1.json"]
    policy = edge["history_policy"]
    market_types = ", ".join(f"'{value}'" for value in policy["market_trade_types"])
    close_statuses = ", ".join(f"'{value}'" for value in policy["close_statuses"])
    creation_sql = (
        "MIN(CASE WHEN "
        f"(t.trade_type_id IN ({market_types}) AND h.status_id = '{policy['market_creation_status']}') "
        f"OR (t.trade_type_id NOT IN ({market_types}) AND h.status_id = '{policy['limit_creation_status']}') "
        "THEN h.status_updated_at END)"
    )
    close_sql = (
        f"MIN(CASE WHEN h.status_id IN ({close_statuses}) "
        "THEN h.status_updated_at END)"
    )
    creation, creation_ast = policy_expression(creation_sql)
    closed, close_ast = policy_expression(close_sql)

    models = {
        "trade_stage.sql": model(
            "trade_stage",
            """SELECT t_id AS trade_id, t_dts AS trade_recorded_at,
            t_st_id AS status_id, t_tt_id AS trade_type_id,
            t_qty AS quantity, t_bid_price AS bid_price FROM raw.trade""",
            ("not_null_trade_id",),
        ),
        "trade_history_stage.sql": model(
            "trade_history_stage",
            """SELECT th_t_id AS trade_id, th_dts AS status_updated_at,
            th_st_id AS status_id FROM raw.trade_history""",
            ("not_null_trade_id",),
        ),
        "trade_type_reference.sql": model(
            "trade_type_reference",
            """SELECT tt_id AS trade_type_id, tt_name AS type_name,
            tt_is_sell AS is_sell, tt_is_mrkt AS is_market FROM raw.trade_type""",
        ),
        "status_type_reference.sql": model(
            "status_type_reference",
            "SELECT st_id AS status_id, st_name AS status_name FROM raw.status_type",
        ),
        "trade_lifecycle.sql": model(
            "trade_lifecycle",
            f"""SELECT t.trade_id, {creation} AS created_at, {closed} AS closed_at
            FROM governed.trade_stage AS t
            JOIN governed.trade_history_stage AS h ON t.trade_id = h.trade_id
            GROUP BY t.trade_id""",
            ("not_null_trade_id", "valid_lifecycle_order"),
        ),
        "dim_trade.sql": model(
            "dim_trade",
            """SELECT t.trade_id, l.created_at, l.closed_at,
            s.status_name AS status, tt.type_name AS type,
            t.quantity, t.bid_price
            FROM governed.trade_stage AS t
            JOIN governed.trade_lifecycle AS l ON t.trade_id = l.trade_id
            JOIN governed.status_type_reference AS s ON t.status_id = s.status_id
            JOIN governed.trade_type_reference AS tt ON t.trade_type_id = tt.trade_type_id""",
            ("not_null_trade_id", "valid_lifecycle_order"),
        ),
    }
    audits = {
        "not_null_trade_id.sql": """AUDIT (name not_null_trade_id);\n\nSELECT * FROM @this_model WHERE trade_id IS NULL\n""",
        "valid_lifecycle_order.sql": """AUDIT (name valid_lifecycle_order);\n\nSELECT * FROM @this_model WHERE created_at IS NULL OR (closed_at IS NOT NULL AND created_at > closed_at)\n""",
    }
    config = (
        "gateways:\n  duckdb:\n    connection:\n      type: duckdb\n"
        f"      database: '{(ROOT / 'build/tpcdi.duckdb').as_posix()}'\n"
        "default_gateway: duckdb\nmodel_defaults:\n  dialect: duckdb\n"
        "  start: '2012-01-01'\n  cron: '@daily'\n"
        "linter:\n  enabled: false\n"
    )
    files = {f"models/{name}": value for name, value in models.items()}
    files.update({f"audits/{name}": value for name, value in audits.items()})
    files["config.yaml"] = config
    expression_manifest = {
        "trade_creation_timestamp": creation_ast,
        "trade_close_timestamp": close_ast,
    }
    return files, expression_manifest


def lineage_manifest(expression_manifest: dict) -> list[dict]:
    return [
        {
            "authority": ["tpc-di-1.1.0-2.2.2.17"],
            "models": ["governed.trade_stage"],
            "expressions": [],
            "audits": ["not_null_trade_id"],
        },
        {
            "authority": ["tpc-di-1.1.0-2.2.2.16"],
            "models": ["governed.trade_history_stage"],
            "expressions": [],
            "audits": ["not_null_trade_id"],
        },
        {
            "authority": [
                "tpc-di-1.1.0-2.2.2.18",
                "tpc-di-1.1.0-4.5.8.2-type",
            ],
            "models": ["governed.trade_type_reference", "governed.dim_trade"],
            "expressions": [],
            "audits": [],
        },
        {
            "authority": [
                "tpc-di-1.1.0-2.2.2.13",
                "tpc-di-1.1.0-4.5.8.2-status",
            ],
            "models": ["governed.status_type_reference", "governed.dim_trade"],
            "expressions": [],
            "audits": [],
        },
        {
            "authority": ["tpc-di-1.1.0-4.5.8.2-copy"],
            "models": ["governed.dim_trade"],
            "expressions": [],
            "audits": ["not_null_trade_id"],
        },
        {
            "authority": ["tpc-di-1.1.0-4.5.8.1", "tpc-di-1.1.0-4.5.8.2-create-close"],
            "models": ["governed.trade_lifecycle", "governed.dim_trade"],
            "expressions": sorted(expression_manifest),
            "audits": ["valid_lifecycle_order"],
        },
    ]


def compile_projection(output: Path = DEFAULT_OUTPUT, retain: bool = True) -> dict:
    inputs = load_inputs()
    files, expressions = render_project(inputs)
    canonical = output / "canonical"
    if output.exists():
        shutil.rmtree(output)
    canonical.mkdir(parents=True)
    for relative, content in sorted(files.items()):
        path = canonical / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for arm in ARMS:
        shutil.copytree(canonical, output / "arms" / arm)
    file_hashes = {
        relative: sha256_bytes(content.encode()) for relative, content in sorted(files.items())
    }
    manifest = {
        "schema_version": "projection-manifest/v1",
        "classification": "replaceable_projection_evidence",
        "compiler_inputs": [
            {"path": path, "sha256": sha256_bytes((ROOT / path).read_bytes())}
            for path in GOVERNING_INPUTS
        ],
        "excluded_context": list(FORBIDDEN_CONTEXT),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("duckdb", "sqlglot", "sqlmesh")
        },
        "files": file_hashes,
        "policy_expressions": expressions,
        "lineage": lineage_manifest(expressions),
        "acceptance": {
            "deterministic_audits": ["not_null_trade_id", "valid_lifecycle_order"],
            "sketch_review": "required_separately_against_sketches/trade-dim-v1.md",
        },
        "arms": {
            arm: {"projection_sha256": sha256_bytes(canonical_json(file_hashes).encode())}
            for arm in ARMS
        },
    }
    if retain:
        RETAINED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        RETAINED_MANIFEST.write_text(canonical_json(manifest), encoding="utf-8")
    return manifest


def verify_manifest(manifest: dict, output: Path = DEFAULT_OUTPUT) -> None:
    if any(item["path"].startswith(FORBIDDEN_CONTEXT) for item in manifest["compiler_inputs"]):
        raise ProjectionError("fresh projection used forbidden CE/oracle context")
    arm_hashes = {details["projection_sha256"] for details in manifest["arms"].values()}
    if len(arm_hashes) != 1:
        raise ProjectionError("experiment arms do not start from equivalent projections")
    authorities = {authority for entry in manifest["lineage"] for authority in entry["authority"]}
    if "tpc-di-1.1.0-4.5.8.2-create-close" not in authorities:
        raise ProjectionError("manifest omits governed lifecycle authority")
    if manifest["acceptance"]["sketch_review"] == "":
        raise ProjectionError("deterministic audits cannot replace Sketch review")
    expected_files = manifest["files"]
    for arm in ARMS:
        project = output / "arms" / arm
        observed = {
            path.relative_to(project).as_posix(): sha256_bytes(path.read_bytes())
            for path in sorted(project.rglob("*"))
            if path.is_file()
        }
        if observed != expected_files:
            raise ProjectionError(f"{arm} projection bytes differ from the manifest")


def execute_projection(output: Path = DEFAULT_OUTPUT) -> dict:
    manifest = compile_projection(output)
    verify_manifest(manifest, output)
    project = output / "arms/compositional_cess"
    result = subprocess.run(
        [
            str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), "plan", "prod",
            "--auto-apply", "--no-prompts", "--skip-tests", "--skip-linter",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise ProjectionError(f"SQLMesh execution failed:\n{result.stdout}\n{result.stderr}")
    audit = subprocess.run(
        [str(ROOT / ".venv/bin/sqlmesh"), "-p", str(project), "audit"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if audit.returncode or "0 audit errors" not in audit.stdout:
        raise ProjectionError(f"SQLMesh audits failed:\n{audit.stdout}\n{audit.stderr}")
    connection = duckdb.connect(str(ROOT / "build/tpcdi.duckdb"), read_only=True)
    try:
        raw_count = connection.execute("SELECT count(*) FROM raw.trade").fetchone()[0]
        row = connection.execute(
            "SELECT count(*), count(DISTINCT trade_id) FROM governed.dim_trade"
        ).fetchone()
        selected = connection.execute(
            "SELECT created_at, closed_at, status, type FROM governed.dim_trade WHERE trade_id = 0"
        ).fetchone()
    finally:
        connection.close()
    if row != (raw_count, raw_count) or selected is None:
        raise ProjectionError("persistent DimTrade projection failed count or identity checks")
    evidence = {
        "schema_version": "sqlmesh-execution/v1",
        "database": "build/tpcdi.duckdb",
        "dim_trade_rows": row[0],
        "distinct_trade_ids": row[1],
        "audit_errors": 0,
        "trade_id_0": {
            "created_at": selected[0].isoformat(),
            "closed_at": selected[1].isoformat(),
            "status": selected[2],
            "type": selected[3],
        },
    }
    evidence_path = ROOT / "evidence/issue-5/sqlmesh-execution-v1.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(canonical_json(evidence), encoding="utf-8")
    return evidence


def fresh_rebuild() -> dict:
    first = compile_projection(DEFAULT_OUTPUT)
    if DEFAULT_OUTPUT.resolve() != (ROOT / "build/issue5-projection").resolve():
        raise ProjectionError("refusing to delete an unexpected projection directory")
    shutil.rmtree(DEFAULT_OUTPUT)
    second = compile_projection(DEFAULT_OUTPUT)
    if first != second:
        raise ProjectionError("fresh projection is not byte/logically equivalent")
    verify_manifest(second, DEFAULT_OUTPUT)
    return second


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compile", "verify", "execute", "fresh"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "execute":
            result = execute_projection()
        elif args.command == "fresh":
            result = fresh_rebuild()
        else:
            result = compile_projection(DEFAULT_OUTPUT, retain=args.command == "compile")
            verify_manifest(result, DEFAULT_OUTPUT)
    except (ProjectionError, OSError, subprocess.SubprocessError) as error:
        print(f"projection error: {error}", file=sys.stderr)
        return 2
    print(canonical_json(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
