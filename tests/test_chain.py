"""Compile-chain machinery: L1 parsing, L2 gate, fingerprints and cache plan, weave, L3 gate."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


L2 = load("chain_l2", "scripts/chain_l2.py")
L3 = load("chain_l3", "scripts/chain_l3.py")
JOB = "ownership-history"
MODEL_PATH = ROOT / "chain/l2" / JOB / "semantic-model.json"


class L1Tests(unittest.TestCase):
    def test_l1_parses_clauses_holes_jobs_and_hashes_each_clause(self):
        l1 = L2.parse_l1()
        self.assertIn("L1.attribution-at-placement", l1["clauses"])
        self.assertIn("L1.statement-content", l1["clauses"])
        self.assertIn("L1.hole.owner-change-reversions-account", l1["holes"])
        self.assertEqual(set(l1["jobs"]), {"ownership-history", "trade-lifecycle", "positions"})
        for job in l1["jobs"].values():
            self.assertTrue(job["feedback"])
        fps = l1["clause_fingerprints"]
        self.assertEqual(len(set(fps.values())), len(fps))
        self.assertEqual(len(fps["L1.identity"]), 64)


class L2GateTests(unittest.TestCase):
    def mutate(self, fn):
        doc = json.loads(MODEL_PATH.read_text())
        fn(doc)
        tmp = ROOT / "chain/l2/testjob"
        (tmp).mkdir(exist_ok=True)
        (tmp / "semantic-model.json").write_text(json.dumps(doc))
        try:
            l1 = L2.parse_l1()
            l1["jobs"]["testjob"] = l1["jobs"][JOB]
            doc["job"] = "testjob"
            (tmp / "semantic-model.json").write_text(json.dumps(doc))
            return L2.check("testjob", l1)
        finally:
            (tmp / "semantic-model.json").unlink()
            tmp.rmdir()

    def test_selected_model_passes_the_gate(self):
        report = L2.check(JOB)
        self.assertEqual(report["status"], "ok", report["problems"])

    def test_role_on_an_attribute_is_rejected(self):
        report = self.mutate(lambda d: d["entities"][0]["attributes"][0].__setitem__("mutation_role", "identity"))
        self.assertTrue(any("roles live on types" in p or "schema" in p for p in report["problems"]), report["problems"])

    def test_mutable_inside_versioned_entity_is_rejected(self):
        def fn(d):
            for t in d["types"]:
                if t["id"] == "customer_tier":
                    t["mutation_role"] = "mutable"
        report = self.mutate(fn)
        self.assertTrue(any("per_statement" in p for p in report["problems"]), report["problems"])

    def test_frozen_role_without_supporting_clause_is_rejected(self):
        def fn(d):
            for t in d["types"]:
                if t["id"] == "customer_tier":
                    t["mutation_role"] = "frozen_from_first_encounter"
        report = self.mutate(fn)
        self.assertTrue(any("frozen" in p for p in report["problems"]), report["problems"])

    def test_uncovered_clause_is_a_gap(self):
        def fn(d):
            d["sufficiency_groups"] = [g for g in d["sufficiency_groups"] if "L1.current-version" not in g["parent_clauses"]]
            d["entities"] = [e for e in d["entities"]]
            for e in d["entities"]:
                e["attributes"] = [a for a in e["attributes"] if a["sufficiency_group"] != "sg.current-version"]
            d["invariants"] = [i for i in d["invariants"] if i["sufficiency_group"] != "sg.current-version"]
            d["types"] = [t for t in d["types"] if t["sufficiency_group"] != "sg.current-version"]
        report = self.mutate(fn)
        self.assertTrue(any("no sufficiency group" in p for p in report["problems"]), report["problems"])

    def test_dangling_question_reference_is_rejected(self):
        report = self.mutate(lambda d: d["entities"][0].__setitem__("note", "see questions_for_authority"))
        self.assertTrue(any("no question is filed" in p for p in report["problems"]), report["problems"])

    def test_filed_question_does_not_block_validation(self):
        report = self.mutate(lambda d: d.__setitem__("questions_for_authority", ["Which moment is placement?"]))
        self.assertEqual(report["status"], "question")
        self.assertEqual(report["problems"], [])

    def test_developer_may_not_self_select(self):
        report = self.mutate(lambda d: d["entities"][0].__setitem__("disposition", "selected"))
        self.assertTrue(any("only a reviewer selects" in p or "schema" in p for p in report["problems"]))

    def test_action_code_enumerations_must_agree_and_match_subjects(self):
        def fn(d):
            for h in d["handoffs"]:
                if h["to"] == "logical.account.account_number" and h["from"].startswith("raw.customer_mgmt_action"):
                    h["necessity"] += " Also INACT rows."
        report = self.mutate(fn)
        self.assertTrue(any("INACT" in p for p in report["problems"]), report["problems"])


    def test_attribute_from_a_field_some_action_omits_needs_carry_forward(self):
        def fn(d):
            for e in d["entities"]:
                for a in e["attributes"]:
                    if a["name"] == "tier":
                        a.pop("derivation", None)
        report = self.mutate(fn)
        self.assertTrue(any("INACT" in p and "carried_forward" in p for p in report["problems"]), report["problems"])

    def test_upstream_handoff_may_change_mutation_role_but_not_meaning(self):
        report = L2.check("trade-lifecycle")
        self.assertIn(report["status"], ("ok", "question"), report.get("problems"))
        self.assertFalse(any("does not match the upstream type" in p for p in report.get("problems", [])))


class CacheTests(unittest.TestCase):
    def test_group_fingerprints_change_only_for_groups_citing_a_changed_clause(self):
        l1 = L2.parse_l1()
        before = L2.fingerprints(JOB, l1)
        changed = json.loads(json.dumps(l1))
        changed["clause_fingerprints"]["L1.current-version"] = "0" * 64
        after = L2.fingerprints(JOB, changed)
        for gid in before:
            cites = "L1.current-version" in before[gid]["derived_from"]
            self.assertEqual(before[gid]["fingerprint"] != after[gid]["fingerprint"], cites, gid)

    def test_plan_reports_hits_and_stale_without_jev(self):
        l1 = L2.parse_l1()
        manifest = {"l1": {"clauses": l1["clauses"], "clause_fingerprints": l1["clause_fingerprints"]}, "jobs": {JOB: {"elements": L2.fingerprints(JOB, l1)}}}
        report = L2.plan(previous=manifest, use_jev=False)
        job = report["jobs"][JOB]
        self.assertEqual(job["status"], "ok")
        self.assertTrue(all(i["cache"] == "hit" for i in job["elements"].values()), {k: v["cache"] for k, v in job["elements"].items()})
        previous = json.loads(json.dumps(manifest))
        previous["l1"]["clause_fingerprints"]["L1.identity"] = "0" * 64
        for gid, info in previous["jobs"][JOB]["elements"].items():
            if "L1.identity" in info["derived_from"]:
                info["fingerprint"] = "1" * 64
        report = L2.plan(previous=previous, use_jev=False)
        stale = report["jobs"][JOB]["stale"]
        self.assertTrue(stale)
        self.assertTrue(all("L1.identity" in report["jobs"][JOB]["elements"][g]["derived_from"] for g in stale))


class WeaveTests(unittest.TestCase):
    def test_weave_reports_uncovered_clauses_as_gaps(self):
        out = L2.weave()
        gaps = {r.get("clause") for r in out["relations"] if r["relation"] == "gap" and "clause" in r}
        covered = {c for j in out["jobs"] for g in json.loads((ROOT / "chain/l2" / j / "semantic-model.json").read_text())["sufficiency_groups"] for c in g["parent_clauses"]}
        for clause in L2.parse_l1()["clauses"]:
            self.assertEqual(clause in gaps, clause not in covered, clause)


class L3GateTests(unittest.TestCase):
    def test_l3_requires_a_passed_review(self):
        with self.assertRaises(L3.L3Error):
            L3.load_job("positions")

    def test_containment_derives_from_selected_handoffs_only(self):
        model = json.loads((ROOT / "chain/l2" / JOB / "semantic-model.json").read_text())
        steps = L2.element_steps(model)
        selected = {eid for eid, st in steps.items() if st.get("disposition") == "candidate"}
        allowed = L3.containment(model, selected)
        self.assertIn("raw.customer_mgmt_action", allowed["logical.account"])
        self.assertIn("ce.account_changes", allowed["logical.account"])
        self.assertNotIn("raw.account_cdc", allowed["logical.account"])  # deferred handoffs never grant reads


if __name__ == "__main__":
    unittest.main()
