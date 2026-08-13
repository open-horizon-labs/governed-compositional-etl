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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "evidence/issue-2/sf3-manifest.json"
SLICE_NAMES = ("status_type", "trade_type", "trade", "trade_history")
TOOL_ARTIFACTS = ("DIGen.jar", "pdgf/pdgf.jar", "pdgf/plugins/tpc-di.jar")
BATCH_NAMES = ("Batch1", "Batch2", "Batch3")


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
    try:
        with path.open(encoding="utf-8") as source:
            manifest = json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"could not load retained manifest {path}: {error}") from error
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: object) -> None:
    def reject(message: str) -> None:
        raise SystemExit(f"invalid retained manifest: {message}")

    def mapping(value: object, name: str) -> dict:
        if not isinstance(value, dict):
            reject(f"{name} must be an object")
        return value

    def exact_keys(value: dict, wanted: tuple[str, ...], name: str) -> None:
        if set(value) != set(wanted):
            reject(f"{name} keys must be {sorted(wanted)}; got {sorted(value)}")

    def positive_integer(value: object, name: str, minimum: int = 1) -> None:
        if type(value) is not int or value < minimum:
            reject(f"{name} must be an integer >= {minimum}")

    root = mapping(manifest, "root")
    exact_keys(root, ("digen", "provenance", "slice_files", "tool_artifacts"), "root")

    digen = mapping(root["digen"], "digen")
    exact_keys(digen, ("version", "scale_factor", "batch_rows"), "digen")
    if not isinstance(digen["version"], str) or not digen["version"].strip():
        reject("digen.version must be a non-empty string")
    positive_integer(digen["scale_factor"], "digen.scale_factor", minimum=3)
    batches = mapping(digen["batch_rows"], "digen.batch_rows")
    exact_keys(batches, BATCH_NAMES + ("all",), "digen.batch_rows")
    for name, count in batches.items():
        positive_integer(count, f"digen.batch_rows.{name}")
    if batches["all"] != sum(batches[name] for name in BATCH_NAMES):
        reject("digen.batch_rows.all must equal Batch1 + Batch2 + Batch3")

    provenance = mapping(root["provenance"], "provenance")
    exact_keys(provenance, ("canonical_download", "evaluated_copy", "note"), "provenance")
    for name, value in provenance.items():
        if not isinstance(value, str) or not value.strip():
            reject(f"provenance.{name} must be a non-empty string")

    slice_files = mapping(root["slice_files"], "slice_files")
    exact_keys(slice_files, SLICE_NAMES, "slice_files")
    for name, value in slice_files.items():
        details = mapping(value, f"slice_files.{name}")
        exact_keys(details, ("path", "sha256", "bytes", "rows"), f"slice_files.{name}")
        path = details["path"]
        if (
            not isinstance(path, str)
            or not path
            or Path(path).is_absolute()
            or ".." in Path(path).parts
        ):
            reject(f"slice_files.{name}.path must be a safe relative path")
        if not isinstance(details["sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", details["sha256"]
        ):
            reject(f"slice_files.{name}.sha256 must be 64 lowercase hex characters")
        positive_integer(details["bytes"], f"slice_files.{name}.bytes")
        positive_integer(details["rows"], f"slice_files.{name}.rows")

    tools = mapping(root["tool_artifacts"], "tool_artifacts")
    exact_keys(tools, TOOL_ARTIFACTS, "tool_artifacts")
    for relative, digest in tools.items():
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            reject(f"tool_artifacts path is unsafe: {relative}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            reject(f"tool_artifacts.{relative} must be 64 lowercase hex characters")


def verify_tools(tools_dir: Path, java: Path, manifest: dict) -> None:
    expected = manifest["tool_artifacts"]
    for relative, wanted in expected.items():
        path = tools_dir / relative
        if not path.is_file():
            raise SystemExit(f"missing pinned tool artifact: {path}")
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
    expected_version = manifest["digen"]["version"]
    match = re.search(r"^DIGen Version:\s*(\S+)\s*$", output, re.MULTILINE)
    if not match or match.group(1) != expected_version:
        observed = match.group(1) if match else "missing"
        raise SystemExit(
            f"DIGen version was {observed}; retained manifest requires {expected_version}"
        )


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


def verify_report(output_dir: Path, manifest: dict) -> None:
    report_path = output_dir / "digen_report.txt"
    if not report_path.is_file():
        raise SystemExit(f"DIGen did not write {report_path}")
    report = report_path.read_text(encoding="utf-8")
    expected = manifest["digen"]
    patterns = {
        "version": r"^DIGen Version:\s*(\S+)\s*$",
        "scale_factor": r"^Scale Factor:\s*(\d+)\s*$",
    }
    observed = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, report, re.MULTILINE)
        if not match:
            raise SystemExit(f"DIGen report is missing {name}")
        observed[name] = match.group(1) if name == "version" else int(match.group(1))
    observed_batches = {}
    for name in BATCH_NAMES:
        match = re.search(rf"TotalRecords for {name}:\s*(\d+)", report)
        if not match:
            raise SystemExit(f"DIGen report is missing row total for {name}")
        observed_batches[name] = int(match.group(1))
    match = re.search(r"TotalRecords all Batches:\s*(\d+)", report)
    if not match:
        raise SystemExit("DIGen report is missing row total for all batches")
    observed_batches["all"] = int(match.group(1))
    observed["batch_rows"] = observed_batches
    if observed != expected:
        raise SystemExit(f"DIGen report was {observed}; retained manifest requires {expected}")


def generate(
    tools_dir: Path, java: Path, output_dir: Path, reuse: bool, manifest: dict
) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        if not reuse:
            raise SystemExit(
                f"{output_dir} is not empty; pass --reuse or choose a fresh --raw-dir"
            )
        verify_report(output_dir, manifest)
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
        str(manifest["digen"]["scale_factor"]),
        "-o",
        str(output_dir.resolve()),
        "-jvm",
        "-Xms512m -Xmx2g",
    ]
    subprocess.run(command, cwd=tools_dir, env=env, check=True)
    verify_report(output_dir, manifest)


def inspect_slice(raw_dir: Path, manifest: dict) -> dict[str, dict[str, object]]:
    observed = {}
    expected = manifest["slice_files"]
    for name in SLICE_NAMES:
        relative = expected[name]["path"]
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
    paths = {
        name: (raw_dir / evidence[name]["path"]).resolve() for name in SLICE_NAMES
    }
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
        generate(tools_dir, java, args.raw_dir, args.reuse, manifest)
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
