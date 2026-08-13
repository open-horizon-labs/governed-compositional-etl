#!/usr/bin/env python3
"""Validate and score the frozen governed semantic-repair oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "oracle/corpus-v1.json"
FIXTURE_KEYS = {
    "schema_version",
    "case_id",
    "title",
    "visibility",
    "disposition",
    "authority",
    "input",
    "observed_output",
    "corrected_output",
    "failure_class",
    "location",
    "allowed_artifacts",
    "forbidden_artifacts",
    "tempting_wrong_repair",
    "affected_descendants",
    "held_outs",
}
SUBMISSION_KEYS = {
    "schema_version",
    "case_id",
    "disposition",
    "failure_class",
    "location",
    "changed_artifacts",
    "corrected_output",
    "revalidated_descendants",
}
LOCATION_KEYS = {"kind", "id", "candidates"}
CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]+$")
HELD_OUT_ID = re.compile(r"^ho-[0-9]{3}$")
TPC_DI_110_SOURCE = (
    "https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-di_v1.1.0.pdf"
)
TPC_DI_110_RULE = re.compile(r"^tpc-di-1\.1\.0-[a-z0-9.-]+$")


class OracleError(ValueError):
    """An oracle artifact cannot be trusted or scored."""


def load_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as source:
            value = json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        raise OracleError(f"could not load {path}: {error}") from error
    if not isinstance(value, dict):
        raise OracleError(f"{path} must contain a JSON object")
    return value


def canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_exact_keys(value: object, keys: set[str], name: str) -> dict:
    if not isinstance(value, dict):
        raise OracleError(f"{name} must be an object")
    if set(value) != keys:
        raise OracleError(
            f"{name} keys must be {sorted(keys)}; got {sorted(value)}"
        )
    return value


def require_string(value: object, name: str, pattern: re.Pattern | None = None) -> str:
    if not isinstance(value, str) or not value:
        raise OracleError(f"{name} must be a non-empty string")
    if pattern and not pattern.fullmatch(value):
        raise OracleError(f"{name} has an invalid format: {value}")
    return value


def require_string_list(
    value: object, name: str, *, minimum: int = 0
) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise OracleError(f"{name} must be a list with at least {minimum} item(s)")
    for index, item in enumerate(value):
        require_string(item, f"{name}[{index}]")
    if len(value) != len(set(value)):
        raise OracleError(f"{name} must not contain duplicates")
    return value


def validate_location(location: object, name: str) -> dict:
    value = require_exact_keys(location, LOCATION_KEYS, name)
    if value["kind"] not in {"stage", "edge", "path_invariant", "ambiguous"}:
        raise OracleError(f"{name}.kind is not recognized")
    if value["id"] is not None:
        require_string(value["id"], f"{name}.id")
    require_string_list(value["candidates"], f"{name}.candidates")
    return value


def validate_fixture(fixture: object) -> dict:
    value = require_exact_keys(fixture, FIXTURE_KEYS, "fixture")
    if value["schema_version"] != "failure-fixture/v1":
        raise OracleError("fixture.schema_version must be failure-fixture/v1")
    require_string(value["case_id"], "fixture.case_id", CASE_ID)
    require_string(value["title"], "fixture.title")
    if value["visibility"] not in {"public", "held_out"}:
        raise OracleError("fixture.visibility must be public or held_out")
    if value["disposition"] not in {"adjudicated", "ambiguous"}:
        raise OracleError("fixture.disposition must be adjudicated or ambiguous")
    if value["failure_class"] not in {
        "local_semantic",
        "edge_composition",
        "candidate_edge_composition",
        "ambiguous",
    }:
        raise OracleError("fixture.failure_class is not recognized")

    authorities = value["authority"]
    if not isinstance(authorities, list) or not authorities:
        raise OracleError("fixture.authority must be a non-empty list")
    authority_ids = []
    for index, item in enumerate(authorities):
        authority = require_exact_keys(
            item, {"kind", "id", "source", "locator"}, f"fixture.authority[{index}]"
        )
        if authority["kind"] not in {"tpc_di_rule", "approved_decision"}:
            raise OracleError(
                "fixture authority must be a named TPC-DI rule or approved decision; "
                "raw data and schemas are not policy authority"
            )
        for field in ("id", "source", "locator"):
            require_string(authority[field], f"fixture.authority[{index}].{field}")
        if authority["kind"] == "tpc_di_rule" and (
            not TPC_DI_110_RULE.fullmatch(authority["id"])
            or authority["source"] != TPC_DI_110_SOURCE
        ):
            raise OracleError(
                "TPC-DI authority must name a 1.1.0 rule and the official specification"
            )
        if authority["kind"] == "approved_decision" and not authority[
            "source"
        ].startswith(".oh/"):
            raise OracleError(
                "approved decision authority must reference a repository-native .oh record"
            )
        authority_ids.append(authority["id"])
    if len(authority_ids) != len(set(authority_ids)):
        raise OracleError("fixture.authority ids must be unique")
    if not any(item["kind"] == "tpc_di_rule" for item in authorities):
        raise OracleError("fixture must cite at least one named TPC-DI rule")

    input_value = require_exact_keys(value["input"], {"tables"}, "fixture.input")
    tables = input_value["tables"]
    if not isinstance(tables, dict) or not tables:
        raise OracleError("fixture.input.tables must be a non-empty object")
    for table, rows in tables.items():
        require_string(table, "fixture input table name")
        if not isinstance(rows, list) or not rows or not all(
            isinstance(row, dict) for row in rows
        ):
            raise OracleError(f"fixture.input.tables.{table} must contain record objects")
    for output in ("observed_output", "corrected_output"):
        if not isinstance(value[output], dict) or not value[output]:
            raise OracleError(f"fixture.{output} must be a non-empty object")
    if value["observed_output"] == value["corrected_output"]:
        raise OracleError("fixture observed and corrected outputs must differ")

    location = validate_location(value["location"], "fixture.location")
    allowed = require_string_list(value["allowed_artifacts"], "fixture.allowed_artifacts")
    forbidden = require_string_list(
        value["forbidden_artifacts"], "fixture.forbidden_artifacts", minimum=1
    )
    if set(allowed) & set(forbidden):
        raise OracleError("fixture allowed and forbidden artifacts overlap")
    wrong = require_exact_keys(
        value["tempting_wrong_repair"],
        {"artifact", "change", "why_wrong"},
        "fixture.tempting_wrong_repair",
    )
    for field in ("artifact", "change", "why_wrong"):
        require_string(wrong[field], f"fixture.tempting_wrong_repair.{field}")
    if wrong["artifact"] not in forbidden:
        raise OracleError("tempting wrong repair artifact must be explicitly forbidden")
    require_string_list(
        value["affected_descendants"], "fixture.affected_descendants", minimum=1
    )

    held_outs = value["held_outs"]
    if not isinstance(held_outs, list) or (
        value["visibility"] == "public" and not held_outs
    ):
        raise OracleError(
            "fixture.held_outs must be a list and public fixtures need a neighbor"
        )
    held_out_ids = []
    for index, item in enumerate(held_outs):
        held_out = require_exact_keys(
            item, {"id", "relationship"}, f"fixture.held_outs[{index}]"
        )
        held_out_ids.append(
            require_string(held_out["id"], f"fixture.held_outs[{index}].id", HELD_OUT_ID)
        )
        if held_out["relationship"] not in {
            "same_boundary_neighbor",
            "downstream_neighbor",
        }:
            raise OracleError(f"fixture.held_outs[{index}].relationship is not recognized")
    if len(held_out_ids) != len(set(held_out_ids)):
        raise OracleError("fixture.held_outs ids must be unique")

    if value["disposition"] == "adjudicated":
        if value["failure_class"] not in {"local_semantic", "edge_composition"}:
            raise OracleError("adjudicated fixture must have a scorable failure class")
        if location["kind"] == "ambiguous" or location["id"] is None or location["candidates"]:
            raise OracleError("adjudicated fixture must name exactly one responsible location")
        if not allowed:
            raise OracleError("adjudicated fixture must authorize at least one artifact")
        if value["failure_class"] == "local_semantic" and location["kind"] != "stage":
            raise OracleError("local semantic fixture must locate a stage")
        if value["failure_class"] == "edge_composition" and location["kind"] not in {
            "edge",
            "path_invariant",
        }:
            raise OracleError("edge/composition fixture must locate an edge or path invariant")
    else:
        if value["failure_class"] not in {
            "ambiguous",
            "candidate_edge_composition",
        }:
            raise OracleError(
                "ambiguous fixture must remain ambiguous or a candidate edge/composition case"
            )
        if (
            location["kind"] != "ambiguous"
            or location["id"] is not None
            or len(location["candidates"]) < 2
        ):
            raise OracleError("ambiguous fixture must retain at least two candidate locations")
        if allowed:
            raise OracleError("ambiguous fixture must not authorize a repair artifact")
    return value


def validate_submission(submission: object) -> dict:
    value = require_exact_keys(submission, SUBMISSION_KEYS, "submission")
    if value["schema_version"] != "repair-submission/v1":
        raise OracleError("submission.schema_version must be repair-submission/v1")
    require_string(value["case_id"], "submission.case_id", CASE_ID)
    if value["disposition"] not in {"resolved", "ambiguous"}:
        raise OracleError("submission.disposition must be resolved or ambiguous")
    if value["failure_class"] not in {
        "local_semantic",
        "edge_composition",
        "candidate_edge_composition",
        "ambiguous",
    }:
        raise OracleError("submission.failure_class is not recognized")
    validate_location(value["location"], "submission.location")
    require_string_list(value["changed_artifacts"], "submission.changed_artifacts")
    require_string_list(
        value["revalidated_descendants"], "submission.revalidated_descendants"
    )
    if not isinstance(value["corrected_output"], dict):
        raise OracleError("submission.corrected_output must be an object")
    return value


def comparable_location(location: dict) -> tuple[str, str | None, tuple[str, ...]]:
    return (location["kind"], location["id"], tuple(sorted(location["candidates"])))


def score(fixture: object, submission: object, *, allow_held_out: bool = False) -> dict:
    expected = validate_fixture(fixture)
    actual = validate_submission(submission)
    if expected["visibility"] == "held_out" and not allow_held_out:
        raise OracleError("visible scoring refuses held-out fixtures")
    expected_disposition = (
        "ambiguous" if expected["disposition"] == "ambiguous" else "resolved"
    )
    changed = set(actual["changed_artifacts"])
    allowed = set(expected["allowed_artifacts"])
    forbidden = set(expected["forbidden_artifacts"])
    artifact_authority = (
        not changed
        if expected["disposition"] == "ambiguous"
        else bool(changed) and changed <= allowed and not changed & forbidden
    )
    dimensions = {
        "case_id": actual["case_id"] == expected["case_id"],
        "disposition": actual["disposition"] == expected_disposition,
        "failure_class": actual["failure_class"] == expected["failure_class"],
        "location": comparable_location(actual["location"])
        == comparable_location(expected["location"]),
        "artifact_authority": artifact_authority,
        "corrected_output": actual["corrected_output"] == expected["corrected_output"],
        "affected_descendants": set(actual["revalidated_descendants"])
        == set(expected["affected_descendants"]),
    }
    return {
        "case_id": expected["case_id"],
        "dimensions": dimensions,
        "passed": all(dimensions.values()),
        "schema_version": "visible-score/v1",
    }


def validate_corpus(path: Path = CORPUS) -> tuple[dict, list[tuple[dict, dict]]]:
    corpus = require_exact_keys(
        load_json(path),
        {"schema_version", "public_cases", "held_out_commitments"},
        "corpus",
    )
    if corpus["schema_version"] != "oracle-corpus/v1":
        raise OracleError("corpus.schema_version must be oracle-corpus/v1")
    if not isinstance(corpus["public_cases"], list) or not corpus["public_cases"]:
        raise OracleError("corpus.public_cases must be a non-empty list")
    pairs = []
    fixture_case_ids = set()
    referenced_held_outs = {}
    for index, item in enumerate(corpus["public_cases"]):
        entry = require_exact_keys(
            item, {"fixture", "example_submission"}, f"corpus.public_cases[{index}]"
        )
        fixture_path = safe_repo_path(entry["fixture"], f"corpus.public_cases[{index}].fixture")
        submission_path = safe_repo_path(
            entry["example_submission"],
            f"corpus.public_cases[{index}].example_submission",
        )
        fixture = validate_fixture(load_json(fixture_path))
        if fixture["visibility"] != "public":
            raise OracleError("corpus.public_cases cannot reference held-out fixtures")
        submission = validate_submission(load_json(submission_path))
        if fixture["case_id"] in fixture_case_ids:
            raise OracleError("corpus public case ids must be unique")
        fixture_case_ids.add(fixture["case_id"])
        for held_out in fixture["held_outs"]:
            if held_out["id"] in referenced_held_outs:
                raise OracleError("a held-out may neighbor only one public case")
            referenced_held_outs[held_out["id"]] = {
                "public_case_id": fixture["case_id"],
                "relationship": held_out["relationship"],
            }
        pairs.append((fixture, submission))

    commitments = corpus["held_out_commitments"]
    if not isinstance(commitments, list) or not commitments:
        raise OracleError("corpus.held_out_commitments must be a non-empty list")
    committed = {}
    for index, item in enumerate(commitments):
        commitment = require_exact_keys(
            item,
            {
                "id",
                "state",
                "schema_version",
                "public_case_id",
                "relationship",
                "sha256",
            },
            f"corpus.held_out_commitments[{index}]",
        )
        case_id = require_string(
            commitment["id"],
            f"corpus.held_out_commitments[{index}].id",
            HELD_OUT_ID,
        )
        if case_id in committed:
            raise OracleError("held-out commitment ids must be unique")
        if commitment["state"] != "frozen_private":
            raise OracleError("held-out commitments must remain frozen_private")
        if commitment["schema_version"] != "failure-fixture/v1":
            raise OracleError("held-out commitment schema version is not recognized")
        require_string(commitment["public_case_id"], "held-out public_case_id", CASE_ID)
        if commitment["relationship"] not in {
            "same_boundary_neighbor",
            "downstream_neighbor",
        }:
            raise OracleError("held-out commitment relationship is not recognized")
        if not isinstance(commitment["sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", commitment["sha256"]
        ):
            raise OracleError("held-out commitment sha256 must be 64 lowercase hex")
        committed[case_id] = commitment
    if set(committed) != set(referenced_held_outs):
        raise OracleError("held-out commitments must exactly match fixture neighbors")
    for case_id, relation in referenced_held_outs.items():
        for field in ("public_case_id", "relationship"):
            if committed[case_id][field] != relation[field]:
                raise OracleError(
                    "held-out commitment relationship metadata contradicts its public fixture"
                )
    return corpus, pairs


def verify_held_out_commitments(
    fixture_dir: Path, corpus: dict, *, require_complete: bool
) -> dict:
    expected = {item["id"]: item for item in corpus["held_out_commitments"]}
    paths = sorted(fixture_dir.glob("*.json")) if fixture_dir.is_dir() else []
    if not paths and not require_complete:
        return {"present": False, "verified": 0}
    fixtures = {}
    fixture_paths = {}
    for path in paths:
        fixture = validate_fixture(load_json(path))
        if fixture["visibility"] != "held_out":
            raise OracleError("private custody accepts only held-out fixtures")
        case_id = fixture["case_id"]
        if case_id in fixtures:
            raise OracleError("private held-out fixture case ids must be unique")
        fixtures[case_id] = fixture
        fixture_paths[case_id] = path
    if set(fixtures) != set(expected):
        raise OracleError(
            "private held-out fixtures must exactly match public commitments (no missing or extra cases)"
        )
    for case_id, fixture in fixtures.items():
        commitment = expected[case_id]
        if fixture["schema_version"] != commitment["schema_version"]:
            raise OracleError(f"held-out schema mismatch for {case_id}")
        actual = sha256(fixture_paths[case_id])
        if actual != commitment["sha256"]:
            raise OracleError(f"held-out commitment mismatch for {case_id}")
    return {"present": True, "verified": len(fixtures)}


def safe_repo_path(relative: object, name: str) -> Path:
    value = require_string(relative, name)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise OracleError(f"{name} must be a safe repository-relative path")
    resolved = (ROOT / path).resolve()
    if ROOT.resolve() not in resolved.parents:
        raise OracleError(f"{name} escapes the repository")
    return resolved


def verify_repository() -> dict:
    corpus, pairs = validate_corpus()
    results = [score(fixture, submission) for fixture, submission in pairs]
    held_out = verify_held_out_commitments(
        ROOT / "oracle/fixtures/held-out", corpus, require_complete=False
    )
    canonical_paths = [CORPUS]
    for entry in corpus["public_cases"]:
        canonical_paths.extend(
            [safe_repo_path(entry["fixture"], "fixture"), safe_repo_path(entry["example_submission"], "submission")]
        )
    canonical_paths.extend(
        [
            ROOT / "oracle/schema/failure-fixture-v1.schema.json",
            ROOT / "oracle/schema/repair-submission-v1.schema.json",
            ROOT / "evidence/issue-3/source-anchors-v1.json",
        ]
    )
    for path in canonical_paths:
        value = load_json(path)
        if path.read_text(encoding="utf-8") != canonical_json(value):
            raise OracleError(f"{path.relative_to(ROOT)} is not canonical JSON")
    return {
        "ambiguous_cases": sum(
            fixture["disposition"] == "ambiguous" for fixture, _ in pairs
        ),
        "cases_passed": sum(result["passed"] for result in results),
        "cases_scored": len(results),
        "held_outs_committed": len(corpus["held_out_commitments"]),
        "held_outs_present": held_out["present"],
        "held_outs_verified": held_out["verified"],
        "passed": all(result["passed"] for result in results),
        "schema_version": "oracle-verification/v1",
    }


def score_sealed(
    fixture_dir: Path,
    submission_dir: Path,
    *,
    commitments: dict | None = None,
) -> dict:
    if commitments is None:
        corpus, _ = validate_corpus()
    else:
        corpus = commitments
    verify_held_out_commitments(fixture_dir, corpus, require_complete=True)
    committed_case_ids = {item["id"] for item in corpus["held_out_commitments"]}
    fixtures = {}
    for path in sorted(fixture_dir.glob("*.json")):
        fixture = validate_fixture(load_json(path))
        if fixture["visibility"] != "held_out":
            raise OracleError("sealed scoring accepts only held-out fixtures")
        if fixture["case_id"] in fixtures:
            raise OracleError("sealed fixture case ids must be unique")
        fixtures[fixture["case_id"]] = fixture
    submissions = {}
    for path in sorted(submission_dir.glob("*.json")):
        submission = validate_submission(load_json(path))
        if submission["case_id"] in submissions:
            raise OracleError("sealed submission case ids must be unique")
        submissions[submission["case_id"]] = submission
    if set(fixtures) != committed_case_ids:
        raise OracleError("sealed fixtures must exactly match the committed held-out case ids")
    if set(fixtures) != set(submissions):
        raise OracleError("sealed fixture and submission case sets must match")
    results = [score(fixtures[case_id], submissions[case_id], allow_held_out=True) for case_id in fixtures]
    return {
        "cases_passed": sum(result["passed"] for result in results),
        "cases_scored": len(results),
        "passed": all(result["passed"] for result in results),
        "schema_version": "sealed-score/v1",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify", help="validate the corpus and score public examples")
    visible = commands.add_parser("score", help="score one public structural submission")
    visible.add_argument("--fixture", type=Path, required=True)
    visible.add_argument("--submission", type=Path, required=True)
    sealed = commands.add_parser(
        "score-sealed", help="score held-outs and emit aggregate results only"
    )
    sealed.add_argument("--fixture-dir", type=Path, required=True)
    sealed.add_argument("--submission-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "verify":
            result = verify_repository()
        elif args.command == "score":
            result = score(load_json(args.fixture), load_json(args.submission))
        else:
            result = score_sealed(args.fixture_dir, args.submission_dir)
    except OracleError as error:
        print(f"oracle error: {error}", file=sys.stderr)
        return 2
    print(canonical_json(result), end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
