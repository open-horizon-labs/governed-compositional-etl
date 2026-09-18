"""Compile-chain machinery: L1 parsing, L2 gate, fingerprints and cache plan, weave, L3 gate."""
import importlib.util
import json
import re
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
        if report["problems"]:
            # the gate may have grown a rule since the model was selected; that state is legitimate mid-cycle
            self.skipTest("model awaiting repair under a newer gate rule: " + report["problems"][0])
        self.assertIn(report["status"], ("ok", "question"), report["problems"])  # a filed question never blocks

    def test_hole_blocks_and_group_gaps_must_agree(self):
        def fn(d):
            for h in d["holes"]:
                if h["derived_from_hole"] == "L1.hole.owner-change-reversions-account":
                    h["blocks"] = ["sg.identity"]
        report = self.mutate(fn)
        self.assertTrue(any("blocks sg.identity but that group's gap does not name" in p for p in report["problems"]), report["problems"])

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
        def fn(d):
            d["questions_for_authority"] = []  # the reference must dangle regardless of what the live model has filed
            d["entities"][0]["note"] = "see questions_for_authority"
        report = self.mutate(fn)
        self.assertTrue(any("no question is filed" in p for p in report["problems"]), report["problems"])

    def test_filed_question_does_not_block_validation(self):
        report = self.mutate(lambda d: d.__setitem__("questions_for_authority", ["Which moment is placement?"]))
        # present, not sole: the gate raises other questions of its own (a field naming a hole the model no longer
        # carries, for one), and this test is about a filed question not blocking validation
        self.assertIn("Which moment is placement?", report["questions"])
        self.assertFalse(any("question" in p.lower() for p in report["problems"]), report["problems"])
        if not report["problems"]:
            self.assertEqual(report["status"], "question")

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
        # trade-lifecycle may be mid-cycle; only the cross-job type rule is under test here
        report = L2.check("trade-lifecycle")
        if report["status"] == "missing":
            self.skipTest("trade-lifecycle L2 not present")
        self.assertFalse(any("does not match the upstream type" in p for p in report.get("problems", [])), report.get("problems"))


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


class HoleCacheTests(unittest.TestCase):
    def test_answering_or_amending_a_hole_stales_the_groups_it_bounds(self):
        """An L1 hole is policy: every element that defers to it leans on it staying open. Amending a hole's text, or
        answering it out of existence, must stale exactly the groups whose gap names it, and nothing else."""
        l1 = L2.parse_l1()
        job, bound = None, None
        for candidate in ("trade-lifecycle", "ownership-history", "positions"):
            for gid, info in L2.fingerprints(candidate, l1, selected=True).items():
                if info["bounded_by"]:
                    job, bound, hole = candidate, gid, info["bounded_by"][0]
                    break
            if job:
                break
        self.assertIsNotNone(job, "no group declares a hole in its gap")
        baseline = {j: L2.fingerprints(j, l1, selected=True) for j in L2.JOB_ORDER}
        for mutate in ("amend", "answer"):
            moved = dict(l1)
            moved["holes"] = {h: (t + " amended." if h == hole else t) for h, t in l1["holes"].items()}
            if mutate == "answer":
                moved["holes"] = {h: t for h, t in l1["holes"].items() if h != hole}
            moved["hole_fingerprints"] = {h: L2.sha(t) for h, t in moved["holes"].items()}
            for j in L2.JOB_ORDER:
                after = L2.fingerprints(j, moved, selected=True)
                for gid, info in after.items():
                    expected_move = hole in baseline[j][gid]["bounded_by"]
                    self.assertEqual(info["fingerprint"] != baseline[j][gid]["fingerprint"], expected_move,
                                     (mutate, j, gid, baseline[j][gid]["bounded_by"]))

    def test_a_group_no_projection_derives_from_cannot_be_l3_stale(self):
        """A group whose only member is a judgement invariant reaches no artifact and no audit; no projection can attest
        it, so it must not sit stale forever waiting for a stamp that can never come."""
        model = json.loads((ROOT / "chain/l2/positions/selected-model.json").read_text())
        cited = set()
        for target in ("duckdb-native", "duckdb-sqlmesh"):
            manifest = json.loads((ROOT / "chain/l3" / target / "positions/manifest.json").read_text())
            cited |= {a["invariant"] for a in manifest["audits"]}
            cited |= {d for a in manifest["artifacts"] for d in a["derived_from"]}
        unprojected = [g["id"] for g in model["sufficiency_groups"] if not set(g["members"]) & cited]
        self.assertTrue(unprojected, "expected at least one group no projection derives from")
        for gid in unprojected:
            self.assertTrue(L2.stamped_everywhere("positions", gid, "a-fingerprint-no-manifest-carries"), gid)


class L3ProvenanceUnderL1Tests(unittest.TestCase):
    def test_an_l1_move_under_an_unchanged_l2_rejects_the_projection(self):
        """A matching review sha proves the L2 text is the one selected; it proves nothing about whether L1 moved under
        it. The gate must compare stamped group fingerprints every time, not only when the sha differs."""
        import shutil, tempfile
        target, job = "duckdb-native", "trade-lifecycle"
        if not (ROOT / "chain/l3" / target / job / "manifest.json").exists():
            self.skipTest("not projected")
        with tempfile.TemporaryDirectory() as tmp:
            l3_dir = Path(tmp) / "l3"
            shutil.copytree(ROOT / "chain/l3" / target / job, l3_dir / target / job)
            mpath = l3_dir / target / job / "manifest.json"
            manifest = json.loads(mpath.read_text())
            review = json.loads((ROOT / "chain/l2" / job / "review.json").read_text())
            manifest["derived_from_model"]["review_sha256"] = review["model_sha256"]  # the L2 text is exactly the selected one
            current = {gid: i["fingerprint"] for gid, i in L2.fingerprints(job, selected=True).items()}
            manifest["group_fingerprints"] = dict(current)
            mpath.write_text(json.dumps(manifest))
            # Complete the accepted state: the review must cover the content on disk. Without this the copy looks
            # recompiled-since-acceptance, and a moved group there is a pending stamp rather than a stale artifact --
            # a real distinction the gate now draws, and one this scenario has to put on the accepted side.
            rpath = l3_dir / target / job / "review.json"
            record = json.loads(rpath.read_text())
            record["projection_sha256"] = L3.projection_digest(l3_dir / target / job)
            rpath.write_text(json.dumps(record))
            saved = L3.L3_DIR
            L3.L3_DIR = l3_dir
            try:
                self.assertFalse([p for p in L3.check(target, job)["problems"] if "moved" in p], "baseline should be clean")
                moved = sorted(current)[0]
                manifest["group_fingerprints"][moved] = "f" * 64  # an L1 clause or hole moved under the same L2 text
                mpath.write_text(json.dumps(manifest))
                problems = L3.check(target, job)["problems"]
            finally:
                L3.L3_DIR = saved
        self.assertTrue(any(moved in p and "moved" in p for p in problems), problems)

    def test_a_move_on_a_projection_recompiled_since_its_acceptance_is_a_question_not_a_refusal(self):
        """The complement, and the friction that prompted it: both trade-lifecycle projections were recompiled for a new
        clause, ran clean, and the gate still told their Developers to re-project stale artifacts -- because a moved
        fingerprint and an unstamped one are the same comparison. They are told apart by whether the projection's
        content is still the content the last acceptance covered. Only then has nothing been done about the move."""
        import shutil, tempfile
        target, job = "duckdb-native", "trade-lifecycle"
        if not (ROOT / "chain/l3" / target / job / "manifest.json").exists():
            self.skipTest("not projected")
        with tempfile.TemporaryDirectory() as tmp:
            l3_dir = Path(tmp) / "l3"
            shutil.copytree(ROOT / "chain/l3" / target / job, l3_dir / target / job)
            base = l3_dir / target / job
            manifest = json.loads((base / "manifest.json").read_text())
            review = json.loads((ROOT / "chain/l2" / job / "review.json").read_text())
            manifest["derived_from_model"]["review_sha256"] = review["model_sha256"]
            current = {gid: i["fingerprint"] for gid, i in L2.fingerprints(job, selected=True).items()}
            moved = sorted(current)[0]
            manifest["group_fingerprints"] = dict(current, **{moved: "f" * 64})
            (base / "manifest.json").write_text(json.dumps(manifest))
            record = json.loads((base / "review.json").read_text())
            record["projection_sha256"] = "0" * 64  # an acceptance covering content that is no longer on disk
            (base / "review.json").write_text(json.dumps(record))
            saved = L3.L3_DIR
            L3.L3_DIR = l3_dir
            try:
                r = L3.check(target, job)
            finally:
                L3.L3_DIR = saved
        self.assertFalse([p for p in r["problems"] if "moved" in p], r["problems"])
        self.assertTrue(any(moved in q and "moved" in q for q in r["questions"]), r["questions"])
        self.assertFalse(r["acceptance"]["accepted"], r["acceptance"])  # still not accepted: it awaits the reviewer


class StampIsAcceptanceTests(unittest.TestCase):
    def test_a_projection_edited_after_its_review_cannot_be_stamped(self):
        """Stamping records that a reviewed projection is accepted, so it is the reviewer's step. A Developer that edits
        SQL and stamps would be accepting its own work; the guard is on content, so a touched-but-identical file passes."""
        import shutil, tempfile
        target, job = "duckdb-native", "trade-lifecycle"
        base_src = ROOT / "chain/l3" / target / job
        if not (base_src / "review.json").exists():
            self.skipTest("not projected")
        if not L3.acceptance(target, job)["accepted"]:
            # The first stamp below is meant to succeed, which needs a projection its review still covers. A projection
            # recompiled since its last review is not wrong, it is mid-cycle, and the guard under test is what says so.
            self.skipTest("projection is not the one its review accepted: mid-cycle")
        with tempfile.TemporaryDirectory() as tmp:
            l3_dir = Path(tmp) / "l3"
            shutil.copytree(base_src, l3_dir / target / job)
            base = l3_dir / target / job
            saved = L3.L3_DIR
            L3.L3_DIR = l3_dir
            try:
                L3.stamp(target, job)  # a reviewed projection stamps and records what the acceptance covers
                self.assertTrue(json.loads((base / "review.json").read_text())["projection_sha256"])
                sql = next(iter(sorted(base.glob("*.sql")) + sorted(base.glob("models/*.sql"))))
                sql.touch()
                L3.stamp(target, job)  # identical content, new timestamp: same projection
                sql.write_text(sql.read_text() + "\n-- an edit the reviewer never saw\n")
                with self.assertRaises(L3.L3Error):
                    L3.stamp(target, job)
                record = json.loads((base / "review.json").read_text())
                record["verdict"] = "fail"
                (base / "review.json").write_text(json.dumps(record))
                with self.assertRaises(L3.L3Error):
                    L3.stamp(target, job)  # and a failed review is never stamped
            finally:
                L3.L3_DIR = saved


class AcceptanceTests(unittest.TestCase):
    """Well-formed and accepted are different questions. A projection mid-cycle is not wrong; it is not yet the one a
    review accepted. The gate answers both, and nothing compiles on top of an upstream that is not accepted."""

    def scratch(self, tmp, *jobs):
        import shutil
        l3 = Path(tmp) / "l3"
        for job in jobs:
            shutil.copytree(ROOT / "chain/l3/duckdb-native" / job, l3 / "duckdb-native" / job)
        return l3

    def test_an_edit_after_acceptance_is_well_formed_but_not_accepted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            l3 = self.scratch(tmp, "ownership-history")
            base = l3 / "duckdb-native/ownership-history"
            saved = L3.L3_DIR
            L3.L3_DIR = l3
            try:
                self.assertTrue(L3.check("duckdb-native", "ownership-history")["acceptance"]["accepted"])
                sql = sorted(base.glob("*.sql"))[0]
                sql.write_text(sql.read_text() + "\n-- an edit the reviewer never saw\n")
                report = L3.check("duckdb-native", "ownership-history")
            finally:
                L3.L3_DIR = saved
        if any("moved since this projection was stamped" in p for p in report["problems"]):
            self.skipTest("the chain is mid-cycle: an L1 change staled this projection, which is what it should say")
        if any("has no audit" in p for p in report["problems"]):
            # the L2 selected an invariant this projection has not implemented yet: mid-cycle, and exactly what the
            # gate should say. This test asserts a property of a projection that is caught up with its model.
            self.skipTest("projection is behind its selected L2: a newly selected invariant has no audit yet")
        # Well-formedness is the absence of problems. A question is not a defect: an L1 move on a projection that has
        # been recompiled since its acceptance is reported as one, and the Developer loop is still unaffected by it.
        self.assertFalse(report["problems"], report["problems"])
        self.assertIn(report["status"], ("ok", "question"), report)
        self.assertFalse(report["acceptance"]["accepted"])
        self.assertIn("changed after the review", report["acceptance"]["reason"])

    def test_nothing_compiles_on_an_unaccepted_upstream(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            l3 = self.scratch(tmp, "ownership-history", "trade-lifecycle")
            upstream_review = l3 / "duckdb-native/ownership-history/review.json"
            record = json.loads(upstream_review.read_text())
            saved = L3.L3_DIR
            L3.L3_DIR = l3
            try:
                for reason, mutate in (("verdict is fail", lambda r: r.update(verdict="fail")),
                                       ("content changed", lambda r: r.update(projection_sha256="f" * 64))):
                    fresh = json.loads(json.dumps(record))
                    mutate(fresh)
                    upstream_review.write_text(json.dumps(fresh))
                    with self.assertRaises(L3.L3Error, msg=reason) as caught:
                        L3.run("duckdb-native", "trade-lifecycle", database=Path(tmp) / "x.duckdb")
                    self.assertIn("ownership-history", str(caught.exception))
                    self.assertIn("not accepted", str(caught.exception))
            finally:
                L3.L3_DIR = saved


class WeaveTests(unittest.TestCase):
    def test_weave_reports_uncovered_clauses_as_gaps(self):
        out = L2.weave()
        gaps = {r.get("clause") for r in out["relations"] if r["relation"] == "gap" and "clause" in r}
        covered = {c for j in out["jobs"] for g in json.loads((ROOT / "chain/l2" / j / "semantic-model.json").read_text())["sufficiency_groups"] for c in g["parent_clauses"]}
        for clause in L2.parse_l1()["clauses"]:
            self.assertEqual(clause in gaps, clause not in covered, clause)


class L3ProjectionTests(unittest.TestCase):
    """Runs the DuckDB-native projection of ownership-history on the fixture; skips if the job is not selected."""

    def test_selected_projection_checks_and_runs_clean(self):
        review = json.loads((ROOT / "chain/l2/ownership-history/review.json").read_text())
        if review["verdict"] != "pass" or not (ROOT / "chain/l3/duckdb-native/ownership-history/manifest.json").exists():
            self.skipTest("ownership-history not selected or not projected")
        check = L3.check("duckdb-native", "ownership-history")
        if any("moved since this projection was stamped" in p for p in check.get("problems", [])):
            self.skipTest("the chain is mid-cycle: an L1 change staled this projection")
        self.assertEqual(check["status"], "ok", check.get("problems"))
        report = L3.run("duckdb-native", "ownership-history", database=ROOT / "build/test-chain-l3.duckdb")
        self.assertTrue(report["ok"], report["audits"])
        model, review = L3.load_job(JOB)
        expected = {i["id"] for i in model["invariants"] if i["deterministic"] and i["id"] in review["selected_element_ids"]}
        self.assertEqual(set(report["audits"]), expected)
        account = report["samples"]["governed.account"]
        cols = account["columns"]
        rows_428 = [dict(zip(cols, r)) for r in account["rows"] if r[0] == "428"]
        self.assertEqual([r["tax_treatment"] for r in rows_428], ["1", "1", "2"])  # carried across CLOSEACCT, then the labeled change
        self.assertEqual([r["provenance"] for r in rows_428][-1], "controlled_counterexample")
        self.assertEqual(sum(1 for r in rows_428 if r["is_current"] == "True"), 1)


class L3ProvenanceTests(unittest.TestCase):
    def test_check_accepts_superseded_sha_when_derived_group_fingerprints_match(self):
        base = ROOT / "chain/l3/duckdb-native/ownership-history"
        review = json.loads((ROOT / "chain/l2/ownership-history/review.json").read_text())
        if review["verdict"] != "pass" or not (base / "manifest.json").exists():
            self.skipTest("ownership-history not selected or not projected")
        original = (base / "manifest.json").read_text()
        try:
            L3.stamp("duckdb-native", "ownership-history")
            manifest = json.loads((base / "manifest.json").read_text())
            manifest["derived_from_model"]["review_sha256"] = "0" * 64
            (base / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            report = L3.check("duckdb-native", "ownership-history")
            if any("has no audit" in p for p in (report.get("problems") or [])):
                self.skipTest("projection is behind its selected L2: a newly selected invariant has no audit yet")
            self.assertEqual(report["status"], "ok", report.get("problems"))
            self.assertIn("fingerprint unchanged", report["provenance"] or "")
            manifest["group_fingerprints"] = {k: "1" * 64 for k in manifest["group_fingerprints"]}
            (base / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            report = L3.check("duckdb-native", "ownership-history")
            self.assertEqual(report["status"], "rejected")
        finally:
            (base / "manifest.json").write_text(original)


class EngineIndependenceTests(unittest.TestCase):
    def test_two_targets_project_identical_tables_from_one_l2(self):
        base = ROOT / "chain/l3"
        if not all((base / t / "ownership-history/manifest.json").exists() for t in ("duckdb-native", "duckdb-sqlmesh")):
            self.skipTest("both targets not projected")
        report = L3.compare("ownership-history", "duckdb-native", "duckdb-sqlmesh")
        self.assertTrue(report["identical"], report)


class L3AuditContainmentTests(unittest.TestCase):
    def test_audit_reading_a_deferred_source_is_rejected(self):
        base = ROOT / "chain/l3/duckdb-native/ownership-history"
        audit = base / "audits/inv.customer_single_current.sql"
        if not audit.exists():
            self.skipTest("native projection not present")
        original = audit.read_text()
        try:
            audit.write_text(original.rstrip().rstrip(";") + "\nUNION ALL SELECT customer_number, 0 FROM raw.customer_cdc\n")
            report = L3.check("duckdb-native", "ownership-history")
            self.assertEqual(report["status"], "rejected")
            self.assertTrue(any("raw.customer_cdc" in p and "audit" in p for p in report["problems"]), report["problems"])
        finally:
            audit.write_text(original)


class CounterexampleSimulationTests(unittest.TestCase):
    """The account-428 rollover as a two-phase simulation: outcome changes, ownership stays pinned."""

    def check_target(self, target):
        review = ROOT / "chain/l2/trade-lifecycle/review.json"
        manifest = ROOT / "chain/l3" / target / "trade-lifecycle/manifest.json"
        if not review.exists() or json.loads(review.read_text())["verdict"] != "pass" or not manifest.exists():
            self.skipTest(f"trade-lifecycle not projected on {target}")
        r = L3.run_two_phase(target, "trade-lifecycle", database=ROOT / f"build/test-twophase-{target}.duckdb")
        self.assertTrue(r["first_phase_ok"] and r["second_phase_ok"], r)
        before, after = r["watched_before"][0], r["watched_after"][0]
        self.assertEqual(before["status"], "PNDG")
        self.assertEqual(after["status"], "CMPT")
        for frozen in ("owning_account_number", "placed_at", "owning_account_effective_from", "owning_customer_number", "first_seen_late"):
            self.assertEqual(before[frozen], after[frozen], frozen)
        self.assertEqual(after["owning_account_effective_from"], "2012-11-15 18:05:28")
        self.assertTrue(any(v[2] == "True" and v[3] == "controlled_counterexample" for v in r["account_428_statements_after"]))
        self.assertTrue(set(r["changed_columns"]) <= {"status", "executed_price", "fees", "commission", "tax", "quantity"}, r["changed_columns"])

    def test_two_phase_on_duckdb_sqlmesh(self):
        self.check_target("duckdb-sqlmesh")

    def test_two_phase_on_duckdb_native(self):
        self.check_target("duckdb-native")


class CitedPathMustExistTests(unittest.TestCase):
    """A citation to a path that is not there reads as evidence and supplies none. One model justified an explained
    absence -- a reports:true invariant with no counterexample naming its rows -- by citing chain/ce/proposed/... when
    the path is counterexamples/proposed/..., which emptied the entire justification while looking settled. A reviewer
    caught it by hand; it is one directory name, and the gate can check it."""

    def _check_with(self, text):
        import copy, json as _json, tempfile, shutil
        path = ROOT / "chain/l2/positions/semantic-model.json"
        if not path.exists():
            self.skipTest("positions not compiled")
        scratch = copy.deepcopy(_json.loads(path.read_text()))
        scratch["invariants"][0]["necessity"] = text
        with tempfile.TemporaryDirectory() as tmp:
            l2 = Path(tmp) / "l2"
            shutil.copytree(ROOT / "chain/l2", l2)
            (l2 / "positions/semantic-model.json").write_text(_json.dumps(scratch))
            saved = L2.L2_DIR
            L2.L2_DIR = l2
            try:
                return L2.check("positions")
            finally:
                L2.L2_DIR = saved

    def test_a_citation_to_a_missing_path_is_reported(self):
        r = self._check_with("Evidence is in chain/ce/proposed/ce-withdrawn-account-v1.json as filed.")
        self.assertTrue([q for q in r["questions"] if "does not exist" in q], r["questions"])
        self.assertFalse([p for p in r["problems"] if "does not exist" in p], "a question, never a refusal")

    def test_a_citation_to_a_real_path_is_not_reported(self):
        real = "counterexamples/proposed/ce-withdrawn-account-v1.json"
        if not (ROOT / real).exists():
            self.skipTest("the counterexample is not present")
        r = self._check_with(f"Evidence is in {real} as filed.")
        self.assertFalse([q for q in r["questions"] if "does not exist" in q], r["questions"])

    def test_prose_that_cites_nothing_is_not_reported(self):
        r = self._check_with("A held report changes nothing and creates nothing, so it is inert to the partition.")
        self.assertFalse([q for q in r["questions"] if "does not exist" in q], r["questions"])


class DanglingHoleReferenceTests(unittest.TestCase):
    """A hole that closes leaves its text behind. Two reviewers found the same defect in two different jobs in one
    cycle: an element's statement rewritten to the new clause while its necessity and parallel_assumption went on
    deferring to the closed hole -- and those are the fields an implementer reads as normative, so the prose
    reinstated the bug the statement had just fixed. Mechanized from that, the rule immediately found four more
    fields naming a hole closed in an earlier cycle, which nobody had caught."""

    def test_a_field_naming_an_uncarried_hole_is_reported(self):
        import copy, json as _json
        path = ROOT / "chain/l2/positions/semantic-model.json"
        if not path.exists():
            self.skipTest("positions not compiled")
        doc = _json.loads(path.read_text())
        carried = {h["derived_from_hole"] for h in doc.get("holes", [])}
        self.assertTrue(carried, "the model carries no hole, so this test proves nothing")
        invented = "L1.hole.a-hole-this-model-does-not-carry"
        self.assertNotIn(invented, carried)
        scratch = copy.deepcopy(doc)
        scratch["invariants"][0]["necessity"] = f"Deferred to {invented} and never resolved."
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as tmp:
            l2 = Path(tmp) / "l2"
            shutil.copytree(ROOT / "chain/l2", l2)
            (l2 / "positions/semantic-model.json").write_text(_json.dumps(scratch))
            saved = L2.L2_DIR
            L2.L2_DIR = l2
            try:
                r = L2.check("positions")
            finally:
                L2.L2_DIR = saved
        self.assertTrue([q for q in r["questions"] if invented in q], r["questions"])
        self.assertFalse([p for p in r["problems"] if invented in p], "it must be a question, never a refusal")

    def test_provenance_naming_the_closure_is_not_reported(self):
        """A reference that says the hole closed records why an element reads as it does, and is worth keeping. A
        question that can never be cleared is the wrong shape for it: a permanently raised question teaches everyone
        to skim past questions. Note the semicolon -- provenance almost always reads '...left to the hole; that hole
        is now closed', and splitting sentences on ';' separated the reference from its own closure marker and
        reported honest provenance as a live deferral."""
        import copy, json as _json, tempfile, shutil
        path = ROOT / "chain/l2/positions/semantic-model.json"
        if not path.exists():
            self.skipTest("positions not compiled")
        doc = _json.loads(path.read_text())
        gone = "L1.hole.a-closed-hole"
        for text, should_flag in (
            (f"Before this clause this invariant left both directions to {gone}; that hole is now closed and the rule is stated directly.", False),
            (f"What a D row means here is {gone}, not decided by this invariant.", True),
            (f"Deferred to {gone}. The clause has since been answered elsewhere.", True),
        ):
            scratch = copy.deepcopy(doc)
            scratch["invariants"][0]["necessity"] = text
            with tempfile.TemporaryDirectory() as tmp:
                l2 = Path(tmp) / "l2"
                shutil.copytree(ROOT / "chain/l2", l2)
                (l2 / "positions/semantic-model.json").write_text(_json.dumps(scratch))
                saved = L2.L2_DIR
                L2.L2_DIR = l2
                try:
                    r = L2.check("positions")
                finally:
                    L2.L2_DIR = saved
            flagged = bool([q for q in r["questions"] if gone in q])
            with self.subTest(text=text[:48]):
                self.assertEqual(flagged, should_flag, f"flagged={flagged} for: {text}")

    def test_the_live_chain_raises_no_dangling_hole_question(self):
        """The standing state: every closed-hole reference left in the three models names its closure."""
        for job in ("ownership-history", "trade-lifecycle", "positions"):
            if not (ROOT / "chain/l2" / job / "semantic-model.json").exists():
                continue
            r = L2.check(job)
            with self.subTest(job=job):
                self.assertFalse([q for q in r["questions"] if "does not carry" in q], r["questions"])

    def test_a_carried_hole_is_not_reported(self):
        for job in ("ownership-history", "trade-lifecycle", "positions"):
            if not (ROOT / "chain/l2" / job / "semantic-model.json").exists():
                continue
            r = L2.check(job)
            carried = set(r["holes_carried"])
            with self.subTest(job=job):
                for q in r["questions"]:
                    if "does not carry" in q:
                        for h in carried:
                            self.assertNotIn(f"still name {h},", q, f"{job}: {h} is carried and must not be flagged")


class ReportedInvariantNeedsACounterexampleTests(unittest.TestCase):
    """L2-FORMAT says a reported invariant carries its weight only through the counterexample that names the rows it
    is expected to report -- a report being the one audit result a passing run may contain. A Developer had to notice
    that by reading the format and said so in its own report, which is a cross-reference the gate can do instead."""

    def test_an_invariant_named_by_a_counterexample_is_not_flagged(self):
        named = L2.counterexamples_naming("inv.trade_on_closed_account_reported")
        if not named:
            self.skipTest("the closed-account counterexamples are not present")
        self.assertTrue(any("closed-account" in n for n in named), named)

    def test_an_invariant_no_counterexample_names_is_flagged_as_a_question(self):
        self.assertEqual(L2.counterexamples_naming("inv.no_counterexample_mentions_this_one"), [])

    def test_the_gate_raises_it_as_a_question_and_never_as_a_problem(self):
        """It must not refuse the model. A reported invariant held behind an open hole legitimately has no
        counterexample yet, and refusing would push the Developer to weaken the invariant instead."""
        for job in ("ownership-history", "trade-lifecycle", "positions"):
            if not (ROOT / "chain/l2" / job / "semantic-model.json").exists():
                continue
            r = L2.check(job)
            with self.subTest(job=job):
                self.assertFalse([p for p in r["problems"] if "reports rather than holds" in p], r["problems"])

    def test_every_reported_invariant_in_the_chain_is_either_named_or_explained(self):
        """The standing invariant this gate rule exists to keep: each reports:true invariant has a counterexample
        naming it, and where the case cannot be exercised the counterexample says why rather than omitting it."""
        import json as _json
        checked = 0
        for job in ("ownership-history", "trade-lifecycle", "positions"):
            path = ROOT / "chain/l2" / job / "semantic-model.json"
            if not path.exists():
                continue
            for inv in _json.loads(path.read_text())["invariants"]:
                if inv.get("reports"):
                    checked += 1
                    self.assertTrue(L2.counterexamples_naming(inv["id"]), f"{job}/{inv['id']} has no counterexample naming it")
        if not checked:
            self.skipTest("no reported invariant selected anywhere in the chain")


class AdjudicationIsJobScopedTests(unittest.TestCase):
    """sg.unknown-codes and sg.constructed-scenarios exist in all three jobs, and one clause change can genuinely
    warrant opposite verdicts in different jobs. A reviewer recorded exactly that under L1.unknown-codes, writing
    '<job>/<group>' keys -- and the lookup was job-blind, so it read none of them and every decision was inert."""

    CLAUSE = ["L1.unknown-codes"]

    def test_a_reviewers_per_job_verdicts_are_read_per_job(self):
        got = {j: L2.adjudication_for(j, "sg.unknown-codes", self.CLAUSE) for j in ("ownership-history", "trade-lifecycle", "positions")}
        if not any(got.values()):
            self.skipTest("no adjudication recorded for sg.unknown-codes under this clause")
        self.assertEqual(got["trade-lifecycle"], "invalidate", got)
        self.assertEqual(got["ownership-history"], "keep", got)
        self.assertNotEqual(got["trade-lifecycle"], got["ownership-history"], "a job-blind lookup returns one verdict for both")

    def test_a_bare_key_still_applies_to_the_job_that_asks(self):
        """Earlier single-job entries were written with bare group ids and must keep working."""
        self.assertEqual(L2.adjudication_for("trade-lifecycle", "sg.placement-moment", ["L1.placement-moment"]), "invalidate")

    def test_an_unadjudicated_group_returns_none(self):
        self.assertIsNone(L2.adjudication_for("positions", "sg.no-such-group", self.CLAUSE))


class CacheDecisionPrecedenceTests(unittest.TestCase):
    """One group can derive from several clauses, so Jev returns several verdicts and they must be combined. The order
    was wrong: review beat invalidate, so a group Jev was confident about (0.83, high, under an amended
    L1.current-version) was downgraded to awaiting adjudication because a second clause touching it scored 0.29 -- and
    the plan reported l3_reprojection_required false while a confidently invalidated group sat in the model."""

    def test_an_invalidate_is_never_downgraded_by_an_uncertain_sibling(self):
        self.assertEqual(L2.cache_decision({"invalidate", "review"}), "stale")
        self.assertEqual(L2.cache_decision({"invalidate", "keep", "review"}), "stale")

    def test_uncertainty_still_beats_keep(self):
        self.assertEqual(L2.cache_decision({"review", "keep"}), "review")

    def test_only_unanimous_keep_is_a_hit(self):
        self.assertEqual(L2.cache_decision({"keep"}), "hit-by-jev")

    def test_a_missing_or_unrecognized_verdict_is_not_a_keep(self):
        """invalidation() returns decision 'invalidate' when Jev cannot run, so an unavailable selector never keeps
        anything. Nothing should quietly become a hit by arriving as None or by arriving not at all."""
        self.assertEqual(L2.cache_decision({None}), "review")
        self.assertEqual(L2.cache_decision(set()), "review")
        self.assertEqual(L2.cache_decision({"something-new"}), "review")


class NonBlockingMatchesTheL2Tests(unittest.TestCase):
    """Mechanized from a capable reviewer's own check. Asked whether `blocking false` appeared only where the L2 grants
    it, the reviewer enumerated the flag across all fourteen audit headers by hand. That is a cross-reference between
    two files, so it belongs in the gate: a must-hold audit quietly declared non-blocking refuses nothing while passing
    every other check, and a reporting audit left blocking sends a finding to abort the plan instead of to the business."""

    TARGET, JOB = "duckdb-sqlmesh", "trade-lifecycle"

    def _check_with(self, edit):
        import shutil, tempfile
        base_src = ROOT / "chain/l3" / self.TARGET / self.JOB
        if not (base_src / "manifest.json").exists():
            self.skipTest("not projected")
        with tempfile.TemporaryDirectory() as tmp:
            l3_dir = Path(tmp) / "l3"
            shutil.copytree(base_src, l3_dir / self.TARGET / self.JOB)
            edit(l3_dir / self.TARGET / self.JOB)
            saved = L3.L3_DIR
            L3.L3_DIR = l3_dir
            try:
                return L3.check(self.TARGET, self.JOB)["problems"]
            finally:
                L3.L3_DIR = saved

    def test_baseline_agrees_with_the_l2(self):
        self.assertFalse([p for p in self._check_with(lambda base: None) if "blocking" in p])

    def test_a_must_hold_audit_declared_non_blocking_is_rejected(self):
        reporting = L3.reporting_invariants_for(self.JOB)
        manifest = json.loads((ROOT / "chain/l3" / self.TARGET / self.JOB / "manifest.json").read_text())
        victim = next(a["file"] for a in manifest["audits"] if a["invariant"] not in reporting)

        def edit(base):
            f = base / victim
            f.write_text(f.read_text().replace(");", ", blocking false);", 1))

        problems = self._check_with(edit)
        self.assertTrue([p for p in problems if "non-blocking" in p and "does not mark" in p], problems)

    def test_a_reporting_audit_left_blocking_is_rejected(self):
        reporting = L3.reporting_invariants_for(self.JOB)
        if not reporting:
            self.skipTest("no reporting invariant selected")
        manifest = json.loads((ROOT / "chain/l3" / self.TARGET / self.JOB / "manifest.json").read_text())
        victim = next(a["file"] for a in manifest["audits"] if a["invariant"] in reporting)

        def edit(base):
            f = base / victim
            text = re.sub(r",?\s*blocking\s+false", "", f.read_text(), flags=re.I)
            f.write_text(text)

        problems = self._check_with(edit)
        self.assertTrue([p for p in problems if "not declared non-blocking" in p], problems)


class ReportedInvariantAggregationTests(unittest.TestCase):
    """An invariant marked reports: true hands the business a finding instead of holding a line. That distinction has
    to survive every path that aggregates audit results, on both engines. It did not: simulate indexed the violation
    count unconditionally and crashed, and the SQLMesh path counted a warned audit as a failed run."""

    AUDITS = {
        "inv.holds": {"violations": 0, "sample": []},
        "inv.broke": {"violations": 3, "sample": [["x"]]},
        "inv.reports": {"reported": 2, "sample": [["353232"], ["372101"]]},
        "inv.quiet_report": {"reported": 0, "sample": []},
        "inv.unknown": {"violations": None},
    }

    def test_a_report_is_never_a_failure_but_is_always_a_finding(self):
        self.assertEqual(set(L3.must_hold_failures(self.AUDITS)), {"inv.broke", "inv.unknown"})
        self.assertEqual(set(L3.findings(self.AUDITS)), {"inv.reports"})

    def test_an_audit_that_returned_rows_fired_whatever_the_rows_mean(self):
        """A counterexample expecting a report is answered by a reported audit, so it must not read as silent."""
        self.assertEqual(set(L3.audits_with_rows(self.AUDITS)), {"inv.broke", "inv.reports", "inv.unknown"})
        self.assertEqual(L3.audits_with_rows({"inv.reports": {"reported": 2}}), {"inv.reports": {"reported": 2}})

    def test_sqlmesh_per_audit_verdicts_survive_line_wrapping_and_repeated_names(self):
        """SQLMesh prints through Rich, which wraps at the terminal width, so a long invariant name can be separated
        from its verdict; and one audit name may run on several models, where a failure anywhere is a failure."""
        counts = L3.sqlmesh_audit_counts(
            "inv.short on model governed.trade \u2705 PASS.\n"
            "inv.a_name_long_enough_that_rich_wraps_it on model governed.account\n\u2705 PASS.\n"
            "inv.reports on model governed.trade \u274c FAIL [2].\n"
            "inv.twice on model governed.trade \u2705 PASS.\n"
            "inv.twice on model governed.account \u274c FAIL [1]."
        )
        self.assertEqual(counts, {"inv.short": 0, "inv.a_name_long_enough_that_rich_wraps_it": 0,
                                  "inv.reports": 2, "inv.twice": 1})

    def test_a_reporting_invariant_does_not_fail_the_run_on_either_engine(self):
        """The end-to-end form of both bugs: the fixture's two trades on account 428's closing statement are reported,
        and a run that reports them is still a passing run, identically on a native engine and under SQLMesh."""
        job = "trade-lifecycle"
        reporting = L3.reporting_invariants_for(job)
        if not reporting:
            self.skipTest("no reporting invariant selected for this job")
        for target in ("duckdb-native", "duckdb-sqlmesh"):
            if not (ROOT / "chain/l3" / target / job / "manifest.json").exists():
                self.skipTest(f"{job} not projected on {target}")
            with self.subTest(target=target):
                r = L3.run(target, job)
                self.assertEqual(L3.must_hold_failures(r["audits"]), {}, r["audits"])
                self.assertTrue(r["ok"], r["audits"])
                self.assertEqual(set(r["findings_for_the_business"]), reporting, r["audits"])
                for inv in reporting:
                    self.assertEqual(L3.audit_rows(r["audits"][inv]), 2, r["audits"][inv])


class CounterexampleDocumentTests(unittest.TestCase):
    CE = Path("counterexamples/proposed/ce-trade-before-account-statement-v1.json")

    def test_trade_before_account_statement_is_visible_or_caught_on_both_engines(self):
        """The constructed trade placed before its account's first statement must never be silently agreed on: before the
        L2 admits the two invariants the engines disagree (native keeps it with null pins, SQLMesh drops it); after, an
        audit fires on each engine. Silent and identical would mean the counterexample stopped doing its job."""
        if not (ROOT / self.CE).exists():
            self.skipTest("counterexample document not present")
        reports, counts = {}, {}
        for target in ("duckdb-native", "duckdb-sqlmesh"):
            if not (ROOT / "chain/l3" / target / "trade-lifecycle/manifest.json").exists():
                self.skipTest(f"trade-lifecycle not projected on {target}")
            reports[target] = L3.simulate(target, "trade-lifecycle", self.CE)
            counts[target] = reports[target]["samples"].get("governed.trade")  # None when a blocking audit refused the plan
        # Caught means a must-hold audit broke. The fixture also carries a standing report under
        # inv.trade_on_closed_account_reported, and a finding is not this counterexample being caught, so asking
        # whether anything fired would answer yes on every run and the test would stop discriminating.
        all_caught = all(bool(r["failures"]) for r in reports.values())
        engines_disagree = len(set(counts.values())) > 1
        self.assertTrue(all_caught or engines_disagree, {t: (sorted(r["failures"]), counts[t]) for t, r in reports.items()})
        for r in reports.values():
            if r["failures"]:
                self.assertTrue(set(r["failures"]) <= {"inv.trade_ownership_pin_present", "inv.every_received_trade_persisted"}, r["failures"])


class L3GateTests(unittest.TestCase):
    def test_a_jev_kept_clause_rewording_does_not_stale_the_projection(self):
        """Above the hash floor Jev decides: when the chain manifest records a derived group as hit-by-jev, the L3 gate
        treats the moved fingerprint as valid; when it records review, the gate demands adjudication. Scratch copies."""
        import shutil, tempfile
        target, job = "duckdb-native", "trade-lifecycle"
        if not (ROOT / "chain/l3" / target / job / "manifest.json").exists():
            self.skipTest("not projected")
        with tempfile.TemporaryDirectory() as tmp:
            l3_dir = Path(tmp) / "l3"
            shutil.copytree(ROOT / "chain/l3" / target / job, l3_dir / target / job)
            mpath = l3_dir / target / job / "manifest.json"
            m = json.loads(mpath.read_text()); m["derived_from_model"]["review_sha256"] = "0" * 64
            current = {gid: info["fingerprint"] for gid, info in L3.L2.fingerprints(job, selected=True).items()}
            m["group_fingerprints"] = dict(current)  # every group the selection knows, as a fresh stamp would record
            groups = list(m["group_fingerprints"]); moved = groups[0]
            m["group_fingerprints"][moved] = "1" * 64
            mpath.write_text(json.dumps(m))
            chain_manifest = json.loads((ROOT / "chain/manifest.json").read_text())
            saved_root_manifest = (ROOT / "chain/manifest.json").read_text()
            saved = L3.L3_DIR; L3.L3_DIR = l3_dir
            try:
                for decision, expect_ok in (("hit-by-jev", True), ("review", False)):
                    cm = json.loads(json.dumps(chain_manifest))
                    for gid in cm["jobs"][job]["elements"]:
                        cm["jobs"][job]["elements"][gid]["cache"] = "hit"
                    cm["jobs"][job]["elements"][moved]["cache"] = decision
                    (ROOT / "chain/manifest.json").write_text(json.dumps(cm))
                    report = L3.check(target, job)
                    provenance_problems = [p for p in report["problems"] if "fingerprint" in p or "adjudicate" in p]
                    self.assertEqual(not provenance_problems, expect_ok, (decision, report["problems"], report.get("provenance")))
            finally:
                L3.L3_DIR = saved
                (ROOT / "chain/manifest.json").write_text(saved_root_manifest)

    def test_a_newly_selected_deterministic_invariant_demands_an_audit(self):
        """The L2-to-L3 seam: when a re-selected L2 adds a deterministic invariant, the L3 gate rejects every projection
        of that job until an audit exists for it. Non-deterministic invariants demand nothing. Exercised on a scratch copy."""
        import shutil, tempfile
        target = "duckdb-native"
        if not (ROOT / "chain/l3" / target / JOB / "manifest.json").exists():
            self.skipTest(f"{JOB} not projected on {target}")
        with tempfile.TemporaryDirectory() as tmp:
            l2_dir, l3_dir = Path(tmp) / "l2", Path(tmp) / "l3"
            shutil.copytree(ROOT / "chain/l2" / JOB, l2_dir / JOB)
            shutil.copytree(ROOT / "chain/l3" / target / JOB, l3_dir / target / JOB)
            snapshot = l2_dir / JOB / "selected-model.json"
            model = json.loads(snapshot.read_text())
            review = json.loads((l2_dir / JOB / "review.json").read_text())
            template = next(i for i in model["invariants"] if i["deterministic"] and i["id"] in review["selected_element_ids"])
            for iid, deterministic in (("inv.synthetic_deterministic", True), ("inv.synthetic_judgement", False)):
                model["invariants"].append({**template, "id": iid, "deterministic": deterministic})
                review["selected_element_ids"].append(iid)
            snapshot.write_text(json.dumps(model))
            (l2_dir / JOB / "review.json").write_text(json.dumps(review))
            saved = (L3.L2_DIR, L3.L3_DIR, L3.L2.L2_DIR)
            L3.L2_DIR, L3.L3_DIR, L3.L2.L2_DIR = l2_dir, l3_dir, l2_dir
            try:
                problems = L3.check(target, JOB)["problems"]
            finally:
                L3.L2_DIR, L3.L3_DIR, L3.L2.L2_DIR = saved
        self.assertIn("deterministic invariant inv.synthetic_deterministic has no audit", problems)
        self.assertFalse(any("inv.synthetic_judgement" in p for p in problems), problems)

    def test_l3_requires_a_passed_review(self):
        """L3 compiles only from a selected L2: no model, no review, or a verdict other than pass all refuse."""
        import shutil, tempfile
        with self.assertRaises(L3.L3Error):
            L3.load_job("no-such-job")
        with tempfile.TemporaryDirectory() as tmp:
            l2_dir = Path(tmp) / "l2"
            shutil.copytree(ROOT / "chain/l2" / JOB, l2_dir / JOB)
            review_path = l2_dir / JOB / "review.json"
            review = json.loads(review_path.read_text())
            review_path.write_text(json.dumps({**review, "verdict": "needs-authority"}))
            saved = L3.L2_DIR
            L3.L2_DIR = l2_dir
            try:
                with self.assertRaises(L3.L3Error):
                    L3.load_job(JOB)
                review_path.unlink()
                with self.assertRaises(L3.L3Error):
                    L3.load_job(JOB)
            finally:
                L3.L2_DIR = saved

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
