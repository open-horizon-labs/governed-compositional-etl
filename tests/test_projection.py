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
        authorities = {entry["source"]["authority"] for entry in manifest["lineage"]}
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
            if entry["source"]["pointer"] == "/mappings/1"
        )
        self.assertEqual(
            lifecycle["targets"]["expressions"],
            ["trade_creation_timestamp"],
        )
        self.assertIn("valid_lifecycle_order", lifecycle["targets"]["audits"])
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

    def test_lineage_exactly_covers_governing_pointers(self):
        inputs = COMPILER.load_inputs()
        manifest = COMPILER.compile_projection(self.temp_dir, retain=False)
        expected = set()
        for path in COMPILER.STAGE_SPECS:
            expected |= {(path, f"/rules/{index}") for index, _ in enumerate(inputs[path]["rules"])}
        expected |= {("contracts/logical-models/dim-trade-v1.json", f"/attributes/{index}") for index, _ in enumerate(inputs["contracts/logical-models/dim-trade-v1.json"]["attributes"])}
        expected |= {("contracts/edges/trade-history-to-dim-trade-v1.json", f"/rules/{index}") for index, _ in enumerate(inputs["contracts/edges/trade-history-to-dim-trade-v1.json"]["rules"])}
        expected |= {("contracts/edges/trade-history-to-dim-trade-v1.json", f"/mappings/{index}") for index, _ in enumerate(inputs["contracts/edges/trade-history-to-dim-trade-v1.json"]["mappings"])}
        expected |= {("contracts/sources/tpcdi-trade-source-v1.json", f"/authority/{index}") for index, _ in enumerate(inputs["contracts/sources/tpcdi-trade-source-v1.json"]["authority"])}
        observed = {(item["source"]["path"], item["source"]["pointer"]) for item in manifest["lineage"]}
        self.assertEqual(observed, expected)
        self.assertEqual({item["source"]["authority"] for item in manifest["lineage"] if item["source"]["pointer"] in {"/mappings/1", "/mappings/2"}}, {"tpc-di-1.1.0-4.5.8.2-create-close"})

    def test_preflight_rejects_governing_shape_mutations_and_injection(self):
        mutations = []
        value = COMPILER.load_inputs(); value["contracts/stages/trade-v1.json"]["rules"] = []; mutations.append(value)
        value = COMPILER.load_inputs(); value["contracts/stages/trade-v1.json"]["output"]["fields"][1]["semantic_type"] = "trade_creation_timestamp"; mutations.append(value)
        value = COMPILER.load_inputs(); value["contracts/logical-models/dim-trade-v1.json"]["attributes"].pop(); mutations.append(value)
        value = COMPILER.load_inputs(); value["contracts/edges/trade-history-to-dim-trade-v1.json"]["mappings"].pop(); mutations.append(value)
        value = COMPILER.load_inputs(); value["contracts/edges/trade-history-to-dim-trade-v1.json"]["history_policy"]["market_creation_status"] = "SBMT') OR TRUE --"; mutations.append(value)
        value = COMPILER.load_inputs(); value["contracts/repair-authority/trade-lifecycle-edge-v1.json"]["allowed_artifacts"] = ["sketch.stage.trade"]; mutations.append(value)
        value = COMPILER.load_inputs(); value["contracts/repair-authority/trade-lifecycle-edge-v1.json"]["active_authority"]["basis"][0]["source"] = "oracle/fixtures/held-out/ho-001.json"; mutations.append(value)
        value = COMPILER.load_inputs(); value["contracts/artifact-classification-v1.json"]["artifacts"][2]["policy_authority"] = True; mutations.append(value)
        value = COMPILER.load_inputs(); value["contracts/logical-models/dim-trade-v1.json"]["holes"][0]["status"] = "resolved"; mutations.append(value)
        for mutated in mutations:
            with self.assertRaises(COMPILER.ProjectionError):
                COMPILER.render_project(mutated)

    def test_verifier_rejects_coordinated_generated_file_and_manifest_tamper(self):
        manifest = COMPILER.compile_projection(self.temp_dir, retain=False)
        relative = "models/trade_stage.sql"
        for location in (self.temp_dir / "canonical", *(self.temp_dir / "arms" / arm for arm in COMPILER.ARMS)):
            path = location / relative
            path.write_text(path.read_text() + "\n-- coordinated tamper\n")
        digest = COMPILER.sha256_bytes((self.temp_dir / "canonical" / relative).read_bytes())
        manifest["files"][relative] = digest
        projection = COMPILER.sha256_bytes(COMPILER.canonical_json(manifest["files"]).encode())
        for arm in COMPILER.ARMS:
            manifest["arms"][arm]["projection_sha256"] = projection
        with self.assertRaises(COMPILER.ProjectionError):
            COMPILER.verify_manifest(manifest, self.temp_dir)

    def test_verifier_rejects_stale_input_expression_lineage_and_dependency_fields(self):
        fields = ("compiler_inputs", "policy_expressions", "lineage", "dependencies")
        for field in fields:
            manifest = COMPILER.compile_projection(self.temp_dir, retain=False)
            if isinstance(manifest[field], list):
                manifest[field].pop()
            else:
                manifest[field][next(iter(manifest[field]))] = "stale"
            with self.assertRaises(COMPILER.ProjectionError):
                COMPILER.verify_manifest(manifest, self.temp_dir)

    def test_compiler_input_path_rejects_symlink_components_and_untracked_files(self):
        security = Path(tempfile.mkdtemp(prefix="issue5-path-", dir=ROOT / "build"))
        try:
            leaf = security / "oracle.json"
            leaf.symlink_to(ROOT / "oracle/fixtures/public/cases.json")
            relative = leaf.relative_to(ROOT).as_posix()
            with self.assertRaises(COMPILER.ProjectionError):
                COMPILER.validate_input_path(relative, (relative,), require_tracked=False)
            private = security / "private.json"
            private.symlink_to(ROOT / "oracle/fixtures/held-out/ho-001.json")
            private_relative = private.relative_to(ROOT).as_posix()
            with self.assertRaises(COMPILER.ProjectionError):
                COMPILER.validate_input_path(private_relative, (private_relative,), require_tracked=False)
            nested = security / "nested"
            nested.symlink_to(ROOT / "oracle", target_is_directory=True)
            nested_relative = (nested / "fixtures/public/cases.json").relative_to(ROOT).as_posix()
            with self.assertRaises(COMPILER.ProjectionError):
                COMPILER.validate_input_path(nested_relative, (nested_relative,), require_tracked=False)
            ce = security / "ce.json"
            ce.symlink_to(ROOT / "counterexamples/archive/private.json")
            ce_relative = ce.relative_to(ROOT).as_posix()
            with self.assertRaises(COMPILER.ProjectionError):
                COMPILER.validate_input_path(ce_relative, (ce_relative,), require_tracked=False)
            regular = security / "regular.json"; regular.write_text("{}")
            regular_relative = regular.relative_to(ROOT).as_posix()
            with self.assertRaises(COMPILER.ProjectionError):
                COMPILER.validate_input_path(regular_relative, (regular_relative,))
        finally:
            shutil.rmtree(security)

    def test_fresh_database_executes_sqlmesh_models_and_audits(self):
        database = self.temp_dir / "fresh.duckdb"
        COMPILER.clone_raw_substrate(database)
        evidence = COMPILER.execute_projection(
            self.temp_dir / "projection", database, retain=False
        )
        self.assertEqual(evidence["dim_trade_rows"], 390978)
        self.assertEqual(evidence["distinct_trade_ids"], 390978)
        self.assertEqual(evidence["audit_errors"], 0)


if __name__ == "__main__":
    unittest.main()
