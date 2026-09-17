# Review 8 (sketch reviewer, scoped): job trade-lifecycle (verdict: fail, one element)

Scope: the cycle-8 delta against `selected-model.json` under `change-contract-8.md`. Gate ok, zero problems, holes carried unchanged; the diff is exactly the enumerated set. Reviewer: Opus sketch reviewer, seven scope questions.

## Findings

1. **Restatement: split.** `inv.trade_ownership_pin_present` is a clean restatement of four `nullable: false` flags and refuses all three remedies for an unpinnable trade by name. `inv.every_received_trade_persisted` restates the entity grain and identity on its raw.trade_cdc half; two parts reach past that (defects A, B). The hole sentence describes what the invariants make visible and hands the decision back; it does not widen or resolve.
2. **Citations: pass.** Three clauses for pin-present is the honest citation: two of the four attributes exist only because L1.as-of and L1.placement-moment define the pin. L1.identity and L1.lifecycle-mutates-outcome correctly not cited.
3. **Determinism: pin-present yes; the second invariant is ill-defined in two cases.** Defect A: an existential over non-D reports keeps a trade with an I row and a later D row in scope and demands its row, which answers L1.hole.deletions in favour of "the row stays" while the element's own parallel_assumption says the hole bounds it. The analogy to `inv.trade_outcome_updates_in_place` does not carry: that one is a rule about what a report does, this one about row existence. Defect B: the raw.trade_history clause demands a row for a history-only trade that no handoff derives (the only identity handoff is from raw.trade_cdc.t_id), and both engines build the entity from the CDC feed; the L3 Developer could discharge it only by inventing a handoff. The anchor's `report_order.note` states that a historical-load trade's held reports are its TradeHistory rows together with the snapshot Trade row; cited, that makes the clause a restatement.
4. **Divergence closed on both engines.** Native (LEFT JOIN pins) fires `inv.trade_ownership_pin_present`; SQLMesh (inner join) fires `inv.every_received_trade_persisted`. No third behavior satisfies both, which is the intent; the CE's deterministic assertion holds.
5. **Feedback: one wrong omission.** `handoff.logical.account.owning_customer_number -> logical.trade.owning_customer_number` is the sole producer of an attribute the invariant names and its review_trigger is precisely the null-producing case; the model's convention puts invariants on every handoff feeding a named attribute.
6. **Unchanged elsewhere: pass**, field-level.
7. **Coverage claims need the next contract.** `sg.placement-moment.coverage_claim` should name the new member as it names every other invariant; `sg.trade-identity.coverage_claim` describes identity consistency only while the group now claims completeness over two sources, and its `gap` reads none though the new member's parallel_assumption names L1.hole.deletions (precedent: sg.outcome).

Failure class: over-reach into a reserved hole and an unrestated clause in one new invariant, with one feedback omission.

Rejected element ids: `inv.every_received_trade_persisted`. `inv.trade_ownership_pin_present` stands.

Coordinator note: the D scoping and the two-source wording came from the contract; corrected in `change-contract-9.md`, which also authorizes the group texts and gap.
