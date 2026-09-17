# Change contract, cycle 7: L1 -> L2, job positions (text consistency after cycle 6)

- **Prior policy authority:** unchanged (`sketches/l1-brokerage-intent-v1.md`, the clauses for `job:positions`; `selected-model.json` at cycle 6).
- **Exact active change authority:** none new. Text corrections authorized by `review-6.md` (notes carried to the next text cycle).
- **Authorized corrections:**
  1. `sg.holding-shape.coverage_claim`: one sentence naming `inv.eligible_holding_report_persisted` as the checkable form of the row-per-pair half; widen the gap illustration from "a pair whose only reports are D-flagged" to the any-D abstention the invariant takes.
  2. `sg.holding-attribution.coverage_claim`: replace "the two engines" with "two projections that differ in this way", and "the two cases coincide" with "the two readings coincide". Apply the same "two projections" wording in `inv.holding_change_current_trade_known.parallel_assumption` if it counts engines.
  3. `inv.holding_quantity_updates_in_place.parallel_assumption`: add a pointer that when several reports of one pair tie under report_order, "a later report" is not well defined and the tie is L1.hole.batch-identity's case, as `hole.batch_identity` now states.
  4. `inv.eligible_holding_report_persisted.necessity`: where it calls itself "the converse of inv.holding_quantity_updates_in_place's second clause", say instead "the converse of the persisted-pair-without-report case that invariant's audit covers"; the direction is right, the reference was loose.
- **Current rules that must be preserved:** all clauses; every cycle-6 element stands except the four texts above.
- **Acceptance:** `.venv/bin/python scripts/chain_l2.py check positions` ok; diff against `selected-model.json` confined to the four fields.
