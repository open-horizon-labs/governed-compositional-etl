# Change contract, cycle 17: L1 -> L2, job trade-lifecycle (frozen invariants quantify over claimed trades)

- **Exact active change authority:** `chain/l3/duckdb-native/trade-lifecycle/review-8.md`.
- **Authorized correction:** one sentence in the statement of `inv.trade_owning_account_frozen`, `inv.trade_placement_reference_frozen` and `inv.trade_order_type_frozen`: each quantifies over trade_numbers for which this job claims a logical.trade row; a trade unclaimed under `inv.trade_held_first_report_unclaimed` or `L1.hole.deletions` is not this invariant's business. Nothing else moves.
- **Acceptance:** gate ok; diff confined to the three statements.
