# Change contract, cycle 5: L1 -> L2, job positions (what review 4 found)

- **Prior policy authority:** unchanged (`sketches/l1-brokerage-intent-v1.md`, the clauses for `job:positions`; `selected-model.json` at cycle 3).
- **Exact active change authority:** `review-4.md`. Items 1 and 5 of `change-contract-4.md` placed two invariants in the wrong group; this contract corrects the contract.
- **Authorized corrections:**
  1. Move `inv.holding_quantity_change_is_difference` and `inv.holding_quantities_present` to `sg.no-phantom-positions` (their `sufficiency_group` field and the two groups' `members` lists); extend each `derived_from` with `L1.no-phantom-positions`, the clause their necessity argues from and the clause the quantity_change derivation cites. `sg.holding-shape` then reverts to its selected text. Name both in `sg.no-phantom-positions.coverage_claim`.
  2. Add `inv.holding_change_current_trade_known` to the feedback of `handoff.raw.holding_history.hh_t_id -> logical.holding_change.current_trade_number`.
  3. Types: add `inv.holding_quantities_present` and `inv.holding_quantity_change_is_difference` to the feedback of both `type.holding_quantity` and `type.holding_quantity_change` (the touch on the first is now authorized; the second is owed for consistency).
  4. `hole.deletions` closing clause: drop "this job's current projection, which yields no row for such a pair"; say that with no I, U or historical report as a candidate, the non-nullable before_qty and after_qty cannot be filled, so the model yields no row, and that this is one behavior consistent with the hole, not a resolution.
  5. `sg.holding-shape.gap`: name `L1.hole.deletions` (row existence of a holding_change row for a D-only pair is undecided), and add `sg.holding-shape` to `hole.deletions.blocks`, keeping the two-way agreement the gate checks.
  6. `inv.holding_change_ownership_present.statement`: keep only the checkable sentence (all four ownership attributes non-null on every persisted holding change); move the exclusion rationale to `parallel_assumption`.
- **Current rules that must be preserved:** all clauses; every cycle-4 element stands except as enumerated; no other text moves.
- **Conflict protocol reminder:** if any item here cannot be done without editing text this contract does not name, file exactly one question in `questions_for_authority`, omit the affected element, and return. Do not follow a contract you can see is wrong; say so through the protocol.
- **Acceptance:** `.venv/bin/python scripts/chain_l2.py check positions` ok with zero problems; diff against `selected-model.json` confined to cycle 4's elements plus the corrections above.
