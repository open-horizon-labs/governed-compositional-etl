# Bounded semantic revalidation cones

Issue #6 keeps the executable SQLMesh DAG and governed semantic dependency DAG separate in `contracts/revalidation-profile-v1.json`. The executable graph answers which generated models must rerun. The semantic graph answers which warehouse meanings and non-SQL consumers may have changed; its lifecycle metric dependency is deliberately absent from SQL lineage.

For the adjudicated TradeHistory creation-time edge, the calculated semantic cone exactly matches the frozen oracle: `logical.dim_trade`, `duckdb.dim_trade`, and `metric.trade_lifecycle_seconds`. Recall and precision are both 1.0, with no escapes or unnecessary semantic recomputation. This is a bounded correctness result, not evidence that smaller cones are generally preferable.

Every cone runs the active edge case, the separately curated local-reference regression, SQLMesh audits, and every path invariant selected by the changed semantic source. Any omitted frozen descendant fails closed. The cone is restaged in an isolated persistent DuckDB copy: SQLMesh refreshes `trade_lifecycle` and then `dim_trade`, while four required ancestors remain in the recorded selection closure and are verified from the copied baseline. A separate isolated full replay refreshes all six models. Exact executed order, status, row counts, audits, checks, and wall time are retained. Timing is operational evidence, not a benchmark or correctness result.

Both case submissions are constructed from deterministic queries over the replayed tables. The harness does not load the prewritten example answers. Adversarial snapshots with a wrong but non-null creation timestamp or type name continue to pass local identity/not-null checks and fail the frozen semantic score.

The accepted-counterexample archive is separately retained and empty because named TPC-DI authority—not an approved counterexample—adjudicated this edge. The curated regression set contains only the distinct local TradeType semantic boundary.
