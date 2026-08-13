import importlib.util
import json
from pathlib import Path
import unittest


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
        self.assertTrue(all(full["execution"]["results"].values()))


if __name__ == "__main__":
    unittest.main()
