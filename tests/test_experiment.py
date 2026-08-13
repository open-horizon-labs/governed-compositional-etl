import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("experiment", ROOT / "scripts/experiment.py")
EXPERIMENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPERIMENT)


class MatchedExperimentTests(unittest.TestCase):
    def setUp(self):
        self.corpus = EXPERIMENT.load(EXPERIMENT.CORPUS)
        self.prereg = EXPERIMENT.load(EXPERIMENT.PREREG)
        self.result = EXPERIMENT.load(EXPERIMENT.RESULT)

    def test_v1_preregistration_and_result_are_explicitly_invalidated(self):
        with self.assertRaises(EXPERIMENT.ExperimentError):
            EXPERIMENT.validate_frozen(self.corpus, self.prereg)
        self.assertEqual(self.prereg["status"], "invalidated_before_v2")
        self.assertTrue((ROOT / ".oh/metis/issue-7-v1-invalidated.md").is_file())
        self.assertEqual(
            {case["expected_failure_class"] for case in self.corpus["cases"]},
            set(self.prereg["corpus_requirements"]["balanced_classes"]),
        )
        edge = next(case for case in self.corpus["cases"] if case["expected_failure_class"] == "edge_contract_mismatch")
        self.assertEqual(edge["local_checks"], {"producer": "pass", "consumer": "pass"})

    def test_all_arms_enforce_matched_controls_and_sealed_reveal(self):
        controls = self.result["matched_controls"]
        for arm in self.result["arms"].values():
            self.assertEqual(arm["raw_snapshot_sha256"], controls["raw_snapshot_sha256"])
            self.assertEqual(arm["projection_sha256"], controls["projection_sha256"])
            self.assertEqual(arm["reveal_order"], controls["reveal_order"])
            self.assertEqual(arm["repair_attempt_budget"], 1)
            self.assertEqual(arm["model_tokens"], 0)
            self.assertEqual(arm["model_calls"], 0)
            self.assertLessEqual(arm["context_bytes_used"], arm["context_budget_bytes"])
            self.assertTrue(arm["visible_acceptance_phase_complete_before_held_out"])
            self.assertEqual(
                set(arm["held_out_aggregate"]),
                {"schema_version", "cases_scored", "cases_passed", "passed"},
            )

    def test_arm_agnostic_scorer_has_no_expected_winner(self):
        case = self.corpus["cases"][0]
        correct = EXPERIMENT.propose(case, ("pipeline",))
        self.assertTrue(EXPERIMENT.score_case(case, correct)["accepted"])
        self.assertEqual(
            EXPERIMENT.score_case(case, correct),
            EXPERIMENT.score_case(case, dict(correct)),
        )
        unauthorized = dict(correct)
        unauthorized["changed_artifacts"] = ["projection.forbidden"]
        self.assertFalse(EXPERIMENT.score_case(case, unauthorized)["authority"])
        self.assertEqual(
            EXPERIMENT.artifact_diff(case, unauthorized)["outside_allowed_set"],
            ["projection.forbidden"],
        )

    def test_traces_retain_diffs_two_checks_and_ambiguity(self):
        for arm_name, arm in self.result["arms"].items():
            self.assertEqual(len(arm["traces"]), 5)
            for trace in arm["traces"]:
                self.assertIn("deterministic_gate", trace["score"])
                self.assertIn("sketch_review", trace["score"])
                self.assertEqual(trace["attempt"], 1)
                self.assertEqual(trace["artifact_diff"]["outside_allowed_set"], [])
            missing = next(trace for trace in arm["traces"] if trace["case_id"] == "missing-execution-price-policy")
            self.assertEqual(missing["proposal"]["disposition"], "inconclusive")
            self.assertEqual(missing["proposal"]["changed_artifacts"], [])
            retained = EXPERIMENT.load(EXPERIMENT.TRACES / f"{arm_name}.json")
            self.assertEqual(retained["traces"], arm["traces"])

    def test_live_outputs_and_held_out_aggregates_are_scored(self):
        for arm in self.result["arms"].values():
            self.assertTrue(all(score["passed"] for score in arm["live_replay_scores"].values()))
            self.assertEqual(arm["held_out_aggregate"]["cases_scored"], 4)
        self.assertEqual(self.result["arms"]["native"]["held_out_aggregate"]["cases_passed"], 3)
        self.assertFalse(self.result["arms"]["native"]["held_out_aggregate"]["passed"])
        for name in ("stage_local_cess", "compositional_cess"):
            self.assertEqual(self.result["arms"][name]["held_out_aggregate"]["cases_passed"], 4)
            self.assertTrue(self.result["arms"][name]["held_out_aggregate"]["passed"])

    def test_compositional_treatment_uses_contract_cone_only(self):
        native = self.result["arms"]["native"]["traces"]
        stage = self.result["arms"]["stage_local_cess"]["traces"]
        comp = self.result["arms"]["compositional_cess"]["traces"]
        self.assertTrue(all(trace["revalidation"] is None for trace in native + stage))
        edge = next(trace for trace in comp if trace["case_id"] == "edge-history-creation-time")
        self.assertEqual(edge["revalidation"]["precision"], 1.0)
        self.assertEqual(edge["revalidation"]["recall"], 1.0)
        self.assertEqual(edge["revalidation"]["escaped_regressions"], [])

    def test_preregistered_result_is_revise_not_tuned_adopt(self):
        self.assertEqual(self.result["incremental_edge_or_composition_catches"], 2)
        self.assertTrue(self.result["threshold_evaluation"]["quality_pass"])
        self.assertFalse(self.result["threshold_evaluation"]["cost_pass"])
        self.assertEqual(self.result["threshold_evaluation"]["decision"], "revise")
        self.assertGreater(self.result["threshold_evaluation"]["operator_cost_multiple"], 3.0)

    def test_invalid_v1_cannot_be_rerun_or_counted(self):
        with self.assertRaises(EXPERIMENT.ExperimentError):
            EXPERIMENT.run(retain=False)


if __name__ == "__main__":
    unittest.main()
