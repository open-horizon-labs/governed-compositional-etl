"""Mutation-role guard and role-derived MERGE projection for the incremental DimTrade slice."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from sqlglot import parse_one

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GUARD = load("merge_guard", "scripts/merge_guard.py")
COMPILER = load("compile_incremental", "scripts/compile_incremental.py")
TYPES = json.loads((ROOT / COMPILER.TYPES).read_text())
LOGICAL = json.loads((ROOT / COMPILER.LOGICAL).read_text())
ROLES = GUARD.column_roles(LOGICAL, GUARD.load_roles(TYPES))
TARGET = "dim_trade_incremental"

NAIVE_MERGE = """
MERGE INTO governed.dim_trade_incremental AS t USING (SELECT * FROM staged) AS s ON t.trade_id = s.trade_id
WHEN MATCHED THEN UPDATE SET status_id = s.status_id, trade_price = s.trade_price, fee = s.fee, commission = s.commission, tax = s.tax,
  sk_account_id = s.sk_account_id, sk_customer_id = s.sk_customer_id
WHEN NOT MATCHED THEN INSERT VALUES (s.trade_id, s.sk_account_id, s.sk_customer_id, s.status_id, s.quantity, s.bid_price, s.trade_price, s.fee, s.commission, s.tax)
"""
RESTRICTED_MERGE = """
MERGE INTO governed.dim_trade_incremental AS t USING (SELECT * FROM staged) AS s ON t.trade_id = s.trade_id
WHEN MATCHED THEN UPDATE SET status_id = s.status_id, quantity = s.quantity, bid_price = s.bid_price, trade_price = s.trade_price, fee = s.fee, commission = s.commission, tax = s.tax
WHEN NOT MATCHED THEN INSERT VALUES (s.trade_id, s.sk_account_id, s.sk_customer_id, s.status_id, s.quantity, s.bid_price, s.trade_price, s.fee, s.commission, s.tax)
"""


class RoleRegistryTests(unittest.TestCase):
    def test_roles_derive_surface_from_types_only(self):
        surface = GUARD.update_surface(ROLES)
        self.assertEqual(surface["identity"], ["trade_id"])
        self.assertEqual(surface["frozen"], ["sk_account_id", "sk_customer_id"])
        self.assertNotIn("sk_account_id", surface["mutable"])
        self.assertIn("status_id", surface["mutable"])

    def test_role_on_a_column_name_is_rejected(self):
        logical = json.loads(json.dumps(LOGICAL))
        logical["attributes"][1]["mutation_role"] = "mutable"
        with self.assertRaisesRegex(GUARD.GuardError, "roles attach to semantic types"):
            GUARD.column_roles(logical, GUARD.load_roles(TYPES))

    def test_unknown_role_and_v1_registry_are_rejected(self):
        types = json.loads(json.dumps(TYPES))
        types["types"][0]["mutation_role"] = "sometimes"
        with self.assertRaises(GUARD.GuardError):
            GUARD.load_roles(types)
        v1 = json.loads((ROOT / "contracts/semantic-types/trade-types-v1.json").read_text())
        with self.assertRaises(GUARD.GuardError):
            GUARD.load_roles(v1)

    def test_frozen_role_is_reused_across_two_types_and_two_columns(self):
        frozen_types = {t["id"] for t in TYPES["types"] if t["mutation_role"] == GUARD.FROZEN}
        self.assertGreaterEqual(len(frozen_types), 2)


class GuardTests(unittest.TestCase):
    def verdict(self, sql):
        return GUARD.guard_sql(sql, ROLES, TARGET)

    def test_naive_merge_is_rejected_with_role_named(self):
        verdict = self.verdict(NAIVE_MERGE)
        self.assertFalse(verdict.ok)
        self.assertEqual({w["column"] for w in verdict.attempted_writes}, {"sk_account_id", "sk_customer_id"})
        self.assertTrue(all(w["semantic_role"] == GUARD.FROZEN for w in verdict.attempted_writes))
        text = GUARD.diagnosis(verdict, COMPILER.DESCENDANTS)
        self.assertIn("Incremental lifecycle contract  FAIL", text)
        self.assertIn("Holdings attribution path       AFFECTED", text)

    def test_conventional_restricted_merge_passes(self):
        verdict = self.verdict(RESTRICTED_MERGE)
        self.assertTrue(verdict.ok, verdict.attempted_writes)
        self.assertIn("UNAFFECTED", GUARD.diagnosis(verdict, COMPILER.DESCENDANTS))

    def test_alias_qualified_and_expression_assignments_are_rejected(self):
        sql = RESTRICTED_MERGE.replace("tax = s.tax", "tax = s.tax, t.sk_account_id = COALESCE(s.sk_account_id, t.sk_account_id)")
        verdict = self.verdict(sql)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.attempted_writes[0]["column"], "sk_account_id")

    def test_matched_delete_then_insert_is_a_rebind_by_other_means(self):
        sql = """
        MERGE INTO governed.dim_trade_incremental AS t USING staged AS s ON t.trade_id = s.trade_id
        WHEN MATCHED THEN DELETE
        WHEN NOT MATCHED THEN INSERT VALUES (s.trade_id, s.sk_account_id, s.sk_customer_id, s.status_id, s.quantity, s.bid_price, s.trade_price, s.fee, s.commission, s.tax)
        """
        verdict = self.verdict(sql)
        self.assertFalse(verdict.ok)
        self.assertEqual({w["via"] for w in verdict.attempted_writes}, {"matched_delete_then_not_matched_insert"})

    def test_plain_update_and_delete_reinsert_outside_merge_are_rejected(self):
        update = "UPDATE governed.dim_trade_incremental SET sk_account_id = 428002 WHERE trade_id = 372101"
        self.assertFalse(self.verdict(update).ok)
        mutable_update = "UPDATE governed.dim_trade_incremental SET status_id = 'CMPT' WHERE trade_id = 372101"
        self.assertTrue(self.verdict(mutable_update).ok)
        script = "DELETE FROM governed.dim_trade_incremental WHERE trade_id = 372101; INSERT INTO governed.dim_trade_incremental SELECT * FROM staged"
        self.assertFalse(self.verdict(script).ok)

    def test_insert_on_conflict_do_update_frozen_is_rejected(self):
        sql = """INSERT INTO governed.dim_trade_incremental SELECT * FROM staged
        ON CONFLICT (trade_id) DO UPDATE SET status_id = excluded.status_id, sk_account_id = excluded.sk_account_id"""
        verdict = self.verdict(sql)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.attempted_writes[0]["via"], "insert_on_conflict_do_update")

    def test_compiler_built_merge_passes_and_contains_only_mutable_columns(self):
        merge = GUARD.build_merge(f"governed.{TARGET}", "SELECT * FROM staged", ROLES)
        self.assertTrue(GUARD.guard_merge(merge, ROLES).ok)
        sql = merge.sql(dialect="duckdb")
        matched = sql.split("WHEN MATCHED THEN UPDATE SET")[1].split("WHEN NOT MATCHED")[0]
        self.assertNotIn("sk_account_id", matched)
        self.assertNotIn("sk_customer_id", matched)
        self.assertIn("status_id", matched)
        parse_one(sql, dialect="duckdb")


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="incremental-projection-"))

    def tearDown(self):
        shutil.rmtree(self.temp)

    def test_compile_is_deterministic_and_reads_no_ce_context(self):
        first = COMPILER.compile_projection(self.temp / "a", database=self.temp / "db.duckdb", retain=False)
        second = COMPILER.compile_projection(self.temp / "b", database=self.temp / "db.duckdb", retain=False)
        self.assertEqual(first["projection_sha256"], second["projection_sha256"])
        self.assertTrue(first["guard"]["ok"])
        self.assertEqual(first["update_surface"]["frozen"], ["sk_account_id", "sk_customer_id"])
        self.assertIn("counterexamples/archive/", first["excluded_context"])
        self.assertTrue(all(not p.startswith("counterexamples/") for p in [i["path"] for i in first["compiler_inputs"]]))
        model = (self.temp / "a/models/dim_trade_incremental.sql").read_text()
        self.assertIn("'frozen_columns' = 'sk_account_id, sk_customer_id'", model)
        self.assertNotIn("sk_account_id", model.split("'mutable_columns' = '")[1].split("'")[0])
        self.assertIn("kind CUSTOM", model)
        self.assertIn("workaround", json.dumps(first).lower())

    def test_preflight_rejects_policy_restated_or_moved_into_projection(self):
        inputs = COMPILER.load_inputs()
        edge = json.loads(json.dumps(inputs[COMPILER.EDGE]))
        edge["history_policy"]["mutable_columns"] = "status_id"
        with self.assertRaisesRegex(COMPILER.ProjectionError, "restates a column list"):
            COMPILER.preflight({**inputs, COMPILER.EDGE: edge})
        sketch = inputs[COMPILER.SKETCH].replace("## Projection workaround (not policy)", "## Notes")
        with self.assertRaisesRegex(COMPILER.ProjectionError, "Projection workaround"):
            COMPILER.preflight({**inputs, COMPILER.SKETCH: sketch})
        logical = json.loads(json.dumps(inputs[COMPILER.LOGICAL]))
        logical["holes"] = [h for h in logical["holes"] if h["id"] != "incremental.authority-locator"]
        with self.assertRaisesRegex(COMPILER.ProjectionError, "authority-locator"):
            COMPILER.preflight({**inputs, COMPILER.LOGICAL: logical})
        types = json.loads(json.dumps(inputs[COMPILER.TYPES]))
        for item in types["types"]:
            if item["id"] == "customer_surrogate_key":
                item["mutation_role"] = "mutable"
        with self.assertRaisesRegex(COMPILER.ProjectionError, "at least two columns"):
            COMPILER.preflight({**inputs, COMPILER.TYPES: types})


class CounterexampleExecutionTests(unittest.TestCase):
    """Runs SQLMesh on DuckDB; the account-428 rollover is a labeled constructed counterexample."""

    CE = ROOT / "counterexamples/archive/ce-account-428-rollover-v1.json"

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="incremental-ce-"))

    def tearDown(self):
        shutil.rmtree(self.temp)

    def test_rollover_before_completion_keeps_first_encounter_keys(self):
        result = COMPILER.run_counterexample(self.CE, self.temp)
        self.assertEqual(result["before"]["sk_account_id"], 428001)
        self.assertEqual(result["before"]["status_id"], "PNDG")
        after, expected = result["after"], result["expected"]
        self.assertEqual(after["sk_account_id"], expected["sk_account_id"])
        self.assertEqual(after["sk_customer_id"], expected["sk_customer_id"])
        self.assertEqual(after["status_id"], "CMPT")
        self.assertEqual(float(after["trade_price"]), expected["trade_price"])
        self.assertEqual(float(after["tax"]), expected["tax"])
        self.assertTrue(result["audit_ok"], result["audit_stdout"])

    def test_hand_edited_projection_with_frozen_in_mutable_fails_before_writing(self):
        ce = json.loads(self.CE.read_text())
        database, project = self.temp / "ce.duckdb", self.temp / "projection"
        COMPILER.load_counterexample_database(database, ce["fixture"], "first_encounter")
        COMPILER.compile_projection(project, database=database, retain=False)
        COMPILER.plan(project)
        model = project / "models/dim_trade_incremental.sql"
        model.write_text(model.read_text().replace("'mutable_columns' = 'status_id", "'mutable_columns' = 'sk_account_id, status_id"))
        shutil.rmtree(project / ".cache", ignore_errors=True)  # SQLMesh caches parsed models by mtime; the edit lands within one second
        COMPILER.swap_cdc(database, ce["fixture"])
        # A restatement plan reuses prod snapshots and ignores local edits; the edit itself is the change that plans.
        with self.assertRaisesRegex(COMPILER.ProjectionError, "frozen_from_first_encounter"):
            COMPILER.plan(project)
        self.assertEqual(COMPILER.read_row(database, 372101)["sk_account_id"], 428001)

    def test_naive_merge_that_bypasses_the_guard_fails_the_deterministic_gate(self):
        import duckdb
        ce = json.loads(self.CE.read_text())
        database, project = self.temp / "ce.duckdb", self.temp / "projection"
        COMPILER.load_counterexample_database(database, ce["fixture"], "first_encounter")
        COMPILER.compile_projection(project, database=database, retain=False)
        COMPILER.plan(project)
        COMPILER.swap_cdc(database, ce["fixture"])
        con = duckdb.connect(str(database))
        try:
            table = con.execute("SELECT table_schema || '.' || table_name FROM information_schema.tables WHERE table_name LIKE 'governed__dim_trade_incremental%' AND table_schema LIKE 'sqlmesh%'").fetchone()[0]
            con.execute(f"UPDATE {table} SET sk_account_id = 428002, status_id = 'CMPT' WHERE trade_id = 372101")
        finally:
            con.close()
        audited = COMPILER.audit(project)
        self.assertIn("frozen_keys_bound_once", audited.stdout + audited.stderr)
        self.assertNotIn("0 audit errors", audited.stdout)


if __name__ == "__main__":
    unittest.main()
