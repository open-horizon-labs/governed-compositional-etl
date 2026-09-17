# Change contract, cycle 9: L1 -> L2, job trade-lifecycle (what review 8 found)

- **Prior policy authority:** unchanged (`sketches/l1-brokerage-intent-v1.md`, the clauses for `job:trade-lifecycle`; `selected-model.json` at cycle 7).
- **Exact active change authority:** `review-8.md`. The D scoping and the two-source wording of `inv.every_received_trade_persisted` came from `change-contract-8.md`; this contract corrects it.
- **Authorized corrections:**
  1. `inv.every_received_trade_persisted.statement`: quantify over trade_numbers none of whose received reports carries cdc_flag D (a trade with any D report is L1.hole.deletions' case and is not claimed here); for those, exactly one logical.trade row exists. Reconcile the `parallel_assumption` so it no longer contradicts the statement.
  2. Same element, `parallel_assumption`: record the anchored shape fact that makes the raw.trade_history clause a restatement: `trade_code_meanings.report_order.note` states that a historical-load trade's held reports are its TradeHistory rows together with the snapshot Trade row, so every th_t_id also appears as a Batch1 t_id and the entity's only identity handoff (raw.trade_cdc.t_id) reaches every history-reported trade. Add as `review_trigger` a th_t_id with no t_id row in any batch.
  3. Add `inv.trade_ownership_pin_present` to the feedback of `handoff.logical.account.owning_customer_number -> logical.trade.owning_customer_number`.
  4. `sg.placement-moment.coverage_claim`: one sentence naming `inv.trade_ownership_pin_present` as the checkable restatement that the pin resolved, in the group's own convention.
  5. `sg.trade-identity.coverage_claim`: state that the group now claims completeness as well as consistency (every received, non-deleted trade appears exactly once) and name the new invariant; `sg.trade-identity.gap`: name `L1.hole.deletions` (a trade with a D report is not claimed); add `sg.trade-identity` to `hole.deletions.blocks` for the two-way agreement the gate checks.
- **Current rules that must be preserved:** all clauses; every cycle-8 element stands except as enumerated; no other text moves.
- **Conflict protocol reminder:** if any item cannot be done without editing text this contract does not name, file exactly one question in `questions_for_authority`, omit the affected element, and return.
- **Acceptance:** `.venv/bin/python scripts/chain_l2.py check trade-lifecycle` ok with zero problems; diff against `selected-model.json` confined to cycle 8's elements plus the corrections above.
