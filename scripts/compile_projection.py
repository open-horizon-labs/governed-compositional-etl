#!/usr/bin/env python3
"""Compile the bounded governing inputs into disposable SQLMesh projections."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

import duckdb
from sqlglot import exp, parse_one


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build/issue5-projection"
RETAINED_MANIFEST = ROOT / "projection/manifest-v1.json"
PROFILE_PATH = "contracts/compiler-profile-trade-dim-v1.json"
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
COMPILER_INPUTS = (*GOVERNING_INPUTS, PROFILE_PATH)
FORBIDDEN_CONTEXT = (
    "oracle/",
    "counterexamples/archive/",
    "oracle/fixtures/held-out/",
    "oracle/submissions/held-out/",
)
FORBIDDEN_ROOTS = (
    ROOT / "oracle",
    ROOT / "counterexamples/archive",
)
POLICY_CODE = re.compile(r"^[A-Z0-9]{1,8}$")
EXPECTED_HOLES = {
    "source.incremental-cdc",
    "dim-trade.security-account-keys",
    "dim-trade.batch-id",
    "trade-stage.execution-pricing-policy",
    "dim-trade-consumer.out-of-slice-keys",
    "edge.incremental-update-lifecycle",
}
CONTRACTS_SPEC = importlib.util.spec_from_file_location(
    "governed_contracts", ROOT / "scripts/contracts.py"
)
CONTRACTS = importlib.util.module_from_spec(CONTRACTS_SPEC)
CONTRACTS_SPEC.loader.exec_module(CONTRACTS)
STAGE_SPECS = {
    "contracts/stages/trade-v1.json": {
        "contract_id": "stage.trade.v1",
        "entity": "raw.trade",
        "model": "trade_stage",
        "rule_order": ["trade.structural-copy"],
        "rule": ("tpc-di-1.1.0-2.2.2.17", "copy_with_semantic_type"),
        "outputs": {
            "trade_id": ("t_id", "trade_id"),
            "trade_recorded_at": ("t_dts", "trade_record_timestamp"),
            "status_id": ("t_st_id", "status_id"),
            "trade_type_id": ("t_tt_id", "trade_type_id"),
            "quantity": ("t_qty", "share_quantity"),
            "bid_price": ("t_bid_price", "usd_per_share"),
        },
    },
    "contracts/stages/trade-history-v1.json": {
        "contract_id": "stage.trade_history.v1",
        "entity": "raw.trade_history",
        "model": "trade_history_stage",
        "rule_order": ["trade-history.structural-copy"],
        "rule": ("tpc-di-1.1.0-2.2.2.16", "copy_with_semantic_type"),
        "outputs": {
            "trade_id": ("th_t_id", "trade_id"),
            "status_updated_at": ("th_dts", "status_update_timestamp"),
            "status_id": ("th_st_id", "status_id"),
        },
    },
    "contracts/stages/trade-type-reference-v1.json": {
        "contract_id": "stage.trade_type_reference.v1",
        "entity": "raw.trade_type",
        "model": "trade_type_reference",
        "rule_order": ["trade-type.copy-authorized-reference"],
        "rule": ("tpc-di-1.1.0-4.5.8.2-type", "copy_with_semantic_type"),
        "outputs": {
            "trade_type_id": ("tt_id", "trade_type_id"),
            "type_name": ("tt_name", "trade_type_name"),
            "is_sell": ("tt_is_sell", "boolean_flag"),
            "is_market": ("tt_is_mrkt", "boolean_flag"),
        },
    },
    "contracts/stages/dim-trade-consumer-v1.json": {
        "contract_id": "stage.dim_trade_consumer.v1",
        "entity": "handoff.trade_lifecycle",
        "model": "dim_trade",
        "rule_order": ["dim-trade.copy-authorized-handoff"],
        "rule": ("tpc-di-1.1.0-4.5.8.2", "copy_semantically_typed_handoff"),
        "outputs": {
            "trade_id": ("trade_id", "trade_id"),
            "created_at": ("created_at", "trade_creation_timestamp"),
            "closed_at": ("closed_at", "trade_close_timestamp"),
        },
    },
}


class ProjectionError(ValueError):
    """The generated projection is inconsistent with its governing inputs."""


def canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_input_path(
    relative: str,
    allowed: tuple[str, ...] = GOVERNING_INPUTS,
    root: Path = ROOT,
    require_tracked: bool = True,
) -> Path:
    if relative not in allowed or PurePosixPath(relative).is_absolute():
        raise ProjectionError("compiler input is outside the exact allowlist")
    parts = PurePosixPath(relative).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ProjectionError("compiler input path is not canonical")
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ProjectionError("compiler inputs may not traverse symlinks")
    resolved = current.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ProjectionError("compiler input resolves outside the repository") from error
    for forbidden in FORBIDDEN_ROOTS:
        try:
            resolved.relative_to(forbidden.resolve())
        except ValueError:
            continue
        raise ProjectionError("compiler input resolves into forbidden oracle/CE context")
    if not resolved.is_file():
        raise ProjectionError(f"missing regular governing input: {relative}")
    if require_tracked:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=root,
            capture_output=True,
            check=False,
        )
        if tracked.returncode:
            raise ProjectionError(f"governing input is not tracked: {relative}")
    return resolved


def load_inputs() -> dict[str, object]:
    loaded = {}
    for relative in GOVERNING_INPUTS:
        path = validate_input_path(relative)
        text = path.read_text(encoding="utf-8")
        loaded[relative] = json.loads(text) if path.suffix == ".json" else text
    return loaded


def remove_pointer(document: object, pointer: str) -> None:
    parts = pointer.removeprefix("/").split("/")
    parent = document
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    del parent[parts[-1]]


def normalized_document(document: object, parameters: list[str]) -> bytes:
    if isinstance(document, str):
        if parameters:
            raise ProjectionError("text compiler inputs cannot expose parameters")
        return document.encode()
    normalized = copy.deepcopy(document)
    try:
        for pointer in parameters:
            remove_pointer(normalized, pointer)
    except (KeyError, IndexError, TypeError) as error:
        raise ProjectionError("compiler profile parameter pointer does not resolve") from error
    return json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()


def compare_canonical(
    actual: object,
    expected: object,
    allowed_parameters: set[str],
    pointer: str = "",
) -> None:
    if pointer in allowed_parameters:
        return
    if type(actual) is not type(expected):
        raise ProjectionError(f"canonical governing type changed at {pointer or '/'}")
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ProjectionError(f"canonical governing fields changed at {pointer or '/'}")
        for key in expected:
            escaped = key.replace("~", "~0").replace("/", "~1")
            compare_canonical(actual[key], expected[key], allowed_parameters, f"{pointer}/{escaped}")
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ProjectionError(f"canonical governing list changed at {pointer or '/'}")
        for index, item in enumerate(expected):
            compare_canonical(actual[index], item, allowed_parameters, f"{pointer}/{index}")
    elif actual != expected:
        raise ProjectionError(f"canonical governing value changed at {pointer or '/'}")


def validate_canonical_profile(inputs: dict[str, object]) -> dict:
    profile_file = validate_input_path(PROFILE_PATH, COMPILER_INPUTS)
    staged = subprocess.run(
        ["git", "show", f":{PROFILE_PATH}"], cwd=ROOT, capture_output=True, check=False
    )
    if staged.returncode or staged.stdout != profile_file.read_bytes():
        raise ProjectionError("bounded compiler profile differs from its tracked index version")
    try:
        profile = json.loads(profile_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ProjectionError("bounded compiler profile is invalid JSON") from error
    require_equal(set(profile), {"schema_version", "documents", "parameters"}, "compiler profile fields")
    require_equal(profile["schema_version"], "bounded-compiler-profile/v1", "compiler profile version")
    require_equal(set(profile["documents"]), set(GOVERNING_INPUTS), "compiler profile documents")
    require_equal(
        profile["parameters"],
        {"contracts/edges/trade-history-to-dim-trade-v1.json": [
            "/history_policy/close_statuses",
            "/history_policy/limit_creation_status",
            "/history_policy/market_creation_status",
            "/history_policy/market_trade_types",
        ]},
        "compiler profile parameters",
    )
    for path in GOVERNING_INPUTS:
        indexed = subprocess.run(
            ["git", "show", f":{path}"], cwd=ROOT, capture_output=True, check=False
        )
        if indexed.returncode:
            raise ProjectionError(f"canonical governing input is absent from index: {path}")
        expected = (
            json.loads(indexed.stdout)
            if path.endswith(".json")
            else indexed.stdout.decode()
        )
        compare_canonical(
            inputs[path], expected, set(profile["parameters"].get(path, []))
        )
        digest = sha256_bytes(
            normalized_document(inputs[path], profile["parameters"].get(path, []))
        )
        require_equal(digest, profile["documents"][path], f"canonical document {path}")
    return profile


def require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ProjectionError(f"unsupported governing shape at {label}")


def json_pointer_get(document: object, pointer: str) -> object:
    value = document
    for raw in pointer.removeprefix("/").split("/") if pointer else []:
        token = raw.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def preflight(inputs: dict[str, object]) -> None:
    require_equal(set(inputs), set(GOVERNING_INPUTS), "compiler input set")
    validate_canonical_profile(inputs)
    sketch = inputs["sketches/trade-dim-v1.md"]
    for required in (
        "status: incomplete",
        "## Known rules in order",
        "## Explicit holes",
        "SQLMesh models, SQLGlot ASTs, generated SQL, and DuckDB tables are replaceable projections",
    ):
        if required not in sketch:
            raise ProjectionError("unsupported or incomplete governing Sketch")
    sketch_rules = (
        "1. **Anchor structure only.** Parse the four issue #2 sources according to their declared fields. This step authorizes no classification or default.",
        "2. **Preserve local timestamp meaning.** Map `Trade.T_DTS` to semantic type `trade_record_timestamp`; do not rename it `created_at`.",
        "3. **Interpret named references.** Resolve trade `Type` from `TradeType.TT_NAME` by identifier and `Status` from `StatusType.ST_NAME` by identifier.",
        "4. **Compose lifecycle identity.** Join Trade and TradeHistory by the trade identifier.",
        "5. **Select creation time at the edge.** For market buy/sell (`TMB`, `TMS`), select the `SBMT` history timestamp.",
        "6. **Select close time at the edge.** Select the `CMPT` or `CNCL` history timestamp and assign semantic type `trade_close_timestamp`.",
        "7. **Emit the logical record.** The consumer may copy an already typed lifecycle handoff; it may not reinterpret `trade_record_timestamp` as `trade_creation_timestamp`",
        "8. **Verify twice.** Run deterministic approved-output gates, then review the result against this current Sketch.",
    )
    if any(rule not in sketch for rule in sketch_rules):
        raise ProjectionError("governing Sketch rule order or meaning is unsupported")

    anchors = inputs["evidence/issue-3/source-anchors-v1.json"]
    require_equal(anchors.get("schema_version"), "oracle-source-anchors/v1", "anchors version")
    require_equal(
        anchors.get("authority", {}).get("url"),
        "https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-di_v1.1.0.pdf",
        "anchor authority URL",
    )
    require_equal(
        {rule["locator"] for rule in anchors["authority"]["rules"]},
        {"2.2.2.13, Table 2.2.13", "2.2.2.16, Table 2.2.15", "2.2.2.18, Table 2.2.17", "4.5.8.1", "4.5.8.2"},
        "anchor clauses",
    )

    types_document = inputs["contracts/semantic-types/trade-types-v1.json"]
    types = {item["id"]: item for item in types_document["types"]}
    required_types = {
        "trade_id", "status_id", "status_name", "trade_type_id", "trade_type_name",
        "trade_record_timestamp", "status_update_timestamp", "trade_creation_timestamp",
        "trade_close_timestamp", "share_quantity", "usd_per_share", "boolean_flag",
    }
    require_equal(set(types), required_types, "semantic type registry")
    require_equal(types["trade_record_timestamp"]["physical_type"], "TIMESTAMP", "trade timestamp physical type")
    require_equal(types["trade_creation_timestamp"]["physical_type"], "TIMESTAMP", "creation timestamp physical type")
    if types["trade_record_timestamp"]["semantic_kind"] == types["trade_creation_timestamp"]["semantic_kind"]:
        raise ProjectionError("nominal timestamp distinction collapsed")

    source = inputs["contracts/sources/tpcdi-trade-source-v1.json"]
    expected_source_fields = {
        "raw.status_type": {"st_id": "status_id", "st_name": "status_name"},
        **{
            spec["entity"]: {
                source_name: semantic_type
                for source_name, semantic_type in spec["outputs"].values()
            }
            for spec in STAGE_SPECS.values()
            if spec["entity"].startswith("raw.")
        },
    }
    observed_source_fields = {
        entity["name"]: {
            field["name"]: field["semantic_type"] for field in entity["fields"]
        }
        for entity in source["entities"]
    }
    require_equal(observed_source_fields, expected_source_fields, "source field bindings")
    for authority in source["authority"]:
        try:
            CONTRACTS.require_policy_authority(authority)
        except CONTRACTS.ContractError as error:
            raise ProjectionError(f"invalid named source authority: {error}") from error

    for path, spec in STAGE_SPECS.items():
        contract = inputs[path]
        require_equal(contract["contract_id"], spec["contract_id"], f"{path} contract_id")
        require_equal(contract["input"]["entity"], spec["entity"], f"{path} input entity")
        require_equal(contract["rule_order"], spec["rule_order"], f"{path} rule order")
        require_equal([rule["id"] for rule in contract["rules"]], spec["rule_order"], f"{path} rules")
        require_equal(
            [(rule["authority"], rule["operation"], rule["status"]) for rule in contract["rules"]],
            [(spec["rule"][0], spec["rule"][1], "known")],
            f"{path} governed rule",
        )
        observed = {
            field["name"]: (field["source"], field["semantic_type"])
            for field in contract["output"]["fields"]
        }
        require_equal(observed, spec["outputs"], f"{path} output bindings")
        input_fields = {
            field["name"]: field["semantic_type"] for field in contract["input"]["fields"]
        }
        require_equal(
            input_fields,
            expected_source_fields.get(spec["entity"], {
                name: semantic_type for name, semantic_type in spec["outputs"].values()
            }),
            f"{path} input bindings",
        )

    logical = inputs["contracts/logical-models/dim-trade-v1.json"]
    expected_attributes = {
        "trade_id": "trade_id", "created_at": "trade_creation_timestamp",
        "closed_at": "trade_close_timestamp", "status": "status_name",
        "type": "trade_type_name", "quantity": "share_quantity", "bid_price": "usd_per_share",
    }
    require_equal(
        {item["name"]: item["semantic_type"] for item in logical["attributes"]},
        expected_attributes,
        "logical DimTrade attributes",
    )
    require_equal(logical["identifiers"], ["trade_id"], "logical DimTrade identity")
    require_equal(
        [(item["name"], item["nullable"], item["source_rule"]) for item in logical["attributes"]],
        [
            ("trade_id", False, "tpc-di-1.1.0-4.5.8.2-copy"),
            ("created_at", False, "tpc-di-1.1.0-4.5.8.2-create"),
            ("closed_at", True, "tpc-di-1.1.0-4.5.8.2-close"),
            ("status", False, "tpc-di-1.1.0-4.5.8.2-status"),
            ("type", False, "tpc-di-1.1.0-4.5.8.2-type"),
            ("quantity", False, "tpc-di-1.1.0-4.5.8.2-copy"),
            ("bid_price", False, "tpc-di-1.1.0-4.5.8.2-copy"),
        ],
        "logical attribute order and authority",
    )

    edge = inputs["contracts/edges/trade-history-to-dim-trade-v1.json"]
    require_equal(edge["contract_id"], "edge.trade_history_to_dim_trade.v1", "edge id")
    require_equal(edge["producer"]["contracts"], ["stage.trade.v1", "stage.trade_history.v1"], "edge producers")
    require_equal(edge["producer"]["identity_join"], "trade_id", "edge identity")
    require_equal(edge["consumer"]["contract"], "stage.dim_trade_consumer.v1", "edge consumer")
    expected_mappings = {
        "handoff.trade_lifecycle.trade_id": ("stage.trade.trade_id", "trade_id", "trade_id", "tpc-di-1.1.0-4.5.8.1"),
        "handoff.trade_lifecycle.created_at": ("stage.trade_history.status_updated_at", "status_update_timestamp", "trade_creation_timestamp", "tpc-di-1.1.0-4.5.8.2-create-close"),
        "handoff.trade_lifecycle.closed_at": ("stage.trade_history.status_updated_at", "status_update_timestamp", "trade_close_timestamp", "tpc-di-1.1.0-4.5.8.2-create-close"),
    }
    observed_mappings = {
        item["to"]: (item["from"], item["source_semantic_type"], item["target_semantic_type"], item["authority"])
        for item in edge["mappings"]
    }
    require_equal(observed_mappings, expected_mappings, "edge mappings")
    require_equal(
        [item.get("selector") for item in edge["mappings"]],
        [None, "creation_status_for_trade_type", "close_status"],
        "edge mapping selectors",
    )
    require_equal(edge["rule_order"], [rule["id"] for rule in edge["rules"]], "edge rule order")
    require_equal(
        [(rule["id"], rule["authority"], rule["operation"], rule["status"]) for rule in edge["rules"]],
        [
            ("edge.require-identity", "tpc-di-1.1.0-4.5.8.1", "join_on_trade_id", "known"),
            ("edge.select-creation-status", "tpc-di-1.1.0-4.5.8.2-create-close", "select_status_qualified_history_time", "known"),
            ("edge.select-close-status", "tpc-di-1.1.0-4.5.8.2-create-close", "select_status_qualified_history_time", "known"),
            ("edge.emit-lifecycle-handoff", "tpc-di-1.1.0-4.5.8.2-create-close", "assign_semantic_types", "known"),
        ],
        "edge governed rules",
    )
    policy = edge["history_policy"]
    for key in ("market_trade_types", "close_statuses"):
        if not isinstance(policy[key], list) or not policy[key] or len(policy[key]) != len(set(policy[key])):
            raise ProjectionError(f"{key} must be a nonempty distinct finite enum")
    for key in ("market_creation_status", "limit_creation_status"):
        if not isinstance(policy[key], str):
            raise ProjectionError(f"{key} must be a finite enum code")
    for value in [*policy["market_trade_types"], policy["market_creation_status"], policy["limit_creation_status"], *policy["close_statuses"]]:
        if not POLICY_CODE.fullmatch(value):
            raise ProjectionError("policy code is outside the finite safe enum")

    repair = inputs["contracts/repair-authority/trade-lifecycle-edge-v1.json"]
    require_equal(repair["authority_id"], "repair.trade-lifecycle-edge.v1", "repair id")
    require_equal(repair["allowed_artifacts"], ["sketch.edge.trade_history_to_dim_trade"], "edge repair surface")
    require_equal(repair["active_authority"]["hat"], "data-product-owner", "repair owner")
    require_equal(repair["active_authority"]["scope"], "historical Trade and TradeHistory lifecycle handoff", "repair scope")
    require_equal(
        repair["conflict_behavior"],
        {
            "authority_conflict": "stop_and_adjudicate_under_domain_reviewer_hat",
            "projection_edit": "reject_and_regenerate_from_governing_sketch",
            "raw_or_schema_inference": "reject_as_non_authority",
        },
        "repair conflict behavior",
    )
    if "tpc-di-1.1.0-4.5.8.2-create-close" not in {item["id"] for item in repair["active_authority"]["basis"]}:
        raise ProjectionError("edge repair authority omits create/close rule")
    required_forbidden = {"sketch.stage.trade", "sketch.stage.trade_history", "sketch.stage.dim_trade_consumer"}
    if not required_forbidden <= set(repair["forbidden_adjacent_policy"]):
        raise ProjectionError("edge repair authority exposes a stage surface")
    for authority in repair["active_authority"]["basis"]:
        try:
            CONTRACTS.require_policy_authority(authority)
        except CONTRACTS.ContractError as error:
            raise ProjectionError(f"invalid named repair authority: {error}") from error

    classification = inputs["contracts/artifact-classification-v1.json"]
    classes = {item["id"]: item for item in classification["artifacts"]}
    require_equal(
        set(classes),
        {"sketch", "source_and_target_schema", "sqlmesh_model", "sqlglot_ast", "generated_sql", "duckdb_table", "deterministic_gate", "sketch_review"},
        "artifact classifications",
    )
    for artifact in ("sqlmesh_model", "sqlglot_ast", "generated_sql", "duckdb_table"):
        if classes.get(artifact, {}).get("class") != "projection" or classes[artifact]["policy_authority"]:
            raise ProjectionError("replaceable projection classification was weakened")
    require_equal(classes["deterministic_gate"]["class"], "evidence", "deterministic gate classification")
    require_equal(classes["sketch_review"]["class"], "review", "Sketch review classification")

    holes = []
    for document in inputs.values():
        if isinstance(document, dict):
            holes.extend(document.get("holes", []))
    require_equal(len(holes), len(EXPECTED_HOLES), "bounded open hole count")
    require_equal({hole["id"] for hole in holes}, EXPECTED_HOLES, "bounded open holes")
    for hole in holes:
        require_equal(hole["status"], "open", f"hole {hole['id']} status")
        require_equal(hole["fill_policy"], "named_authority_or_approved_counterexample", f"hole {hole['id']} policy")
        require_equal(set(hole["forbidden_evidence"]), {"raw_data", "target_schema", "projection"}, f"hole {hole['id']} forbidden evidence")


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


def safe_policy_literals(values: list[str]) -> str:
    if not values or any(not POLICY_CODE.fullmatch(value) for value in values):
        raise ProjectionError("policy literal is outside the finite safe enum")
    return ", ".join(
        exp.Literal.string(value).sql(dialect="duckdb") for value in values
    )


def stage_query(contract: dict) -> str:
    selections = ", ".join(
        f"{exp.column(field['source']).sql(dialect='duckdb')} AS "
        f"{exp.to_identifier(field['name']).sql(dialect='duckdb')}"
        for field in contract["output"]["fields"]
    )
    return f"SELECT {selections} FROM {contract['input']['entity']}"


def render_project(
    inputs: dict[str, object], database: Path | None = None
) -> tuple[dict[str, str], dict]:
    preflight(inputs)
    database = database or ROOT / "build/tpcdi.duckdb"
    edge = inputs["contracts/edges/trade-history-to-dim-trade-v1.json"]
    policy = edge["history_policy"]
    market_types = safe_policy_literals(policy["market_trade_types"])
    close_statuses = safe_policy_literals(policy["close_statuses"])
    market_creation = safe_policy_literals([policy["market_creation_status"]])
    limit_creation = safe_policy_literals([policy["limit_creation_status"]])
    mappings = {
        item["selector"]: item for item in edge["mappings"] if "selector" in item
    }
    creation_source = mappings["creation_status_for_trade_type"]["from"].rsplit(".", 1)[-1]
    close_source = mappings["close_status"]["from"].rsplit(".", 1)[-1]
    creation_sql = (
        "MIN(CASE WHEN "
        f"(t.trade_type_id IN ({market_types}) AND h.status_id = {market_creation}) "
        f"OR (t.trade_type_id NOT IN ({market_types}) AND h.status_id = {limit_creation}) "
        f"THEN h.{creation_source} END)"
    )
    close_sql = (
        f"MIN(CASE WHEN h.status_id IN ({close_statuses}) "
        f"THEN h.{close_source} END)"
    )
    creation, creation_ast = policy_expression(creation_sql)
    closed, close_ast = policy_expression(close_sql)

    models = {}
    for path, spec in STAGE_SPECS.items():
        if spec["entity"].startswith("raw."):
            audits_for_stage = (
                ("not_null_trade_id",) if "trade_id" in spec["outputs"] else ()
            )
            models[f"{spec['model']}.sql"] = model(
                spec["model"], stage_query(inputs[path]), audits_for_stage
            )
    source = inputs["contracts/sources/tpcdi-trade-source-v1.json"]
    status_entity = next(
        entity for entity in source["entities"] if entity["name"] == "raw.status_type"
    )
    status_fields = {
        field["semantic_type"]: field["name"] for field in status_entity["fields"]
    }
    models["status_type_reference.sql"] = model(
        "status_type_reference",
        f"SELECT {status_fields['status_id']} AS status_id, "
        f"{status_fields['status_name']} AS status_name FROM {status_entity['name']}",
    )
    identity = edge["producer"]["identity_join"]
    models["trade_lifecycle.sql"] = model(
        "trade_lifecycle",
        f"""SELECT t.{identity}, {creation} AS created_at, {closed} AS closed_at
        FROM governed.trade_stage AS t
        JOIN governed.trade_history_stage AS h ON t.{identity} = h.{identity}
        GROUP BY t.{identity}""",
        ("not_null_trade_id", "valid_lifecycle_order"),
    )
    logical = inputs["contracts/logical-models/dim-trade-v1.json"]
    logical_sources = {
        "trade_id": f"t.{identity}",
        "trade_creation_timestamp": "l.created_at",
        "trade_close_timestamp": "l.closed_at",
        "status_name": "s.status_name",
        "trade_type_name": "tt.type_name",
        "share_quantity": "t.quantity",
        "usd_per_share": "t.bid_price",
    }
    dim_columns = ", ".join(
        f"{logical_sources[item['semantic_type']]} AS {item['name']}"
        for item in logical["attributes"]
    )
    models["dim_trade.sql"] = model(
        "dim_trade",
        f"""SELECT {dim_columns}
        FROM governed.trade_stage AS t
        JOIN governed.trade_lifecycle AS l ON t.{identity} = l.{identity}
        JOIN governed.status_type_reference AS s ON t.status_id = s.status_id
        JOIN governed.trade_type_reference AS tt ON t.trade_type_id = tt.trade_type_id""",
        ("not_null_trade_id", "valid_lifecycle_order"),
    )
    audits = {
        "not_null_trade_id.sql": """AUDIT (name not_null_trade_id);\n\nSELECT * FROM @this_model WHERE trade_id IS NULL\n""",
        "valid_lifecycle_order.sql": """AUDIT (name valid_lifecycle_order);\n\nSELECT * FROM @this_model WHERE created_at IS NULL OR (closed_at IS NOT NULL AND created_at > closed_at)\n""",
    }
    config = (
        "gateways:\n  duckdb:\n    connection:\n      type: duckdb\n"
        f"      database: '{database.as_posix()}'\n"
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


def lineage_manifest(inputs: dict[str, object]) -> list[dict]:
    entries = []
    for path, spec in STAGE_SPECS.items():
        document = inputs[path]
        for index, rule in enumerate(document["rules"]):
            entries.append({
                "source": {"path": path, "pointer": f"/rules/{index}", "authority": rule["authority"]},
                "targets": {"models": [f"governed.{spec['model']}"], "columns": sorted(spec["outputs"]), "expressions": [], "audits": ["not_null_trade_id"] if "trade_id" in spec["outputs"] else []},
            })
    logical_path = "contracts/logical-models/dim-trade-v1.json"
    for index, item in enumerate(inputs[logical_path]["attributes"]):
        entries.append({
            "source": {"path": logical_path, "pointer": f"/attributes/{index}", "authority": item["source_rule"]},
            "targets": {"models": ["governed.dim_trade"], "columns": [item["name"]], "expressions": [], "audits": ["not_null_trade_id"] if item["name"] == "trade_id" else []},
        })
    edge_path = "contracts/edges/trade-history-to-dim-trade-v1.json"
    edge = inputs[edge_path]
    for index, rule in enumerate(edge["rules"]):
        expression = {"edge.select-creation-status": ["trade_creation_timestamp"], "edge.select-close-status": ["trade_close_timestamp"]}.get(rule["id"], [])
        entries.append({
            "source": {"path": edge_path, "pointer": f"/rules/{index}", "authority": rule["authority"]},
            "targets": {"models": ["governed.trade_lifecycle"], "columns": [], "expressions": expression, "audits": ["valid_lifecycle_order"]},
        })
    for index, mapping in enumerate(edge["mappings"]):
        column = mapping["to"].rsplit(".", 1)[-1]
        expression = {"created_at": ["trade_creation_timestamp"], "closed_at": ["trade_close_timestamp"]}.get(column, [])
        entries.append({
            "source": {"path": edge_path, "pointer": f"/mappings/{index}", "authority": mapping["authority"]},
            "targets": {"models": ["governed.trade_lifecycle", "governed.dim_trade"], "columns": [column], "expressions": expression, "audits": ["valid_lifecycle_order"] if expression else ["not_null_trade_id"]},
        })
    for key, expressions in (
        ("market_trade_types", ["trade_creation_timestamp"]),
        ("market_creation_status", ["trade_creation_timestamp"]),
        ("limit_creation_status", ["trade_creation_timestamp"]),
        ("close_statuses", ["trade_close_timestamp"]),
    ):
        entries.append({
            "source": {"path": edge_path, "pointer": f"/history_policy/{key}", "authority": "tpc-di-1.1.0-4.5.8.2-create-close"},
            "targets": {"models": ["governed.trade_lifecycle"], "columns": ["created_at" if expressions == ["trade_creation_timestamp"] else "closed_at"], "expressions": expressions, "audits": ["valid_lifecycle_order"]},
        })
    source_path = "contracts/sources/tpcdi-trade-source-v1.json"
    model_by_clause = {"2.2.2.13": "status_type_reference", "2.2.2.16": "trade_history_stage", "2.2.2.17": "trade_stage", "2.2.2.18": "trade_type_reference"}
    for index, authority in enumerate(inputs[source_path]["authority"]):
        clause = authority["id"].rsplit("-", 1)[-1]
        entries.append({
            "source": {"path": source_path, "pointer": f"/authority/{index}", "authority": authority["id"]},
            "targets": {"models": [f"governed.{model_by_clause[clause]}"], "columns": [], "expressions": [], "audits": []},
        })
    return sorted(entries, key=lambda item: (item["source"]["path"], item["source"]["pointer"]))


def project_hashes(files: dict[str, str]) -> dict[str, str]:
    return {path: sha256_bytes(content.encode()) for path, content in sorted(files.items())}


def build_manifest(inputs: dict[str, object], files: dict[str, str], expressions: dict) -> dict:
    file_hashes = project_hashes(files)
    projection_hash = sha256_bytes(canonical_json(file_hashes).encode())
    return {
        "schema_version": "projection-manifest/v1",
        "classification": "replaceable_projection_evidence",
        "compiler_inputs": [{"path": path, "sha256": sha256_bytes((ROOT / path).read_bytes())} for path in COMPILER_INPUTS],
        "excluded_context": list(FORBIDDEN_CONTEXT),
        "dependencies": {name: importlib.metadata.version(name) for name in ("duckdb", "sqlglot", "sqlmesh")},
        "files": file_hashes,
        "policy_expressions": expressions,
        "lineage": lineage_manifest(inputs),
        "acceptance": {"deterministic_audits": ["not_null_trade_id", "valid_lifecycle_order"], "sketch_review": "required_separately_against_sketches/trade-dim-v1.md"},
        "arms": {arm: {"projection_sha256": projection_hash} for arm in ARMS},
    }


def compile_projection(output: Path = DEFAULT_OUTPUT, retain: bool = True, database: Path | None = None) -> dict:
    inputs = load_inputs()
    files, expressions = render_project(inputs, database)
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
    manifest = build_manifest(inputs, files, expressions)
    if retain:
        RETAINED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        RETAINED_MANIFEST.write_text(canonical_json(manifest), encoding="utf-8")
    return manifest


def verify_manifest(manifest: dict, output: Path = DEFAULT_OUTPUT, database: Path | None = None) -> None:
    inputs = load_inputs()
    files, expressions = render_project(inputs, database)
    expected_manifest = build_manifest(inputs, files, expressions)
    if manifest != expected_manifest:
        raise ProjectionError("manifest differs from independently recomputed governing projection")
    expected_files = project_hashes(files)
    canonical = output / "canonical"
    observed_canonical = {path.relative_to(canonical).as_posix(): sha256_bytes(path.read_bytes()) for path in sorted(canonical.rglob("*")) if path.is_file()}
    if observed_canonical != expected_files:
        raise ProjectionError("canonical projection bytes differ from recomputed projection")
    for arm in ARMS:
        project = output / "arms" / arm
        observed = {
            path.relative_to(project).as_posix(): sha256_bytes(path.read_bytes())
            for path in sorted(project.rglob("*"))
            if path.is_file()
        }
        if observed != expected_files:
            raise ProjectionError(f"{arm} projection bytes differ from recomputed projection")


def clone_raw_substrate(target: Path) -> None:
    source = ROOT / "build/tpcdi.duckdb"
    if target.exists():
        target.unlink()
    connection = duckdb.connect(str(target))
    try:
        connection.execute(f"ATTACH '{source.as_posix()}' AS source_db (READ_ONLY)")
        connection.execute("CREATE SCHEMA raw")
        for table in ("trade", "trade_history", "trade_type", "status_type"):
            connection.execute(f"CREATE TABLE raw.{table} AS SELECT * FROM source_db.raw.{table}")
        connection.execute("DETACH source_db")
    finally:
        connection.close()


def execute_projection(
    output: Path = DEFAULT_OUTPUT,
    database: Path | None = None,
    retain: bool = True,
) -> dict:
    database = database or ROOT / "build/tpcdi.duckdb"
    manifest = compile_projection(output, retain=retain, database=database)
    verify_manifest(manifest, output, database)
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
    connection = duckdb.connect(str(database), read_only=True)
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
        "database": database.relative_to(ROOT).as_posix() if database.is_relative_to(ROOT) else str(database),
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
    if retain:
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
