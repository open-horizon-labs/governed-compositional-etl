import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from sqlglot import exp, parse_one
from sqlmesh.core.context import Context


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compile_projection", ROOT / "scripts/compile_projection.py"
)
COMPILER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPILER)


class GovernedProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="issue5-projection-"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_compiler_emits_loadable_sqlmesh_project_and_sqlglot_asts(self):
        manifest = COMPILER.compile_projection(self.temp_dir, retain=False)
        COMPILER.verify_manifest(manifest, self.temp_dir)
        context = Context(paths=self.temp_dir / "arms/native")
        self.assertEqual(len(context.models), 6)
        self.assertEqual(manifest["dependencies"]["sqlmesh"], "0.236.1")
        self.assertEqual(manifest["dependencies"]["sqlglot"], "30.8.0")
        self.assertEqual(manifest["dependencies"]["duckdb"], "1.5.5")
        for details in manifest["policy_expressions"].values():
            expression = parse_one(details["rendered_sql"], dialect="duckdb")
            self.assertIsInstance(expression, exp.Expression)
            self.assertEqual(expression.__class__.__name__, details["ast_class"])

    def test_manifest_has_rule_to_model_expression_and_audit_lineage(self):
        manifest = COMPILER.compile_projection(self.temp_dir, retain=False)
        authorities = {
            authority
            for entry in manifest["lineage"]
            for authority in entry["authority"]
        }
        self.assertTrue(
            {
                "tpc-di-1.1.0-2.2.2.13",
                "tpc-di-1.1.0-2.2.2.16",
                "tpc-di-1.1.0-2.2.2.17",
                "tpc-di-1.1.0-2.2.2.18",
                "tpc-di-1.1.0-4.5.8.1",
                "tpc-di-1.1.0-4.5.8.2-create-close",
            }
            <= authorities
        )
        lifecycle = next(
            entry
            for entry in manifest["lineage"]
            if "tpc-di-1.1.0-4.5.8.2-create-close" in entry["authority"]
        )
        self.assertEqual(
            lifecycle["expressions"],
            ["trade_close_timestamp", "trade_creation_timestamp"],
        )
        self.assertIn("valid_lifecycle_order", lifecycle["audits"])
        self.assertEqual(
            manifest["acceptance"]["sketch_review"],
            "required_separately_against_sketches/trade-dim-v1.md",
        )

    def test_fresh_projection_uses_no_oracle_or_ce_context(self):
        first = COMPILER.compile_projection(self.temp_dir, retain=False)
        shutil.rmtree(self.temp_dir)
        second = COMPILER.compile_projection(self.temp_dir, retain=False)
        self.assertEqual(first, second)
        paths = [item["path"] for item in second["compiler_inputs"]]
        self.assertEqual(paths, list(COMPILER.GOVERNING_INPUTS))
        self.assertFalse(any(path.startswith("oracle/") for path in paths))
        self.assertFalse(any("counterexamples/archive" in path for path in paths))
        self.assertFalse(any("held-out" in path for path in paths))

    def test_three_arms_are_byte_equivalent(self):
        manifest = COMPILER.compile_projection(self.temp_dir, retain=False)
        hashes = {
            details["projection_sha256"] for details in manifest["arms"].values()
        }
        self.assertEqual(len(hashes), 1)
        trees = []
        for arm in COMPILER.ARMS:
            project = self.temp_dir / "arms" / arm
            trees.append(
                {
                    path.relative_to(project).as_posix(): path.read_bytes()
                    for path in project.rglob("*")
                    if path.is_file()
                }
            )
        self.assertEqual(trees[0], trees[1])
        self.assertEqual(trees[1], trees[2])

    def test_retained_manifest_matches_fresh_compilation(self):
        retained = json.loads(COMPILER.RETAINED_MANIFEST.read_text(encoding="utf-8"))
        fresh = COMPILER.compile_projection(self.temp_dir, retain=False)
        self.assertEqual(retained, fresh)


if __name__ == "__main__":
    unittest.main()
