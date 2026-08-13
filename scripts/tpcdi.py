#!/usr/bin/env python3
"""Generate, verify, and structurally load the bounded TPC-DI raw slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "evidence/issue-2/sf3-manifest.json"
SLICE_FILES = {
    "status_type": "Batch1/StatusType.txt",
    "trade_type": "Batch1/TradeType.txt",
    "trade": "Batch1/Trade.txt",
    "trade_history": "Batch1/TradeHistory.txt",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_count(path: Path) -> int:
    count = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            count += chunk.count(b"\n")
    return count


def load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def verify_tools(tools_dir: Path, java: Path, manifest: dict) -> None:
    expected = manifest["tool_artifacts"]
    for relative, wanted in expected.items():
        path = tools_dir / relative
        if not path.is_file():
            raise SystemExit(f"missing official tool artifact: {path}")
        actual = sha256(path)
        if actual != wanted:
            raise SystemExit(
                f"unexpected SHA-256 for {relative}: {actual} (expected {wanted})"
            )

    version = subprocess.run(
        [str(java), "-jar", str(tools_dir / "DIGen.jar"), "-v"],
        cwd=tools_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    output = version.stdout + version.stderr
    if "DIGen Version: 1.1.0" not in output:
        raise SystemExit(f"DIGen version check failed:\n{output}")


def java_home(java: Path) -> Path:
    probe = subprocess.run(
        [str(java), "-XshowSettings:properties", "-version"],
        text=True,
        capture_output=True,
        check=True,
    )
    match = re.search(r"^\s*java\.home\s*=\s*(.+)$", probe.stderr, re.MULTILINE)
    if not match:
        raise SystemExit("could not determine java.home")
    return Path(match.group(1)).resolve()


def prepare_compat_home(java: Path, destination: Path) -> Path:
    real_home = java_home(java)
    destination.mkdir(parents=True, exist_ok=True)

    def ensure_link(link: Path, target: Path) -> None:
        if link.is_symlink():
            if link.resolve() == target.resolve():
                return
            link.unlink()
        elif link.exists():
            raise SystemExit(f"compatibility cache path is not a symlink: {link}")
        link.symlink_to(target)

    for item in real_home.iterdir():
        if item.name == "bin":
            continue
        ensure_link(destination / item.name, item)

    bin_dir = destination / "bin"
    bin_dir.mkdir(exist_ok=True)
    for item in (real_home / "bin").iterdir():
        if item.name == "java":
            continue
        ensure_link(bin_dir / item.name, item)
    java_link = bin_dir / "java"
    ensure_link(java_link, ROOT / "scripts/digen-java-home/bin/java")
    return destination.resolve()


def verify_report(output_dir: Path) -> None:
    report_path = output_dir / "digen_report.txt"
    if not report_path.is_file():
        raise SystemExit(f"DIGen did not write {report_path}")
    report = report_path.read_text(encoding="utf-8")
    required = (
        "DIGen Version: 1.1.0",
        "Scale Factor: 3",
        "TotalRecords for Batch1: 4539962",
        "TotalRecords for Batch2: 19900",
        "TotalRecords for Batch3: 19855",
        "TotalRecords all Batches: 4579717",
    )
    missing = [entry for entry in required if entry not in report]
    if missing:
        raise SystemExit(f"DIGen report is missing expected evidence: {missing}")


def generate(tools_dir: Path, java: Path, output_dir: Path, reuse: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        if not reuse:
            raise SystemExit(
                f"{output_dir} is not empty; pass --reuse or choose a fresh --raw-dir"
            )
        verify_report(output_dir)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    compat_home = prepare_compat_home(java, ROOT / ".cache/tpcdi-java-home")
    env = os.environ.copy()
    env["TPCDI_REAL_JAVA"] = str(java.resolve())
    command = [
        str(java),
        f"-Djava.home={compat_home}",
        "-jar",
        "DIGen.jar",
        "-sf",
        "3",
        "-o",
        str(output_dir.resolve()),
        "-jvm",
        "-Xms512m -Xmx2g",
    ]
    subprocess.run(command, cwd=tools_dir, env=env, check=True)
    verify_report(output_dir)


def inspect_slice(raw_dir: Path, manifest: dict) -> dict[str, dict[str, object]]:
    observed = {}
    expected = manifest["slice_files"]
    for name, relative in SLICE_FILES.items():
        path = raw_dir / relative
        if not path.is_file():
            raise SystemExit(f"missing selected raw file: {path}")
        details = {
            "path": relative,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "rows": line_count(path),
        }
        wanted = expected[name]
        for key in ("sha256", "bytes", "rows"):
            if details[key] != wanted[key]:
                raise SystemExit(
                    f"{relative} {key} was {details[key]!r}; expected {wanted[key]!r}"
                )
        observed[name] = details
    return observed


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def load_sql(raw_dir: Path, temp_dir: Path, evidence: dict) -> str:
    paths = {name: (raw_dir / relative).resolve() for name, relative in SLICE_FILES.items()}
    evidence_rows = ",\n".join(
        "(" + ", ".join(
            [
                sql_literal(details["path"]),
                sql_literal(details["sha256"]),
                str(details["bytes"]),
                str(details["rows"]),
            ]
        ) + ")"
        for details in evidence.values()
    )
    return f"""
SET memory_limit = '2GB';
SET temp_directory = {sql_literal(str(temp_dir.resolve()))};
CREATE SCHEMA IF NOT EXISTS raw;
CREATE OR REPLACE TABLE raw.status_type AS
SELECT * FROM read_csv({sql_literal(str(paths['status_type']))}, delim='|', header=false,
  columns={{'st_id':'VARCHAR','st_name':'VARCHAR'}});
CREATE OR REPLACE TABLE raw.trade_type AS
SELECT * FROM read_csv({sql_literal(str(paths['trade_type']))}, delim='|', header=false,
  columns={{'tt_id':'VARCHAR','tt_name':'VARCHAR','tt_is_sell':'BOOLEAN','tt_is_mrkt':'BOOLEAN'}});
CREATE OR REPLACE TABLE raw.trade AS
SELECT * FROM read_csv({sql_literal(str(paths['trade']))}, delim='|', header=false,
  columns={{'t_id':'BIGINT','t_dts':'TIMESTAMP','t_st_id':'VARCHAR','t_tt_id':'VARCHAR',
    't_is_cash':'BOOLEAN','t_s_symb':'VARCHAR','t_qty':'INTEGER','t_bid_price':'DECIMAL(18,2)',
    't_ca_id':'BIGINT','t_exec_name':'VARCHAR','t_trade_price':'DECIMAL(18,2)',
    't_chrg':'DECIMAL(18,2)','t_comm':'DECIMAL(18,2)','t_tax':'DECIMAL(18,2)'}});
CREATE OR REPLACE TABLE raw.trade_history AS
SELECT * FROM read_csv({sql_literal(str(paths['trade_history']))}, delim='|', header=false,
  columns={{'th_t_id':'BIGINT','th_dts':'TIMESTAMP','th_st_id':'VARCHAR'}});
CREATE OR REPLACE TABLE raw.source_evidence(
  source_file VARCHAR, sha256 VARCHAR, byte_count BIGINT, source_row_count BIGINT
);
INSERT INTO raw.source_evidence VALUES
{evidence_rows};
"""


def find_duckdb(explicit: str | None) -> str:
    executable = explicit or shutil.which("duckdb")
    if not executable:
        raise SystemExit("duckdb CLI not found; pass --duckdb")
    return executable


def load_raw(
    raw_dir: Path,
    database: Path,
    temp_dir: Path,
    evidence: dict,
    duckdb: str,
) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [duckdb, str(database)],
        input=load_sql(raw_dir, temp_dir, evidence),
        text=True,
        check=True,
    )


def verify_database(database: Path, evidence: dict, duckdb: str) -> None:
    expected = {
        "status_type": evidence["status_type"]["rows"],
        "trade_type": evidence["trade_type"]["rows"],
        "trade": evidence["trade"]["rows"],
        "trade_history": evidence["trade_history"]["rows"],
    }
    query = " UNION ALL ".join(
        f"SELECT {sql_literal(name)}, count(*) FROM raw.{name}"
        for name in expected
    ) + " ORDER BY 1"
    result = subprocess.run(
        [duckdb, "-csv", "-noheader", str(database), query],
        text=True,
        capture_output=True,
        check=True,
    )
    actual = {}
    for line in result.stdout.splitlines():
        name, count = line.split(",", 1)
        actual[name] = int(count)
    if actual != expected:
        raise SystemExit(f"DuckDB row counts were {actual}; expected {expected}")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("action", choices=("verify", "generate", "load", "smoke"))
    command.add_argument("--tools-dir", type=Path, default=ROOT / ".cache/tpcdi-tools/1.1.0")
    command.add_argument("--java", type=Path, default=Path(shutil.which("java") or "java"))
    command.add_argument("--duckdb")
    command.add_argument("--raw-dir", type=Path, default=ROOT / "raw/generated/tpcdi-sf3")
    command.add_argument("--database", type=Path, default=ROOT / "build/tpcdi.duckdb")
    command.add_argument("--temp-dir", type=Path, default=ROOT / "tmp/duckdb")
    command.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    command.add_argument("--reuse", action="store_true")
    return command


def main() -> None:
    args = parser().parse_args()
    manifest = load_manifest(args.manifest)
    java = args.java.resolve()
    tools_dir = args.tools_dir.resolve()
    if args.action in ("verify", "generate", "smoke"):
        verify_tools(tools_dir, java, manifest)
    if args.action in ("generate", "smoke"):
        generate(tools_dir, java, args.raw_dir, args.reuse)
    if args.action in ("verify", "load", "smoke"):
        evidence = inspect_slice(args.raw_dir, manifest)
    if args.action in ("load", "smoke"):
        duckdb = find_duckdb(args.duckdb)
        load_raw(args.raw_dir, args.database, args.temp_dir, evidence, duckdb)
        verify_database(args.database, evidence, duckdb)
    if args.action == "verify":
        print(json.dumps(evidence, indent=2, sort_keys=True))
    elif args.action == "smoke":
        print(f"smoke passed: {args.database}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from error
