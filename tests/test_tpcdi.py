import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


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

    def test_malformed_manifest_is_rejected(self):
        cases = []
        missing_digen = copy.deepcopy(self.manifest)
        del missing_digen["digen"]
        cases.append(missing_digen)
        invalid_hash = copy.deepcopy(self.manifest)
        invalid_hash["slice_files"]["trade"]["sha256"] = "not-a-sha"
        cases.append(invalid_hash)
        unsafe_path = copy.deepcopy(self.manifest)
        unsafe_path["slice_files"]["trade"]["path"] = "../Trade.txt"
        cases.append(unsafe_path)
        inconsistent_total = copy.deepcopy(self.manifest)
        inconsistent_total["digen"]["batch_rows"]["all"] += 1
        cases.append(inconsistent_total)

        for malformed in cases:
            with self.subTest(malformed=malformed), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "manifest.json"
                path.write_text(json.dumps(malformed), encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "invalid retained manifest"):
                    TPCDI.load_manifest(path)

    def test_corrupted_raw_file_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["slice_files"]["status_type"]["path"] = "custom/Status.tbl"
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            for name, details in manifest["slice_files"].items():
                path = raw_dir / details["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"{name}\r\n".encode())
                details["sha256"] = TPCDI.sha256(path)
                details["bytes"] = path.stat().st_size
                details["rows"] = TPCDI.line_count(path)
            TPCDI.validate_manifest(manifest)
            TPCDI.inspect_slice(raw_dir, manifest)

            trade = raw_dir / manifest["slice_files"]["trade"]["path"]
            with trade.open("ab") as destination:
                destination.write(b"corruption")
            with self.assertRaisesRegex(SystemExit, "Trade.txt sha256"):
                TPCDI.inspect_slice(raw_dir, manifest)

    def test_wrong_tool_hash_is_rejected_before_java_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory)
            for relative in self.manifest["tool_artifacts"]:
                path = tools / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"wrong")
            with mock.patch.object(TPCDI.subprocess, "run") as run:
                with self.assertRaisesRegex(SystemExit, "unexpected SHA-256"):
                    TPCDI.verify_tools(tools, Path("/unused/java"), self.manifest)
                run.assert_not_called()

    def test_tool_version_must_match_manifest(self):
        manifest = copy.deepcopy(self.manifest)
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory)
            for relative in manifest["tool_artifacts"]:
                path = tools / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(relative.encode())
                manifest["tool_artifacts"][relative] = TPCDI.sha256(path)
            TPCDI.validate_manifest(manifest)
            result = subprocess.CompletedProcess(
                args=[], returncode=255, stdout="DIGen Version: 9.9.9\n", stderr=""
            )
            with mock.patch.object(TPCDI.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(SystemExit, "manifest requires 1.1.0"):
                    TPCDI.verify_tools(tools, Path("/java"), manifest)

    def test_report_must_match_manifest_version_scale_and_totals(self):
        expected = self.manifest["digen"]

        def report(version=None, scale=None, rows=None):
            batch_rows = rows or expected["batch_rows"]
            return "\n".join(
                [
                    "TPC-DI Data Generation Report",
                    f"DIGen Version: {version or expected['version']}",
                    f"Scale Factor: {scale or expected['scale_factor']}",
                    f"AuditTotalRecordsSummaryWriter - TotalRecords for Batch1: {batch_rows['Batch1']}",
                    f"AuditTotalRecordsSummaryWriter - TotalRecords for Batch2: {batch_rows['Batch2']}",
                    f"AuditTotalRecordsSummaryWriter - TotalRecords for Batch3: {batch_rows['Batch3']}",
                    f"AuditTotalRecordsSummaryWriter - TotalRecords all Batches: {batch_rows['all']} 1.0 records/second",
                ]
            )

        wrong_totals = dict(expected["batch_rows"])
        wrong_totals["Batch2"] += 1
        cases = (
            report(version="9.9.9"),
            report(scale=expected["scale_factor"] + 1),
            report(rows=wrong_totals),
        )
        for content in cases:
            with (
                self.subTest(report=content),
                tempfile.TemporaryDirectory() as directory,
            ):
                output = Path(directory)
                (output / "digen_report.txt").write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "retained manifest requires"):
                    TPCDI.verify_report(output, self.manifest)

    def test_database_row_count_mismatch_is_rejected(self):
        evidence = self.manifest["slice_files"]
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="status_type,6\ntrade,390977\ntrade_history,982180\ntrade_type,5\n",
            stderr="",
        )
        with mock.patch.object(TPCDI.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(SystemExit, "DuckDB row counts were"):
                TPCDI.verify_database(Path("fixture.duckdb"), evidence, "duckdb")

    def test_generation_scale_comes_from_manifest(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["digen"]["scale_factor"] = 7
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw"
            with (
                mock.patch.object(TPCDI, "prepare_compat_home", return_value=Path("/compat")),
                mock.patch.object(TPCDI, "verify_report"),
                mock.patch.object(TPCDI.subprocess, "run") as run,
            ):
                TPCDI.generate(Path("/tools"), Path("/java"), output, False, manifest)
                command = run.call_args.args[0]
                self.assertEqual(command[command.index("-sf") + 1], "7")


if __name__ == "__main__":
    unittest.main()
