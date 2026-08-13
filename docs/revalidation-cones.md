# Bounded semantic revalidation cones

Issue #6 keeps the executable SQLMesh DAG and governed semantic dependency DAG separate in `contracts/revalidation-profile-v1.json`. The executable graph answers which generated models must rerun. The semantic graph answers which warehouse meanings and non-SQL consumers may have changed; its lifecycle metric dependency is deliberately absent from SQL lineage.

For the adjudicated TradeHistory creation-time edge, the calculated semantic cone exactly matches the frozen oracle: `logical.dim_trade`, `duckdb.dim_trade`, and `metric.trade_lifecycle_seconds`. Recall and precision are both 1.0, with no escapes or unnecessary semantic recomputation. This is a bounded correctness result, not evidence that smaller cones are generally preferable.

Every cone runs the active edge case, the separately curated local-reference regression, SQLMesh audits, and every path invariant selected by the changed semantic source. Any omitted frozen descendant fails closed. The full-replay control retains recall 1.0 while reporting its larger node set; elapsed time is retained as operational evidence but is not presented as a benchmark or the basis for correctness.

The accepted-counterexample archive is separately retained and empty because named TPC-DI authority—not an approved counterexample—adjudicated this edge. The curated regression set contains only the distinct local TradeType semantic boundary.
