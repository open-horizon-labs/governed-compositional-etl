import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import duckdb


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("revalidation", ROOT / "scripts/revalidation.py")
REVALIDATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVALIDATION)


class RevalidationConeTests(unittest.TestCase):
    def setUp(self):
        self.profile = REVALIDATION.load_json(REVALIDATION.PROFILE)

    def test_genuine_edge_cone_matches_frozen_exhaustive_oracle(self):
        cone = REVALIDATION.calculate(self.profile, "edge.create_status")
        self.assertEqual(cone["recall"], 1.0)
        self.assertEqual(cone["precision"], 1.0)
        self.assertEqual(cone["escaped_regressions"], [])
        self.assertEqual(cone["unnecessary_recomputation"], [])
        self.assertEqual(
            cone["semantic_descendants"],
            ["duckdb.dim_trade", "logical.dim_trade", "metric.trade_lifecycle_seconds"],
        )

    def test_omitted_known_descendant_fails_closed(self):
        with self.assertRaisesRegex(REVALIDATION.RevalidationError, "escaped"):
            REVALIDATION.calculate(
                self.profile,
                "edge.create_status",
                {"logical.dim_trade", "duckdb.dim_trade"},
            )

    def test_extra_unaffected_node_is_reported_not_celebrated(self):
        proposed = set(self.profile["frozen_descendant_oracle"]["edge.trade_history_to_dim_trade.create_close_time"])
        proposed.add("edge.trade_type_to_dim_trade")
        cone = REVALIDATION.calculate(self.profile, "edge.create_status", proposed)
        self.assertEqual(cone["recall"], 1.0)
        self.assertEqual(cone["precision"], 0.75)
        self.assertEqual(cone["unnecessary_recomputation"], ["edge.trade_type_to_dim_trade"])

    def test_semantic_only_dependency_absent_from_sql_lineage_is_included(self):
        cone = REVALIDATION.calculate(self.profile, "edge.close_statuses")
        self.assertIn("metric.trade_lifecycle_seconds", cone["semantic_descendants"])
        self.assertNotIn("metric.trade_lifecycle_seconds", cone["executable_revalidation"])

    def test_executable_only_dependencies_remain_separate(self):
        cone = REVALIDATION.calculate(self.profile, "edge.create_status")
        self.assertIn("governed.trade_lifecycle", cone["executable_revalidation"])
        self.assertNotIn("governed.trade_lifecycle", cone["semantic_descendants"])
        self.assertNotEqual(
            self.profile["semantic_dependencies"], self.profile["executable_dependencies"]
        )

    def test_changed_field_specificity_excludes_unrelated_lifecycle_metric(self):
        cone = REVALIDATION.calculate(self.profile, "stage.trade_type.rule")
        self.assertEqual(
            cone["semantic_descendants"],
            ["duckdb.dim_trade", "edge.trade_type_to_dim_trade", "logical.dim_trade"],
        )
        self.assertNotIn("metric.trade_lifecycle_seconds", cone["all_revalidation_nodes"])
        self.assertNotIn("invariant.lifecycle_duration", cone["checks"])

    def test_active_curated_and_every_affected_path_invariant_are_selected(self):
        cone = REVALIDATION.calculate(self.profile, "edge.create_status")
        self.assertTrue(
            {
                "edge-trade-history-create-time-v1",
                "local-trade-type-name-v1",
                "invariant.dim_trade_identity",
                "invariant.lifecycle_duration",
            }
            <= set(cone["checks"])
        )
        archive = json.loads((ROOT / "counterexamples/archive/index-v1.json").read_text())
        regressions = json.loads((ROOT / "regressions/curated-v1.json").read_text())
        self.assertEqual(archive["accepted_counterexamples"], [])
        self.assertEqual([case["id"] for case in regressions["cases"]], ["local-trade-type-name-v1"])

    def test_full_replay_control_preserves_safety_and_reports_cost(self):
        report = json.loads(REVALIDATION.EVIDENCE.read_text())
        full = report["full_replay_control"]
        cone = report["cone"]
        self.assertEqual(full["recall"], 1.0)
        self.assertEqual(full["escaped_regressions"], [])
        self.assertGreater(full["node_count"], cone["node_count"])
        self.assertGreaterEqual(full["check_count"], cone["check_count"])
        self.assertTrue(all(full["execution"]["check_results"].values()))
        self.assertEqual(len(full["execution"]["executed_models"]), 6)
        self.assertEqual(len(cone["execution"]["executed_models"]), 2)
        self.assertEqual(
            [item["name"] for item in cone["execution"]["executed_models"]],
            ["governed.trade_lifecycle", "governed.dim_trade"],
        )
        self.assertEqual(len(cone["execution"]["required_ancestors"]), 4)
        self.assertEqual(full["execution"]["audit_count"], 6)

    def test_live_scores_replayed_data_not_predeclared_example_outputs(self):
        report = json.loads(REVALIDATION.EVIDENCE.read_text())
        live = report["cone"]["execution"]["live_submissions"]
        self.assertEqual(live["edge-trade-history-create-time-v1"]["corrected_output"]["created_at"], "2012-07-07T00:01:13")
        self.assertEqual(live["local-trade-type-name-v1"]["corrected_output"]["type_name"], "Market Sell")
        self.assertTrue(all(live["edge-trade-history-create-time-v1"]["score_dimensions"].values()))

    def test_wrong_live_semantics_pass_local_structure_but_fail_case_scoring(self):
        with tempfile.TemporaryDirectory(prefix="issue6-negative-", dir=ROOT / "build") as directory:
            database = Path(directory) / "negative.duckdb"
            connection = duckdb.connect(str(database))
            connection.execute("CREATE SCHEMA replay_observed")
            connection.execute("CREATE TABLE replay_observed.dim_trade(trade_id BIGINT, created_at TIMESTAMP, closed_at TIMESTAMP)")
            connection.execute("INSERT INTO replay_observed.dim_trade VALUES (0, TIMESTAMP '2012-07-07 00:02:34', TIMESTAMP '2012-07-07 00:02:34')")
            connection.execute("CREATE TABLE replay_observed.trade_type_reference(trade_type_id VARCHAR, type_name VARCHAR, is_sell BOOLEAN, is_market BOOLEAN)")
            connection.execute("INSERT INTO replay_observed.trade_type_reference VALUES ('TMS', 'TMS', true, true)")
            self.assertTrue(connection.execute("SELECT count(*) = count(DISTINCT trade_id) AND count(*) = 1 FROM replay_observed.dim_trade").fetchone()[0])
            self.assertTrue(connection.execute("SELECT count(*) = 0 FROM replay_observed.dim_trade WHERE trade_id IS NULL OR created_at IS NULL").fetchone()[0])
            self.assertTrue(connection.execute("SELECT count(*) = 0 FROM replay_observed.trade_type_reference WHERE trade_type_id IS NULL OR type_name IS NULL").fetchone()[0])
            connection.close()
            for case_id, source in (
                ("edge-trade-history-create-time-v1", "edge.trade_history_to_dim_trade.create_close_time"),
                ("local-trade-type-name-v1", "stage.trade_type_reference.type_name"),
            ):
                submission = REVALIDATION.live_submission(database, case_id, self.profile["frozen_descendant_oracle"][source])
                fixture = REVALIDATION.load_json(ROOT / f"oracle/fixtures/public/{case_id}.json")
                score = REVALIDATION.ORACLE.score(fixture, submission)
                self.assertFalse(score["passed"])
                self.assertFalse(score["dimensions"]["corrected_output"])

    def test_profile_rejects_dag_lineage_alias_check_and_invariant_mutations(self):
        mutations = []
        value = json.loads(json.dumps(self.profile)); value["executable_dependencies"]["governed.trade_stage"].remove("governed.dim_trade"); mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["executable_dependencies"]["governed.dim_trade"].append("governed.trade_stage"); mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["changes"]["edge.create_status"]["pointer"] = "/history_policy/ordering"; mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["semantic_public_nodes"]["logical.dim_trade.type"] = "duckdb.dim_trade"; mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["node_checks"]["governed.dim_trade"] = []; mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["path_invariants"]["invariant.lifecycle_duration"]["sources"] = []; mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["path_invariants"]["invariant.lifecycle_duration"]["nodes"].append("edge.trade_type_to_dim_trade"); mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["node_checks"]["metric.trade_lifecycle_seconds"].append("local-trade-type-name-v1"); mutations.append(value)
        value = json.loads(json.dumps(self.profile)); del value["node_checks"]["stage.trade_type_reference.type_name"]; mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["node_checks"]["unknown.semantic.node"] = ["sqlmesh.audits"]; mutations.append(value)
        value = json.loads(json.dumps(self.profile)); del value["node_checks"]["governed.trade_lifecycle"]; mutations.append(value)
        value = json.loads(json.dumps(self.profile)); value["unexpected"] = True; mutations.append(value)
        for mutated in mutations:
            with self.assertRaises(REVALIDATION.RevalidationError):
                REVALIDATION.validate_profile(mutated)

    def test_profile_path_rejects_symlink_even_to_canonical_profile(self):
        with tempfile.TemporaryDirectory(prefix="issue6-profile-", dir=ROOT / "build") as directory:
            link = Path(directory) / "profile.json"
            link.symlink_to(REVALIDATION.PROFILE)
            original = REVALIDATION.PROFILE
            try:
                REVALIDATION.PROFILE = link
                with self.assertRaisesRegex(REVALIDATION.RevalidationError, "tracked regular non-symlink"):
                    REVALIDATION.validate_profile(self.profile)
            finally:
                REVALIDATION.PROFILE = original


if __name__ == "__main__":
    unittest.main()
