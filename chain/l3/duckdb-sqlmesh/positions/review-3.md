# Review 3 (sketch reviewer, scoped): positions on duckdb-sqlmesh, L3 cycle 3 (verdict: pass)

Scope: the cycle-3 change under `change-contract-3.md`: the updates-in-place audit rewritten to the tolerant form, one new AUDIT (`inv.eligible_holding_report_persisted`), the cardinality half and null-safe key joins in both sum audits, manifest provenance. Model SELECT bodies and materialization properties verified byte-identical. Evidence: check status question, zero problems, 13 audits; run ok, 13 at zero; two-phase ok; mutate 14, zero unprotected; the tie counterexample now silent on this engine (it refused the plan before); compare identical.

Reviewer: Opus sketch reviewer, six scope questions.

## Findings

1. **Updates-in-place: pass.** Clause 2 is "no candidate"; clause 1 is "an undominated candidate exists and none matches", null-safe on quantities. Dominance is faithful to report_order (incremental beats historical, then batch_date, then cdc_dsn), `COALESCE(cdc_dsn, -1)` on both sides, verified consistent with DuckDB's NULLS LAST in the model's own ordering. Candidate filter is the model's own. Comment substantively true; two narrow imprecisions (tie needs equal batch_date too; "neither true" describes the conjunction) for a text pass.
2. **New audit: pass.** Whole-pair abstention, all four ownership values non-null, both halves reported, reads confined, registered quoted on holding_change; `depends_on (governed.trade)` already present.
3. **Sum audits: pass.** Cardinality computed over `@this_model` alone before the join (the load-bearing detail), `IS NOT DISTINCT FROM` on both key columns, each on its own model.
4. **Manifest and headers: pass.** Sha matches; counts reconcile (13 files, 13 entries, 7+3+3 in the models' lists, 13 deterministic selected invariants). One sentence owed in the holding_change artifact's strategy prose ("latest I- or U-flagged" omits the null-flag historical rows); requested with the parity question.
5. **Cross-engine:** the candidate-filter difference the native review found is real but bounded to an out-of-vocabulary flag, and this target's posture (drop and let the converse audit fire) is the better one under the conflict protocol; native was brought to the same form. The two `*_key_matches_holding_change` audits still use `=` where native is null-safe; unreachable here (the upstream publishes no unpinnable trade), noted for a later cycle.
6. **Policy decided in SQL: none** beyond the filed question. Residuals recorded: the `-1` sentinel decides a null incremental cdc_dsn ranks below any real one in the same batch; the vocabulary question, now filed on both targets.

Failure class: none. Rejected artifacts: none. Stamped on acceptance after the two parity edits.
