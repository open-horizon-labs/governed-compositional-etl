# Agent guidance

Read `.oh/tpcdi-governed-etl.md` before planning or implementation.

Preserve these boundaries:

- Raw data and a target schema do not authorize business policy.
- Unknown transformations remain explicit Sketch holes until an approved counterexample or named authority resolves them.
- SQLMesh models, SQLGlot ASTs, generated SQL, and DuckDB tables are replaceable projections, not governing policy.
- Keep the complete accepted-counterexample archive separate from the curated regression set.
- Acceptance requires deterministic approved-output checks and separate review against the current Sketch.
- A stage-local pass does not establish edge or end-to-end correctness.
- Do not describe this work as a compliant TPC-DI benchmark or compare its performance with published TPC results.

Work GitHub issues in dependency order. Each issue contains its S&T lineage, acceptance signal, and review trigger.
