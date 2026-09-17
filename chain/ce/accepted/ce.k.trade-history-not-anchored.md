### CE: ce.k.trade-history-not-anchored

- Status: approved (anchor amendment, data-architect hat; see .oh/metis/issue-8-scd2-versioning-adjudication.md addendum)
- Level: K (anchors), observed at L3 review of trade-lifecycle on duckdb-sqlmesh; confirmed on duckdb-native
- Input and simulation context: trade 353232's only anchored report is the Batch1 historical snapshot row (status CMPT, t_dts 2017-04-10 20:26:42). The brokerage also holds Batch1 TradeHistory rows for it (per-status times), which phase 1 used and this chain did not anchor.
- Projection output: placed_at = the completion-time t_dts; first_seen_late = true; ownership pinned as of that moment.
- Corrected output or behavior: placed_at = the earliest per-status report's time (the pending or submitted row in TradeHistory); first_seen_late = false when that history exists.
- Classification: anchor gap (the source set omits a file the brokerage holds), which makes L1.placement-moment's "earliest report the brokerage holds" evaluate over the wrong set. Not an L1 gap: the clause is right; the anchors under-state what is held.
- Proposed change: anchor `raw.trade_history` (th_t_id, th_dts, th_st_id) as a Batch1 source with its natural identifiers; add the two trades' history rows to the chain fixture from the real Batch1 file; then an authorized trade-lifecycle L2 change adds a handoff from raw.trade_history.th_dts under first_encounter_only for placed_at and lets first_seen_late consider history rows. Expected cone: sg.placement-moment stale; the two trade L3 artifacts re-project; every other group and artifact is a hit.
- Adjacent behavior not authorized: completion timing (L1.hole.trade-timestamps); market-order first encounters (ce.l1.first-seen-late-market-orders).
- Tempting wrong repair: treating the historical snapshot row's status as an ordinary first report and adjusting the first_seen_late rule to exempt Batch1 rows; that hides the missing source instead of anchoring it.
- Proposed by: projection reviewer (Opus), trade-lifecycle on duckdb-sqlmesh.
- Approved or rejected by: pending, data-architect hat (anchor) and the trade-lifecycle L2 authority (handoff).
