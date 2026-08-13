#!/usr/bin/env python3
"""Validate governed contracts and reproduce the issue #4 edge adjudication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError:  # pragma: no cover - exercised by the documented environment check
    Draft202012Validator = None
    SchemaError = ValidationError = Exception


ROOT = Path(__file__).resolve().parents[1]
TPC_RULE = re.compile(r"^tpc-di-1\.1\.0-[a-z0-9.-]+$")
HOLE_KEYS = {
    "id",
    "question",
    "owner_hat",
    "status",
    "fill_policy",
    "forbidden_evidence",
}
FORBIDDEN_HOLE_EVIDENCE = {"raw_data", "target_schema", "projection"}
PROJECTIONS = {"sqlmesh_model", "sqlglot_ast", "generated_sql", "duckdb_table"}


class ContractError(ValueError):
    """A governing contract or its evidence is inconsistent."""


def load_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as source:
            value = json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"could not load {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain an object")
    return value


def canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def exact_keys(value: object, keys: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ContractError(f"{name} keys must be {sorted(keys)}; got {actual}")
    return value


def nonempty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{name} must be a non-empty string")
    return value


def validate_hole(hole: object) -> dict:
    value = exact_keys(hole, HOLE_KEYS, "hole")
    nonempty_string(value["id"], "hole.id")
    nonempty_string(value["question"], "hole.question")
    nonempty_string(value["owner_hat"], "hole.owner_hat")
    if value["status"] != "open":
        raise ContractError("declared holes must remain open")
    if value["fill_policy"] != "named_authority_or_approved_counterexample":
        raise ContractError("a hole may be filled only by named authority or approval")
    if set(value["forbidden_evidence"]) != FORBIDDEN_HOLE_EVIDENCE:
        raise ContractError(
            "holes must explicitly forbid raw data, target schema, and projection inference"
        )
    return value


def require_policy_authority(authority: object) -> dict:
    value = exact_keys(authority, {"kind", "id", "source", "locator"}, "authority")
    if value["kind"] == "tpc_di_rule":
        if not TPC_RULE.fullmatch(value["id"]):
            raise ContractError("TPC-DI policy authority must name a 1.1.0 rule")
    elif value["kind"] == "approved_decision":
        if not value["source"].startswith(".oh/"):
            raise ContractError("approved policy authority must name a repository decision")
    elif value["kind"] == "approved_counterexample":
        if not value["source"].startswith("counterexamples/archive/"):
            raise ContractError(
                "approved counterexample authority must name the complete CE archive"
            )
    else:
        raise ContractError(
            "raw data, target structure, and projections cannot fill policy holes"
        )
    return value


def semantic_type_compatible(actual: str, required: str) -> bool:
    """Local compatibility is nominal, not physical-type equivalence."""
    return actual == required


def validate_semantic_mapping(mapping: dict, semantic_types: dict[str, dict]) -> None:
    source_type = mapping.get("source_semantic_type")
    target_type = mapping.get("target_semantic_type")
    if source_type not in semantic_types or target_type not in semantic_types:
        raise ContractError("edge mapping references an unknown semantic type")
    if source_type != target_type and not TPC_RULE.fullmatch(
        mapping.get("authority", "")
    ):
        raise ContractError(
            "semantic type conversion at an edge requires named business authority"
        )


def validate_repair_authority(record: dict) -> None:
    if record.get("schema_version") != "repair-authority/v1":
        raise ContractError("repair authority version is invalid")
    allowed = set(record.get("allowed_artifacts", []))
    forbidden = set(record.get("forbidden_adjacent_policy", []))
    if not allowed or allowed & forbidden:
        raise ContractError("repair authority must be non-empty and non-overlapping")
    if not all(item.startswith("sketch.") for item in allowed):
        raise ContractError("repair authority may allow only governing Sketch artifacts")
    behavior = record.get("conflict_behavior", {})
    if behavior != {
        "authority_conflict": "stop_and_adjudicate_under_domain_reviewer_hat",
        "projection_edit": "reject_and_regenerate_from_governing_sketch",
        "raw_or_schema_inference": "reject_as_non_authority",
    }:
        raise ContractError("repair conflict behavior is incomplete")
    active = exact_keys(
        record.get("active_authority"), {"hat", "scope", "basis"}, "active authority"
    )
    if not active["hat"] or not active["scope"] or not active["basis"]:
        raise ContractError("repair authority must name the active conceptual hat and basis")


def validate_projection_classification(classification: dict) -> None:
    classes = {item["id"]: item for item in classification.get("artifacts", [])}
    for projection in PROJECTIONS:
        item = classes.get(projection)
        if not item or item.get("class") != "projection" or item.get(
            "policy_authority"
        ):
            raise ContractError(f"{projection} must remain a non-governing projection")


def validate_schema_files() -> dict[str, object]:
    if Draft202012Validator is None:
        raise ContractError(
            "Draft 2020-12 validation requires the pinned development dependencies"
        )
    paths = sorted((ROOT / "contracts/schema").glob("*.schema.json"))
    expected = {
        "source-v1.schema.json",
        "logical-model-v1.schema.json",
        "semantic-types-v1.schema.json",
        "stage-contract-v1.schema.json",
        "edge-contract-v1.schema.json",
        "repair-authority-v1.schema.json",
    }
    if {path.name for path in paths} != expected:
        raise ContractError("contract schema set is incomplete")
    ids = set()
    schemas = {}
    for path in paths:
        schema = load_json(path)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ContractError(f"{path.name} must declare JSON Schema 2020-12")
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            raise ContractError(f"{path.name} must define a closed object")
        schema_id = nonempty_string(schema.get("$id"), f"{path.name}.$id")
        if schema_id in ids:
            raise ContractError("contract schema ids must be unique")
        ids.add(schema_id)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            raise ContractError(f"{path.name} is not a valid Draft 2020-12 schema: {error.message}") from error
        schemas[path.name] = schema
    return schemas


def validate_instance(schema: dict, instance: dict, name: str) -> None:
    try:
        Draft202012Validator(schema).validate(instance)
    except ValidationError as error:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ContractError(f"{name} fails its schema at {location}: {error.message}") from error


def validate_bundle() -> dict:
    schemas = validate_schema_files()
    types_document = load_json(
        ROOT / "contracts/semantic-types/trade-types-v1.json"
    )
    validate_instance(
        schemas["semantic-types-v1.schema.json"],
        types_document,
        "semantic type registry",
    )
    if types_document.get("schema_version") != "semantic-types/v1":
        raise ContractError("semantic type registry version is invalid")
    semantic_types = {}
    for item in types_document.get("types", []):
        type_id = nonempty_string(item.get("id"), "semantic type id")
        if type_id in semantic_types:
            raise ContractError("semantic type ids must be unique")
        semantic_types[type_id] = item
    if not semantic_types:
        raise ContractError("semantic type registry must not be empty")

    source = load_json(ROOT / "contracts/sources/tpcdi-trade-source-v1.json")
    validate_instance(schemas["source-v1.schema.json"], source, "source descriptor")
    for authority in source.get("authority", []):
        require_policy_authority(authority)
    holes = []
    holes.extend(validate_hole(hole) for hole in source.get("holes", []))
    for entity in source.get("entities", []):
        if not entity.get("grain") or not entity.get("identifiers"):
            raise ContractError("every source entity needs grain and identifiers")
        for field in entity.get("fields", []):
            if field.get("semantic_type") not in semantic_types:
                raise ContractError("source field references an unknown semantic type")

    logical = load_json(ROOT / "contracts/logical-models/dim-trade-v1.json")
    validate_instance(
        schemas["logical-model-v1.schema.json"], logical, "logical model"
    )
    holes.extend(validate_hole(hole) for hole in logical.get("holes", []))
    for attribute in logical.get("attributes", []):
        if attribute.get("semantic_type") not in semantic_types:
            raise ContractError("logical attribute references an unknown semantic type")
        nonempty_string(attribute.get("source_rule"), "logical attribute source_rule")

    stage_documents = {}
    for path in sorted((ROOT / "contracts/stages").glob("*.json")):
        contract = load_json(path)
        validate_instance(
            schemas["stage-contract-v1.schema.json"], contract, str(path.relative_to(ROOT))
        )
        if contract.get("schema_version") != "stage-contract/v1":
            raise ContractError(f"stage contract version is invalid: {path.name}")
        contract_id = nonempty_string(contract.get("contract_id"), "stage contract id")
        if contract_id in stage_documents:
            raise ContractError("stage contract ids must be unique")
        stage_documents[contract_id] = contract
        holes.extend(validate_hole(hole) for hole in contract.get("holes", []))
        rule_order = contract.get("rule_order", [])
        for rule in contract.get("rules", []):
            if rule.get("id") not in rule_order or not TPC_RULE.fullmatch(
                rule.get("authority", "")
            ):
                raise ContractError("stage rules need ordered, named TPC-DI authority")
        for field in contract.get("output", {}).get("fields", []):
            if field.get("semantic_type") not in semantic_types:
                raise ContractError("stage output references an unknown semantic type")

    edge = load_json(ROOT / "contracts/edges/trade-history-to-dim-trade-v1.json")
    validate_instance(schemas["edge-contract-v1.schema.json"], edge, "edge contract")
    if edge.get("schema_version") != "edge-contract/v1":
        raise ContractError("edge contract version is invalid")
    holes.extend(validate_hole(hole) for hole in edge.get("holes", []))
    for contract_id in edge.get("producer", {}).get("contracts", []):
        if contract_id not in stage_documents:
            raise ContractError("edge producer references an unknown stage contract")
    if edge.get("consumer", {}).get("contract") not in stage_documents:
        raise ContractError("edge consumer references an unknown stage contract")
    edge_rule_ids = {rule.get("id") for rule in edge.get("rules", [])}
    if not edge_rule_ids <= set(edge.get("rule_order", [])):
        raise ContractError("edge rule order omits a governed rule")
    for rule in edge.get("rules", []):
        if not TPC_RULE.fullmatch(rule.get("authority", "")):
            raise ContractError("edge rules need named TPC-DI authority")
    for mapping in edge.get("mappings", []):
        validate_semantic_mapping(mapping, semantic_types)

    repair_records = []
    for path in sorted((ROOT / "contracts/repair-authority").glob("*.json")):
        record = load_json(path)
        validate_instance(
            schemas["repair-authority-v1.schema.json"],
            record,
            str(path.relative_to(ROOT)),
        )
        validate_repair_authority(record)
        repair_records.append(record)

    classification = load_json(ROOT / "contracts/artifact-classification-v1.json")
    validate_projection_classification(classification)

    adjudication = adjudicate_candidate(stage_documents, edge, semantic_types)
    retained = load_json(
        ROOT / "evidence/issue-4/candidate-edge-adjudication-v1.json"
    )
    if retained != adjudication:
        raise ContractError("retained candidate adjudication does not match executable checks")

    canonical_paths = list((ROOT / "contracts").rglob("*.json")) + list(
        (ROOT / "evidence/issue-4").glob("*.json")
    )
    for path in canonical_paths:
        value = load_json(path)
        if path.read_text(encoding="utf-8") != canonical_json(value):
            raise ContractError(f"{path.relative_to(ROOT)} is not canonical JSON")
    return {
        "adjudication": adjudication["decision"],
        "contracts_verified": len(stage_documents) + 3,
        "holes_open": len(holes),
        "projection_classes_verified": len(PROJECTIONS),
        "repair_authorities_verified": len(repair_records),
        "schemas_verified": len(schemas),
        "semantic_types_verified": len(semantic_types),
    }


def apply_stage_mapping(contract: dict, source: dict) -> dict:
    return {
        field["name"]: source[field["source"]]
        for field in contract["output"]["fields"]
    }


def validate_consumer(contract: dict, handoff: dict, output: dict) -> bool:
    expected = apply_stage_mapping(contract, handoff)
    if expected != output:
        return False
    created = output.get("created_at")
    closed = output.get("closed_at")
    return closed is None or created <= closed


def expected_edge_handoff(edge: dict, trade: dict, history: list[dict]) -> dict:
    policy = edge["history_policy"]
    creation_status = (
        policy["market_creation_status"]
        if trade["trade_type_id"] in policy["market_trade_types"]
        else policy["limit_creation_status"]
    )
    created = [
        row["status_updated_at"] for row in history if row["status_id"] == creation_status
    ]
    closed = [
        row["status_updated_at"]
        for row in history
        if row["status_id"] in policy["close_statuses"]
    ]
    if len(created) != 1 or len(closed) != 1:
        raise ContractError("candidate history does not satisfy edge status selectors")
    return {
        "trade_id": trade["trade_id"],
        "created_at": created[0],
        "closed_at": closed[0],
    }


def adjudicate_candidate(
    stages: dict[str, dict], edge: dict, semantic_types: dict[str, dict]
) -> dict:
    case = load_json(ROOT / "evidence/issue-4/candidate-edge-check-v1.json")
    trade_contract = stages["stage.trade.v1"]
    history_contract = stages["stage.trade_history.v1"]
    consumer_contract = stages["stage.dim_trade_consumer.v1"]
    trade_expected = apply_stage_mapping(trade_contract, case["raw_trade"])
    history_expected = [
        apply_stage_mapping(history_contract, row) for row in case["raw_history"]
    ]
    trade_pass = trade_expected == case["trade_stage_output"]
    history_pass = history_expected == case["history_stage_output"]
    consumer_pass = validate_consumer(
        consumer_contract, case["consumer_input"], case["consumer_output"]
    )
    expected_handoff = expected_edge_handoff(
        edge, case["trade_stage_output"], case["history_stage_output"]
    )
    created_mapping = next(
        mapping for mapping in edge["mappings"] if mapping["to"].endswith("created_at")
    )
    actual_type = case["handoff_bindings"]["created_at"]["source_semantic_type"]
    required_type = created_mapping["target_semantic_type"]
    edge_pass = expected_handoff == case["consumer_input"] and semantic_type_compatible(
        actual_type, required_type
    )
    if not (trade_pass and history_pass and consumer_pass) or edge_pass:
        raise ContractError(
            "candidate does not demonstrate local producer/consumer passes with edge failure"
        )
    if semantic_types[actual_type]["physical_type"] != semantic_types[required_type][
        "physical_type"
    ]:
        raise ContractError("candidate must remain structurally type-valid")
    return {
        "authority": [
            "tpc-di-1.1.0-4.5.8.1",
            "tpc-di-1.1.0-4.5.8.2-create-close",
        ],
        "case_id": case["case_id"],
        "checks": {
            "consumer_local": "pass",
            "edge_composition": "fail",
            "history_producer_local": "pass",
            "trade_producer_local": "pass",
        },
        "decision": {
            "allowed_artifacts": ["sketch.edge.trade_history_to_dim_trade"],
            "failure_class": "edge_composition",
            "location": "edge.trade_history_to_dim_trade.create_close_time",
            "status": "adjudicated",
        },
        "schema_version": "candidate-edge-adjudication/v1",
        "semantic_distinction": {
            "actual": actual_type,
            "physical_type": semantic_types[actual_type]["physical_type"],
            "required": required_type,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "adjudicate"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = validate_bundle()
    except ContractError as error:
        print(f"contract error: {error}", file=sys.stderr)
        return 2
    if args.command == "adjudicate":
        result = result["adjudication"]
    print(canonical_json(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
