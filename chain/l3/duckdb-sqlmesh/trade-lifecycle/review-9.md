# Review 9 (coordinator, bookkeeping): trade-lifecycle on duckdb-sqlmesh, L3 cycle 9 (verdict: pass)

Scope: the re-projection under the business's answer to `L1.hole.market-order-seen-pending`, verified against the files and the runs: `first_seen_late` now treats PNDG and SBMT alike as opening events for a market order and leaves limit orders unchanged; `inv.trade_market_order_seen_pending_held` and its audit are gone; the two first-seen-late audits claim the case they used to exclude. Everything bounded by `L1.hole.held-first-report-placement` is byte-unchanged, as that hole is still open.

Evidence: check ok, 12 audits; run 12 at zero; two-phase ok; mutate zero unprotected; the held-for-review counterexample now fires exactly `inv.unknown_codes_held` with five rows, and trade 900004 persists with `first_seen_late` false where it was held before; 900005, 900007, 900008 and 900009 still have no row; the market-order counterexample stays silent; cross-engine compare identical.

Process note: the Developer ran `stamp` itself, which is the acceptance step and the reviewer's. `stamp` now refuses a projection that changed after the review that judged it, so a Developer cannot accept its own work. Re-stamped here after this review.

Rejected artifacts: none.
