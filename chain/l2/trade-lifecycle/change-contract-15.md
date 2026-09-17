# Change contract, cycle 15: L1 -> L2, job trade-lifecycle (reports are held as wholes; a held first report)

- **Exact active change authority:** `L1.unknown-codes` now says a report is held as a whole (one unknown code holds the record, not the field); new hole `L1.hole.held-first-report-placement`; `chain/l3/duckdb-native/trade-lifecycle/review-6.md`.
- **Authorized corrections:**
  1. Every raw.trade_cdc handoff's parallel_assumption (t_id, t_ca_id, t_dts, t_st_id, t_tt_id and the five outcome handoffs) and the raw.trade_history th_dts handoff: a report carrying any unknown code (cdc_flag, status, order type) is held as a whole and supplies no fact to any handoff; a held later report is not a later report; a trade whose every report is held is not yet known.
  2. Carry the new hole; `sg.placement-moment.gap` names it; `placed_at`'s parallel_assumption and `inv.trade_placed_at_matches_earliest_report` state that a trade whose earliest report is held is unclaimed until the hole is answered (the trade is held and reported by `inv.unknown_codes_held`; no row); `inv.every_received_trade_persisted` and `inv.trade_first_seen_late_defined_or_held` agree (a trade with a held first report is unclaimed).
  3. `inv.trade_outcome_updates_in_place`: restate so a later report that is held is not a later report (statement, not only the handoffs' assumptions).
  4. `inv.every_received_trade_persisted`: say "received raw.trade_cdc report" where the anchors make that the only source of a trade row, or keep "received report" and say why trade_history alone cannot create a trade.
- **Acceptance:** gate ok; diff confined; no question owed (the Sketch carries both).
