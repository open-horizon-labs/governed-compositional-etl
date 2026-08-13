import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("final_report", ROOT / "scripts/verify_final_report.py")
FINAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FINAL)


class FinalReportTests(unittest.TestCase):
    def setUp(self):
        self.decision = FINAL.load(FINAL.DECISION)
        self.report = FINAL.REPORT.read_text(encoding="utf-8")

    def coordinated_mutation(self, mutate):
        decision = copy.deepcopy(self.decision)
        mutate(decision["canonical_evidence"])
        before = self.report.split(FINAL.BEGIN, 1)[0]
        after = self.report.split(FINAL.END, 1)[1]
        block = json.dumps(decision["canonical_evidence"], indent=2, sort_keys=True)
        report = before + FINAL.BEGIN + block + FINAL.END + after
        decision["canonical_evidence_sha256"] = FINAL.evidence_hash(decision["canonical_evidence"])
        decision["report_sha256"] = FINAL.sha256_bytes(report.encode())
        with self.assertRaises(FINAL.FinalReportError):
            FINAL.verify(decision, report)

    def test_report_recomputes_every_claim(self):
        verified = FINAL.verify()
        self.assertEqual(verified["decision"], "revise")
        evidence = self.decision["canonical_evidence"]
        for arm in evidence["arms"].values():
            self.assertFalse(arm["operator_time_available"])
            self.assertFalse(arm["compute_cost_available"])
            self.assertEqual(arm["model_calls"], 0)
            self.assertEqual(arm["model_tokens"], 0)

    def test_prose_metric_mutation_fails_complete_report_hash(self):
        changed = self.report.replace("physically repaired both", "physically repaired three", 1)
        with self.assertRaises(FINAL.FinalReportError):
            FINAL.verify(self.decision, changed)

    def test_coordinated_decision_metric_mutation_fails_derivation(self):
        self.coordinated_mutation(lambda evidence: evidence["decision"].update({"bounded_decision": "adopt"}))

    def test_coordinated_explanation_mutation_fails_derivation(self):
        self.coordinated_mutation(lambda evidence: evidence["chronology"].update({"unit_change_before_valid_run": "changed after scoring"}))

    def test_decision_hash_mutation_fails(self):
        changed = copy.deepcopy(self.decision)
        changed["canonical_evidence_sha256"] = "0" * 64
        with self.assertRaises(FINAL.FinalReportError):
            FINAL.verify(changed, self.report)

    def test_coordinated_block_value_mutation_fails_derivation(self):
        self.coordinated_mutation(lambda evidence: evidence["arms"]["compositional_cess"].update({"active_repair_rate": 1.0}))

    def test_invalid_run_inclusion_fails(self):
        self.coordinated_mutation(lambda evidence: evidence["limitations"].update({"invalid_scored_attempts_excluded": ["v1"]}))

    def test_physical_repairs_cannot_be_promoted_to_scored_catches(self):
        self.coordinated_mutation(lambda evidence: evidence["physical_vs_scored"].update({"scored_composition_catches": 2}))


if __name__ == "__main__":
    unittest.main()
