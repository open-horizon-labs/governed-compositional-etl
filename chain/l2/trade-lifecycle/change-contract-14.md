# Change contract, cycle 14: L1 -> L2, job trade-lifecycle (review 13; the Sketch clarification on held reports)

- **Exact active change authority:** `review-13.md`; `L1.unknown-codes` as clarified (a held report changes nothing and creates nothing; facts stand as last stood; a trade known only through held reports is not yet known; the hold is reported).
- **Authorized corrections:**
  1. `sg.placement-moment.parent_clauses`: add `L1.unknown-codes` (first_seen_late's held cases derive from it); `inv.trade_first_seen_late_defined_or_held.derived_from` cites it.
  2. Held scope: qualify every "held" phrase on `first_seen_late` (review_trigger) and `inv.trade_first_seen_late_matches_status_order` to "held on its first-encountered report's status or order type, or a market order seen pending"; an unknown code on a later report does not make first_seen_late null.
  3. The five outcome handoffs and the t_st_id handoff (latest_change): restate the sentence under the clarified clause: a held later report is not a later report for latest_change; the outcome stands as last derived; the hold is reported by `inv.unknown_codes_held`. No nullability change.
  4. The three selection handoffs (`t_id -> trade_number`, `t_ca_id -> owning_account_number`, `t_dts -> placed_at`): they read cdc_flag to select rows; add the sentence and the feedback. Under the clarified clause, a trade whose every report is held is not yet known: no logical.trade row; `inv.every_received_trade_persisted` restated to quantify over trades with at least one report whose codes are all anchored and none D, and to say a trade known only through held reports is unclaimed and reported by `inv.unknown_codes_held`.
  5. `sg.unknown-codes.coverage_claim`: enumerate readers correctly (all ten) ; `gap`: none; remove `sg.unknown-codes` from `hole.market_order_seen_pending.blocks` (its member is candidate); move the adjacency remark into the coverage claim.
  6. Serialize with ensure_ascii false and a trailing newline; touch no other bytes.
- **Acceptance:** gate ok; diff confined to cycle 13's elements plus the above; no question left owed (the Sketch now carries both).
