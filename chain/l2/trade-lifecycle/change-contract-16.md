# Change contract, cycle 16: L1 -> L2, job trade-lifecycle (held reports as evidence; placement-fixing facts)

- **Exact active change authority:** `L1.unknown-codes` (a held report keeps its place in the order of reports; nothing else about it may be read) and `L1.hole.held-first-report-placement` as widened (a trade any of whose placement-fixing facts would come from a held report is held until the hole is answered); `chain/l3/duckdb-native/trade-lifecycle/review-7.md`.
- **Authorized corrections:**
  1. Restate `inv.trade_owning_account_frozen`, `inv.trade_placement_reference_frozen` and `inv.trade_order_type_frozen` so a held report is not evidence: each quantifies over anchored reports only, and a held report neither confirms nor contradicts the frozen value.
  2. `placed_at`, `owning_account_number`, `order_type` and their handoffs: a trade whose placement, owning account or order type would come from a held report (the earliest report of the source that supplies it is held, whatever another source's earliest report says) is unclaimed and has no row while the hole is open; `inv.every_received_trade_persisted` and `inv.trade_first_seen_late_defined_or_held` agree; `sg.placement-moment.gap` restates the widened hole.
  3. One sentence in the report_order-reading handoffs' parallel_assumption: a held report keeps its place in the order, so it can be the earliest report (and hold the trade) without any of its content being read.
- **Acceptance:** gate ok; diff confined; no question owed.
