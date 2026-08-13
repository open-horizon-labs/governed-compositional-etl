import copy
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


EXP = module("experiment_v2", "scripts/experiment_v2.py")
VERIFY = module("verify_experiment_v2", "scripts/verify_experiment_v2.py")


class ExperimentV2AdversarialTests(unittest.TestCase):
    def test_one_repair_policy_has_no_arm_branch_or_truth_input(self):
        source = inspect.getsource(EXP.repair_policy)
        self.assertNotIn("arm_name", source)
        self.assertNotIn("layers", source)
        self.assertNotIn("expected", source)
        evidence = [{"kind": "semantic_finding", "failure_class": "projection_defect", "location": "x", "artifact": "a"}]
        self.assertEqual(EXP.repair_policy(evidence), EXP.repair_policy(copy.deepcopy(evidence)))

    def test_runner_cannot_read_private_custody_or_answer_submissions(self):
        source = (ROOT / "scripts/experiment_v2.py").read_text()
        self.assertNotIn("custody/", source)
        self.assertNotIn("oracle/submissions/held-out", source)
        self.assertNotIn("fixtures.json", source)

    def test_scorer_rejects_arm_branch_and_scores_only_after_submission(self):
        request = {"arm": "native", "case_id": "v2-projection-null-trade-id", "proposal": {}, "live_result": {}, "diff": {}}
        run = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/experiment_scorer_v2.py")], input=json.dumps(request), text=True)
        self.assertNotEqual(run.returncode, 0)
        source = (ROOT / "scripts/experiment_scorer_v2.py").read_text()
        self.assertNotIn("if arm", source)

    def test_noop_and_forbidden_repairs_fail(self):
        case = EXP.load(EXP.CORPUS)["cases"][0]
        proposal = {"disposition": "resolved"}
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            project = Path(directory)
            target = project / "models/dim_trade.sql"
            target.parent.mkdir(parents=True)
            target.write_text("NULL AS trade_id")
            with self.assertRaises(EXP.ExperimentV2Error):
                EXP.restore_and_execute(case, project, ROOT / "build/tpcdi.duckdb", target, "NULL AS trade_id", proposal)

    def test_heldout_custodian_rejects_before_visible_acceptance(self):
        request = {"visible_phase_complete": False, "layers": ["pipeline"], "run_nonce": "issue7-v24-run-20260813-d"}
        run = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/sealed_custodian_v2.py")], input=json.dumps(request), text=True)
        self.assertNotEqual(run.returncode, 0)

    def test_posthoc_corpus_and_harness_tamper_fail_prereg(self):
        corpus, prereg = EXP.load(EXP.CORPUS), EXP.load(EXP.PREREG)
        mutated = copy.deepcopy(prereg)
        mutated["frozen_hashes"]["corpus_sha256"] = "0" * 64
        with self.assertRaises(EXP.ExperimentV2Error):
            EXP.validate_preregistration(corpus, mutated)

    @unittest.skipUnless(EXP.RESULT.exists() and EXP.ENVELOPE.exists(), "v2 result not run yet")
    def test_envelope_detects_tamper_and_fake_replay_metrics(self):
        envelope, result = EXP.load(EXP.ENVELOPE), EXP.load(EXP.RESULT)
        VERIFY.verify(envelope, result)
        fake = copy.deepcopy(result)
        fake["arms"]["native"]["localized_replay"]["recall"] = 0.5
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.verify(envelope, fake)

    def test_static_output_shortcut_absent(self):
        source = (ROOT / "scripts/experiment_v2.py").read_text()
        self.assertIn("SELECT count(*) FROM experiment_observed.dim_trade", source)
        self.assertIn("materialize_observed", source)
        self.assertIn("date_diff('second', created_at, closed_at)", source)
        self.assertNotIn("score_live_probe", source)


if __name__ == "__main__":
    unittest.main()
