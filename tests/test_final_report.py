import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("final_report", ROOT / "scripts/verify_final_report.py")
FINAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FINAL)


class FinalReportTests(unittest.TestCase):
    def test_report_recomputes_and_verifies(self):
        self.assertEqual(FINAL.verify()["decision"], "revise")

    def test_valid_result_is_not_rescored_for_order_false_negative(self):
        result = FINAL.load(FINAL.RESULT)
        self.assertEqual(result["incremental_edge_or_composition_catches"], 1)
        self.assertEqual(result["threshold_evaluation"]["decision"], "revise")
        edge = next(item for item in result["arms"]["compositional_cess"]["traces"] if item["case_id"] == "v2-edge-creation-time")
        self.assertFalse(edge["deterministic_score"]["dimensions"]["affected_descendants"])
        self.assertFalse(edge["deterministic_score"]["passed"])

    def test_reported_metrics_fail_under_tamper(self):
        result = FINAL.load(FINAL.RESULT)
        changed = copy.deepcopy(result)
        changed["summaries"]["compositional_cess"]["active_repair_rate"] = 1.0
        self.assertNotEqual(FINAL.exact_arm(changed, "compositional_cess"), FINAL.load(FINAL.DECISION)["arms"]["compositional_cess"])


if __name__ == "__main__":
    unittest.main()
