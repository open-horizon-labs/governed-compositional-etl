# Change contract, cycle 18: L1 -> L2, job trade-lifecycle (the business answered the pending-market-order question)

- **Prior policy authority:** `selected-model.json` at cycle 17.
- **Exact active change authority:** `L1.placement-moment` as amended and `L1.hole.market-order-seen-pending` as answered and closed, by the business accepting `chain/ce/accepted/ce.l1.market-order-seen-pending.md`. The answer: the brokerage's own systems record a market order as pending on receipt, before routing it; that pending record is the order's own first lifecycle event, so such a trade is **not** first seen late. Cache: `sg.placement-moment` stale (Jev 0.59 and 0.42, low, review; adjudicated invalidate). The L2 gate already rejects this model for citing a hole L1 no longer has.
- **Authorized changes (confined to sg.placement-moment):**
  1. Remove the carried hole `hole.market_order_seen_pending` and every citation of it (the group's `gap`, any `parallel_assumption` or `review_trigger` that defers to it).
  2. Delete `inv.trade_market_order_seen_pending_held`: the case it reported is decided and is no longer held. Remove it from the group's members and from every `feedback` list.
  3. `logical.trade.first_seen_late.derivation.rule`: a market order (TMB, TMS) is first seen late only when its earliest anchored report's status is later than SBMT in `status_order` (CMPT or CNCL); a report of PNDG or SBMT is the order's own first lifecycle event and is not late. A limit order (TLB, TLS) is unchanged: late when later than PNDG. The attribute stays nullable, but the only remaining held reason is an unknown code on the first-encountered report (and the trade is unclaimed then anyway); say so, and update necessity, parallel_assumption and review_trigger.
  4. `inv.trade_first_seen_late_matches_status_order`: restate over the new rule; the market-order-pending case is now **claimed**, not excluded.
  5. `inv.trade_first_seen_late_defined_or_held`: the held set shrinks to the unknown-code case; restate it.
  6. `sg.placement-moment.coverage_claim`: one sentence recording that the pending-market-order case is now decided by the clause rather than held.
- **Current rules that must be preserved:** every other element; `L1.hole.held-first-report-placement` stays open and everything that defers to it is untouched; no other group moves.
- **Conflict protocol reminder:** one question, omit the element, return, if the Sketch does not carry what an item needs.
- **Acceptance:** `.venv/bin/python scripts/chain_l2.py check trade-lifecycle` ok with zero problems; diff against `selected-model.json` confined to the elements enumerated here.
