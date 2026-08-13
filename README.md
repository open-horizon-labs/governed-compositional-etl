# Governed Compositional ETL

This repository tests whether counterexample-supplemented sketches can govern a multi-stage ETL pipeline, not just one generated component.

The proposed experiment uses a TPC-DI-derived retail-brokerage workload, DuckDB for local analytical execution, SQLMesh and SQLGlot for the executable model DAG, and CESS for reviewed semantic change. TPC-DI is used as a research workload and transformation oracle, not as a compliant or comparative TPC benchmark.

The central question is:

> Can a system locate the first incorrect semantic decision, change only the artifact authorized by that failure, and revalidate all affected downstream meaning better than native pipeline checks or independent stage-level CESS?

Start with [.oh/tpcdi-governed-etl.md](.oh/tpcdi-governed-etl.md). It records the aim, problem weave, selected solution, risks, and issue plan.

The reproducible issue #2 substrate is documented in [docs/tpcdi-raw-substrate.md](docs/tpcdi-raw-substrate.md). After personally acquiring TPC-DI 1.1.0 tools, its smoke command generates the scale-factor-3 source, verifies retained checksums and counts, and structurally loads the selected trade slice into persistent DuckDB.

The issue #3 [semantic repair oracle](docs/semantic-repair-oracle.md) freezes a policy-authorized local case, an issue #4 contract-adjudicated edge/composition case, and an ambiguous case plus narrative-free scoring before experiment execution.

The issue #4 [semantic contracts and change authority](docs/semantic-contracts.md) keep known rules, explicit holes, nominal semantic types, repair surfaces, and replaceable projections separate.

The issue #5 [replaceable SQLMesh projection](docs/executable-projection.md) compiles only the current Sketch, structural anchors, and contracts into SQLGlot-built expressions, deterministic SQLMesh audits, and persistent DuckDB results.

## Intended architecture

```text
TPC-DI raw files
  -> parsing and normalization
  -> reference interpretation
  -> identity and history
  -> event classification
  -> logical warehouse model
  -> DuckDB dimensions and facts
  -> metrics and verification
```

Policy must remain separate from generated SQL:

- Sketches govern meaning, rule order, authority, and explicit holes.
- Source and target schemas anchor stable structure.
- SQLMesh models and SQL are replaceable projections.
- DuckDB executes projections and deterministic gates.
- Accepted counterexamples preserve reviewed policy changes.
- Curated regressions protect distinct semantic boundaries.
- Stage and edge contracts carry units, grain, time semantics, evidence, rule IDs, and disposition.

## Evidence boundary

The initial proof is a bounded vertical slice. It does not establish general correctness, benchmark performance, or vendor superiority. Review the TPC fair-use requirements before publishing any derived performance results.

## Sources

- [TPC-DI overview](https://www.tpc.org/tpcdi/)
- [TPC-DI specification 1.1.0](https://www.tpc.org/TPC_Documents_Current_Versions/pdf/TPC-DI_v1.1.0.pdf)
- [DuckDB larger-than-memory guidance](https://duckdb.org/docs/current/guides/performance/environment)
- [SQLMesh](https://github.com/SQLMesh/sqlmesh)
- [SQLGlot](https://github.com/tobymao/sqlglot)
