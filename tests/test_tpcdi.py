import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tpcdi", ROOT / "scripts/tpcdi.py")
TPCDI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TPCDI)


class TpcdiSubstrateTests(unittest.TestCase):
    def setUp(self):
        self.manifest = TPCDI.load_manifest(TPCDI.DEFAULT_MANIFEST)

    def test_manifest_freezes_the_selected_slice(self):
        self.assertEqual(self.manifest["digen"]["version"], "1.1.0")
        self.assertEqual(self.manifest["digen"]["scale_factor"], 3)
        self.assertEqual(
            set(self.manifest["slice_files"]),
            {"status_type", "trade_type", "trade", "trade_history"},
        )
        for details in self.manifest["slice_files"].values():
            self.assertEqual(len(details["sha256"]), 64)
            self.assertGreater(details["rows"], 0)

    def test_loader_is_structural_and_has_explicit_resource_settings(self):
        evidence = self.manifest["slice_files"]
        sql = TPCDI.load_sql(Path("/raw"), Path("/tmp"), evidence)
        self.assertIn("SET memory_limit = '2GB'", sql)
        self.assertIn("SET temp_directory", sql)
        self.assertIn("CREATE SCHEMA IF NOT EXISTS raw", sql)
        self.assertNotIn("JOIN", sql.upper())
        self.assertNotIn("CASE", sql.upper())
        for table in ("status_type", "trade_type", "trade", "trade_history"):
            self.assertIn(f"raw.{table}", sql)

    def test_manifest_is_canonical_json(self):
        text = TPCDI.DEFAULT_MANIFEST.read_text(encoding="utf-8")
        self.assertEqual(json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n", text)


if __name__ == "__main__":
    unittest.main()
