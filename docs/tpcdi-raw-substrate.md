# TPC-DI 1.1.0 raw substrate

This spike uses the official, unchanged TPC-DI 1.1.0 DIGen and its bundled PDGF. It is a bounded research workload, not a compliant TPC-DI benchmark, and its timings must not be compared with published TPC results.

## Acquire the tools

The canonical source is the TPC's [current specifications and tools page](https://www.tpc.org/TPC_Documents_Current_Versions/current_specifications5.asp). Select `TPC-DI_Tools_v1.1.0.zip`. TPC requires each downloader to register and personally accept its [End User License Agreement](https://www.tpc.org/TPC_Documents_Current_Versions/txt/EULA_v2.2.0.txt); this repository therefore does not download or redistribute the package.

Extract the package outside Git so that this layout exists:

```text
.cache/tpcdi-tools/1.1.0/
  DIGen.jar
  pdgf/pdgf.jar
  pdgf/plugins/tpc-di.jar
```

The smoke command rejects different core artifact hashes before execution. The issue #2 run evaluated the copy retained at [`mwiewior/tbd-tpc-di@8929270`](https://github.com/mwiewior/tbd-tpc-di/tree/892927064ab9246340f8b22910081372cd2520b9/tools). Its self-reported version and core hashes were corroborated across three additional public redistributions of the 1.1.0 package. This provenance is evidence, not a new canonical source: acquire a fresh licensed copy from TPC for subsequent runs.

TPC now lists TPC-DI as an obsolete workload. The TPC EULA permits academic or research use and requires non-TPC performance results to be clearly identified as non-comparable. Human review of the current TPC policies and fair-use guidance remains required before publishing results.

## Runtime

The TPC-DI 1.1.0 specification requires at least Java SE 7. This repository pins Zulu OpenJDK 8 because the bundled 2014 PDGF assumes the Java 8 class-loader model; Java 17 does not run it. DuckDB 1.3.2 is the verified structural-loading runtime.

With `mise` available, install the pinned versions:

```sh
mise install
```

The unchanged DIGen wrapper does not discover its bundled TPC-DI plugin correctly on the verified Apple Silicon Java 8 runtime. `scripts/tpcdi.py` gives DIGen a compatibility Java home whose launcher supplies the already-bundled jars on the child JVM classpath and disables PDGF's interactive shell. It does not edit DIGen, PDGF, their configuration, or generated data. Core jar hashes are checked first, and DIGen still writes `digen_report.txt`.

The effective generation is DIGen's documented small-scale command:

```sh
java -jar DIGen.jar -sf 3 -o raw/generated/tpcdi-sf3 -jvm "-Xms512m -Xmx2g"
```

Run the complete generation, verification, and persistent load with:

```sh
mise exec -- python3 scripts/tpcdi.py smoke
```

Reuse already verified generated data while recreating and checking DuckDB with:

```sh
mise exec -- python3 scripts/tpcdi.py smoke --reuse
```

Generated data lives under `raw/generated/`; the persistent database is `build/tpcdi.duckdb`; DuckDB spill files use `tmp/duckdb/`. All three paths are ignored by Git.

## Selected vertical slice

The bounded historical-load path is:

```text
StatusType.txt ----\
                    > Trade.txt -> trade identity and typed event fields
TradeType.txt -----/       |
                           v
                    TradeHistory.txt -> ordered status observations
```

The four selected files allow later issues to exercise pipe-delimited parsing, reference interpretation for trade type and status, stable trade identity across history, a logical trade fact, and a downstream status/time metric. Issue #2 loads only source-declared structure:

- `raw.status_type`: six status reference rows;
- `raw.trade_type`: five trade-type reference rows;
- `raw.trade`: 390,978 historical trade rows;
- `raw.trade_history`: 982,180 historical status observations.

There are no joins, classifications, policy defaults, or business-rule transformations in this load. The reference meanings and history semantics remain work for governed Sketches and the frozen oracle. Raw data and these table shapes do not authorize that policy.

## Retained evidence

[`evidence/issue-2/sf3-manifest.json`](../evidence/issue-2/sf3-manifest.json) freezes the tool hashes, source-file hashes, byte counts, source row counts, scale factor, and DIGen batch totals. The loader repeats these checks before writing DuckDB and stores the selected source evidence in `raw.source_evidence`.

DIGen 1.1.0 reported:

| Batch | Rows |
|---|---:|
| Batch1 | 4,539,962 |
| Batch2 | 19,900 |
| Batch3 | 19,855 |
| Total | 4,579,717 |

The report contains timestamps and generation throughput, so it remains in the ignored generated-data directory rather than becoming a claimed performance artifact.
