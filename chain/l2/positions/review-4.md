# Review 4 (sketch reviewer, scoped): job positions (verdict: fail, narrow)

Scope: the cycle-4 delta against `selected-model.json` under `change-contract-4.md`. Gate ok, zero problems. Reviewer: Opus sketch reviewer, seven scope questions.

## Findings

1. **Restatement: pass.** Each of the six invariants reproduces a derivation, handoff, grain, nullable flag or stated group rule. `inv.holding_change_current_trade_known` asserts resolution only and hands the meaning back to the business; `inv.holding_change_ownership_present` restates the exclusion the coverage claims already state. Drafting note: ownership_present's second sentence ("excluded from this entity entirely rather than persisted with a null ownership reference") is not audit-checkable and duplicates its parallel_assumption; it belongs there.
2. **Citations: subsets, but two invariants under-cite by construction.** `inv.holding_quantity_change_is_difference` and `inv.holding_quantities_present` sit in `sg.holding-shape`, whose parents exclude L1.no-phantom-positions, while the derivation they restate cites it and their necessity argues from it.
3. **Determinism: pass.** The sum invariants' "exactly one position row per key" clause is checkable both ways and has teeth: the `(428, NULL)` phantom group from the native review is a key-existence failure that it and ownership_present now catch together. Scope of current-trade-known (reports whose cdc_flag is not D) is consistent with `inv.holding_quantity_updates_in_place` and the widened hole. L3 note: historical rows carry null cdc_flag, so an L3 that writes `cdc_flag <> 'D'` drops every historical report; it must write `IS DISTINCT FROM 'D'`.
4. **Group placement: the literal placement is not defensible.** Both quantity invariants touch zero members of sg.holding-shape, all their checked elements live in sg.no-phantom-positions, and sg.holding-shape's own coverage claim says its scope "is limited to the entity's shape and its two identity attributes." The contract's items 1 and 5 were a drafting slip (item 2 places the sums correctly). The Developer followed the contract literally and reported the tension in prose instead of filing the one question the conflict protocol asks for. Cache cost today: zero (holding_change.sql derives from all three groups); the cost is the forward coupling the group mechanism exists to prevent.
5. **Feedback: one omission, one out-of-contract touch.** `handoff.raw.holding_history.hh_t_id -> current_trade_number` does not list current-trade-known though the invariant's parallel_assumption is that handoff's own. `type.holding_quantity.feedback` was touched (types were not in the authorized list) while `type.holding_quantity_change`, constrained by both new invariants, was not.
6. **Unchanged elsewhere: pass**, verified structurally.
7. **Holes: nothing resolved; the widening opens an unnamed gap.** `hole.deletions` now bounds row existence of a holding_change row, which is sg.holding-shape's row-per-pair claim, yet `sg.holding-shape.gap` reads none. Not authorized by the contract; needs the next one. Wording nit: "this job's current projection, which yields no row" imports L3 into L2; the no-row outcome follows from the selector and nullability.

Failure class: sufficiency-group bookkeeping against text the contract did not hand over, reported in prose rather than filed as a question.

Rejected element ids: `inv.holding_quantity_change_is_difference`, `inv.holding_quantities_present` (as placed; text stands).

Coordinator note: the contract author's slip, corrected in `change-contract-5.md`, which also authorizes the gap and blocks edits the reviewer routed to authority.
