import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("oracle", ROOT / "scripts/oracle.py")
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


def fixture(name):
    return ORACLE.load_json(ROOT / f"oracle/fixtures/public/{name}.json")


def submission(name):
    return ORACLE.load_json(ROOT / f"oracle/submissions/examples/{name}.json")


class SemanticRepairOracleTests(unittest.TestCase):
    def test_repository_corpus_is_canonical_and_examples_pass(self):
        result = ORACLE.verify_repository()
        self.assertTrue(result["passed"])
        self.assertEqual(result["cases_scored"], 3)
        self.assertEqual(result["cases_passed"], 3)
        self.assertEqual(result["ambiguous_cases"], 2)
        self.assertEqual(result["held_outs_committed"], 4)
        self.assertIn(
            (result["held_outs_present"], result["held_outs_verified"]),
            {(False, 0), (True, 4)},
        )

    def test_machine_readable_schemas_cover_issue_fields(self):
        schema = ORACLE.load_json(
            ROOT / "oracle/schema/failure-fixture-v1.schema.json"
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], "failure-fixture/v1")
        self.assertEqual(
            set(schema["required"]),
            {
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
            },
        )
        answer_schema = ORACLE.load_json(
            ROOT / "oracle/schema/repair-submission-v1.schema.json"
        )
        self.assertFalse(answer_schema["additionalProperties"])
        self.assertNotIn("explanation", answer_schema["properties"])
        self.assertNotIn("narrative", answer_schema["properties"])

    def test_cases_are_grounded_in_retained_source_anchors_and_manifest(self):
        anchors = ORACLE.load_json(ROOT / "evidence/issue-3/source-anchors-v1.json")
        manifest = ORACLE.load_json(ROOT / "evidence/issue-2/sf3-manifest.json")
        self.assertEqual(
            anchors["generated_source"]["manifest_slice_sha256"],
            {
                name: details["sha256"] for name, details in manifest["slice_files"].items()
            },
        )
        local = fixture("local-trade-type-name-v1")
        edge = fixture("edge-trade-history-create-time-v1")
        self.assertIn(
            local["input"]["tables"]["trade_type"][0],
            anchors["generated_source"]["selected_rows"]["trade_type"],
        )
        self.assertEqual(
            edge["input"]["tables"]["trade_history"],
            anchors["generated_source"]["selected_rows"]["trade_history"],
        )

    def test_raw_or_schema_authority_is_rejected(self):
        malformed = fixture("local-trade-type-name-v1")
        malformed["authority"] = [
            {
                "kind": "raw_schema",
                "id": "inferred-from-columns",
                "source": "raw.trade_type",
                "locator": "tt_name",
            }
        ]
        with self.assertRaisesRegex(ORACLE.OracleError, "not policy authority"):
            ORACLE.validate_fixture(malformed)

        disguised = fixture("local-trade-type-name-v1")
        disguised["authority"] = [
            {
                "kind": "tpc_di_rule",
                "id": "made-up-rule",
                "source": "raw.trade_type",
                "locator": "tt_name looks descriptive",
            }
        ]
        with self.assertRaisesRegex(ORACLE.OracleError, "official specification"):
            ORACLE.validate_fixture(disguised)

    def test_adjudicated_fixture_cannot_hide_ambiguity_or_overlap_authority(self):
        base = fixture("local-trade-type-name-v1")
        cases = []
        multiple_locations = copy.deepcopy(base)
        multiple_locations["location"]["candidates"] = ["another.stage"]
        cases.append(multiple_locations)
        no_allowed = copy.deepcopy(base)
        no_allowed["allowed_artifacts"] = []
        cases.append(no_allowed)
        overlap = copy.deepcopy(base)
        overlap["forbidden_artifacts"].append(overlap["allowed_artifacts"][0])
        cases.append(overlap)
        same_output = copy.deepcopy(base)
        same_output["observed_output"] = same_output["corrected_output"]
        cases.append(same_output)
        wrong_boundary_kind = copy.deepcopy(base)
        wrong_boundary_kind["location"]["kind"] = "edge"
        cases.append(wrong_boundary_kind)
        for malformed in cases:
            with self.subTest(case=malformed["case_id"]):
                with self.assertRaises(ORACLE.OracleError):
                    ORACLE.validate_fixture(malformed)

    def test_ambiguous_case_authorizes_no_forced_repair(self):
        expected = fixture("ambiguous-status-name-boundary-v1")
        actual = submission("ambiguous-status-name-boundary-v1")
        self.assertTrue(ORACLE.score(expected, actual)["passed"])

        forced = copy.deepcopy(actual)
        forced["disposition"] = "resolved"
        forced["failure_class"] = "local_semantic"
        forced["location"] = {
            "kind": "stage",
            "id": "stage.status_type_reference.status_name",
            "candidates": [],
        }
        forced["changed_artifacts"] = ["sketch.stage.status_type_reference"]
        result = ORACLE.score(expected, forced)
        self.assertFalse(result["passed"])
        self.assertFalse(result["dimensions"]["artifact_authority"])
        self.assertFalse(result["dimensions"]["location"])

    def test_narrative_is_invalid_and_cannot_improve_wrong_structural_score(self):
        expected = fixture("edge-trade-history-create-time-v1")
        wrong = submission("edge-trade-history-create-time-v1")
        wrong["location"] = {
            "kind": "stage",
            "id": "stage.trade",
            "candidates": [],
        }
        wrong["changed_artifacts"] = ["generated_sql.dim_trade"]
        result = ORACLE.score(expected, wrong)
        self.assertFalse(result["passed"])
        self.assertFalse(result["dimensions"]["location"])
        self.assertFalse(result["dimensions"]["artifact_authority"])

        wrong["repair_narrative"] = (
            "A persuasive explanation claiming this projection patch is sufficient."
        )
        with self.assertRaisesRegex(ORACLE.OracleError, "submission keys"):
            ORACLE.score(expected, wrong)

    def test_candidate_composition_case_authorizes_no_boundary_or_repair_yet(self):
        expected = fixture("edge-trade-history-create-time-v1")
        actual = submission("edge-trade-history-create-time-v1")
        self.assertEqual(expected["failure_class"], "candidate_edge_composition")
        self.assertEqual(expected["location"]["kind"], "ambiguous")
        self.assertEqual(expected["allowed_artifacts"], [])
        self.assertTrue(ORACLE.score(expected, actual)["passed"])

        forced = copy.deepcopy(actual)
        forced["disposition"] = "resolved"
        forced["failure_class"] = "edge_composition"
        forced["location"] = {
            "kind": "edge",
            "id": "edge.trade_history_to_dim_trade.create_close_time",
            "candidates": [],
        }
        forced["changed_artifacts"] = ["sketch.edge.trade_history_to_dim_trade"]
        result = ORACLE.score(expected, forced)
        self.assertFalse(result["passed"])
        self.assertFalse(result["dimensions"]["artifact_authority"])

    def test_wrong_output_and_incomplete_revalidation_fail_independently(self):
        expected = fixture("local-trade-type-name-v1")
        actual = submission("local-trade-type-name-v1")
        actual["corrected_output"]["type_name"] = "TMS"
        actual["revalidated_descendants"].pop()
        result = ORACLE.score(expected, actual)
        self.assertFalse(result["passed"])
        self.assertFalse(result["dimensions"]["corrected_output"])
        self.assertFalse(result["dimensions"]["affected_descendants"])
        self.assertTrue(result["dimensions"]["location"])

    def test_visible_scoring_refuses_held_out_fixture(self):
        hidden = fixture("local-trade-type-name-v1")
        hidden["case_id"] = "hidden-local-case"
        hidden["visibility"] = "held_out"
        answer = submission("local-trade-type-name-v1")
        answer["case_id"] = hidden["case_id"]
        with self.assertRaisesRegex(ORACLE.OracleError, "refuses held-out"):
            ORACLE.score(hidden, answer)

    def test_sealed_scoring_returns_aggregate_only(self):
        hidden = fixture("local-trade-type-name-v1")
        hidden["case_id"] = "hidden-local-case"
        hidden["visibility"] = "held_out"
        answer = submission("local-trade-type-name-v1")
        answer["case_id"] = hidden["case_id"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_dir = root / "fixtures"
            submission_dir = root / "submissions"
            fixture_dir.mkdir()
            submission_dir.mkdir()
            (fixture_dir / "opaque.json").write_text(
                ORACLE.canonical_json(hidden), encoding="utf-8"
            )
            (submission_dir / "answer.json").write_text(
                ORACLE.canonical_json(answer), encoding="utf-8"
            )
            corpus = self.private_corpus(hidden, fixture_dir / "opaque.json")
            result = ORACLE.score_sealed(
                fixture_dir,
                submission_dir,
                commitments=corpus,
            )
        self.assertEqual(
            set(result),
            {"schema_version", "cases_scored", "cases_passed", "passed"},
        )
        self.assertTrue(result["passed"])
        serialized = json.dumps(result)
        self.assertNotIn(hidden["case_id"], serialized)
        self.assertNotIn("dimensions", serialized)
        self.assertNotIn("corrected_output", serialized)

    def test_sealed_scoring_rejects_public_or_mismatched_case_sets(self):
        public = fixture("local-trade-type-name-v1")
        answer = submission("local-trade-type-name-v1")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_dir = root / "fixtures"
            submission_dir = root / "submissions"
            fixture_dir.mkdir()
            submission_dir.mkdir()
            (fixture_dir / "case.json").write_text(
                ORACLE.canonical_json(public), encoding="utf-8"
            )
            (submission_dir / "answer.json").write_text(
                ORACLE.canonical_json(answer), encoding="utf-8"
            )
            corpus = self.private_corpus(public, fixture_dir / "case.json")
            with self.assertRaisesRegex(ORACLE.OracleError, "only held-out"):
                ORACLE.score_sealed(
                    fixture_dir,
                    submission_dir,
                    commitments=corpus,
                )

            public["visibility"] = "held_out"
            (fixture_dir / "case.json").write_text(
                ORACLE.canonical_json(public), encoding="utf-8"
            )
            corpus["held_out_commitments"][0]["id"] = "a-different-reserved-case"
            with self.assertRaisesRegex(ORACLE.OracleError, "public commitments"):
                ORACLE.score_sealed(
                    fixture_dir,
                    submission_dir,
                    commitments=corpus,
                )

    def test_held_out_commitment_mismatch_and_missing_or_extra_cases_fail(self):
        hidden = fixture("local-trade-type-name-v1")
        hidden["case_id"] = "ho-901"
        hidden["visibility"] = "held_out"
        hidden["held_outs"] = []
        with tempfile.TemporaryDirectory() as directory:
            fixture_dir = Path(directory)
            path = fixture_dir / "ho-901.json"
            path.write_text(ORACLE.canonical_json(hidden), encoding="utf-8")
            corpus = self.private_corpus(hidden, path)
            self.assertEqual(
                ORACLE.verify_held_out_commitments(
                    fixture_dir, corpus, require_complete=True
                )["verified"],
                1,
            )

            tampered = copy.deepcopy(hidden)
            tampered["title"] = "changed after commitment"
            path.write_text(ORACLE.canonical_json(tampered), encoding="utf-8")
            with self.assertRaisesRegex(ORACLE.OracleError, "commitment mismatch"):
                ORACLE.verify_held_out_commitments(
                    fixture_dir, corpus, require_complete=True
                )

            path.unlink()
            with self.assertRaisesRegex(ORACLE.OracleError, "missing or extra"):
                ORACLE.verify_held_out_commitments(
                    fixture_dir, corpus, require_complete=True
                )

            path.write_text(ORACLE.canonical_json(hidden), encoding="utf-8")
            extra = copy.deepcopy(hidden)
            extra["case_id"] = "ho-902"
            (fixture_dir / "ho-902.json").write_text(
                ORACLE.canonical_json(extra), encoding="utf-8"
            )
            with self.assertRaisesRegex(ORACLE.OracleError, "missing or extra"):
                ORACLE.verify_held_out_commitments(
                    fixture_dir, corpus, require_complete=True
                )

    @staticmethod
    def private_corpus(hidden, path):
        return {
            "held_out_commitments": [
                {
                    "id": hidden["case_id"],
                    "public_case_id": "local-trade-type-name-v1",
                    "relationship": "same_boundary_neighbor",
                    "schema_version": "failure-fixture/v1",
                    "sha256": ORACLE.sha256(path),
                    "state": "frozen_private",
                }
            ]
        }


if __name__ == "__main__":
    unittest.main()
