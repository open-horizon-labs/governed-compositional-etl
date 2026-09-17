# Review 11 (sketch reviewer, scoped): job trade-lifecycle (verdict: fail, three elements; one point needs authority)

Scope: the cycle-11 delta against `selected-model.json` (cycle 10) under `change-contract-11.md`, compiled from the amended `L1.placement-moment` and the new `trade_type_codes` anchor. Gate ok; diff confined to the four contract items. Reviewer: Opus sketch reviewer, six scope questions.

## Findings

1. **Derivation fidelity: fail on one case.** The rule says "other than the order's first lifecycle event" where the contract said "later than"; the two coincide for limit orders and differ for exactly one case, a market order first reported PNDG, which the rule decides (late) while also listing as a review trigger. The clause does not decide it: a market order seen pending contradicts the premise that it has no pending stage. Correct elsewhere: market first reported CMPT or CNCL is late; limit first reported SBMT is late; market first reported SBMT is not, the CE's assertion. Unanchored order types are left undefined with a review trigger, the right shape.
2. **Anchor use: overreach in three prose fields.** The anchor's own note says which lifecycle stages an order type passes through is not stated there; the derivation rule cites the Sketch sentence correctly, but the necessity, parallel_assumption and the invariant statement say "anchored first lifecycle event". Only the code shape is anchored.
3. **New attribute and handoff:** frozen_from_first_encounter is substantively right, but `L1.attribution-at-placement` on the type is a gate-appeasing citation (it is about the ownership reference). The honest citation is `L1.lifecycle-mutates-outcome`: it enumerates what a later report changes, and order type is in neither the outcome set nor the ownership set. The gate rule stands; the citation gives. nullable false rests on the same premise as owning_account_number; first_encounter_only is right.
4. **Invariant:** deterministic in form, inherits the "other than" reading, and has no truth value for an unanchored type while claiming deterministic; that case must be explicitly unclaimed.
5. **Containment: pass**, with one stale sentence: the coverage claim still carries the pre-amendment "other than PNDG" sentence beside its replacement.
6. **Filed question owed:** is a market order whose earliest held report is PNDG first seen late, or an incoherent observation? The clause is silent; the Developer answered it. The coordinator, acting as business proxy in this demonstration, declines to answer it and files it.

Failure class: unauthorized decision on a case the contract reserved for review; anchor attribution overreach; one gate-appeasing citation.

Rejected element ids: `logical.trade.first_seen_late`, `inv.trade_first_seen_late_matches_status_order`, `type.trade_order_type`. Standing: `logical.trade.order_type`, the t_tt_id handoff, the group membership. Corrections in `change-contract-12.md`.
