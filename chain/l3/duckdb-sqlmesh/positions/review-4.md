# Review 4 (coordinator, bookkeeping): positions on duckdb-sqlmesh (verdict: pass)

Scope: the one audit L1.unknown-codes demanded, `audits/inv.unknown_codes_held.sql`, read in full: it reports rows of the job's raw source whose coded field carries a value outside the anchored vocabulary (null-safe where a null is not an anchored historical marker), names the record and the code, reads only that source, and decides nothing after. Registered; provenance moved; the cdc_flag-vocabulary question retired on positions since the clause answers it. Evidence: check ok or question with zero problems; run every audit zero; two-phase ok; mutate zero unprotected; on positions the unanchored-flag counterexample now fires this audit on both engines.

Reviewer: coordinator acting as sketch reviewer for a single restating audit whose SQL is one predicate. Rejected artifacts: none. Stamped on acceptance.
