# Review 6 (sketch reviewer, scoped): job positions (verdict: pass)

Scope: the cycle-6 delta against `selected-model.json` (cycle 5) under `change-contract-6.md`. Gate ok, zero problems; invariants 13 to 14. Reviewer: Opus sketch reviewer, seven scope questions.

## Findings

1. **Restatement: pass.** `inv.eligible_holding_report_persisted` claims only the grain half (eligible pair implies exactly one row): the group's stated one-row-per-pair plus sg.holding-attribution's stated exclusion. It is silent on non-eligible pairs; the biconditional comes from pairing it with the pre-existing ownership-present invariant. The D-touched case is handed to L1.hole.deletions by name, wording parallel to trade-lifecycle's completeness invariant.
2. **Citations: pass.** identity and holdings-follow-trade suffice for a cardinality claim; attribution-at-placement earns the frozen half, which this invariant does not claim.
3. **Determinism: pass.** Every term is nameable and recomputable; the upper half of "exactly one" is structurally unreachable under an identity-keyed rebuild, so the teeth are the zero-row half; the `IS NULL OR IN ('I','U')` reading is correctly demoted to the parallel assumption.
4. **Group placement: pass**; row existence per pair is the entity's shape. hole.deletions bounds it; hole.batch_identity is not owed here (the tie is about quantities, which sg.no-phantom-positions carries).
5. **Reconciliation text: pass.** States a fact (the two readings coincide under trade-lifecycle's pin-present invariant, and a dropped trade is already a violation upstream) without importing join shapes or granting permission; both engine behaviours are upstream violations.
6. **hole.batch_identity: pass**; widens to the tie without picking a candidate, in the house formula.
7. **Unchanged elsewhere: pass**, structural diff.

Rejected element ids: none.

## Notes carried to the next text cycle

- `sg.holding-shape.coverage_claim` is now the only group claim that does not narrate its own invariant member by name; one sentence owed, and its gap illustration should widen from D-only to any-D abstention.
- "the two engines" in the coverage claim ties an L2 note to the current L3 roster; "two projections that differ in this way" carries the fact without counting engines. "The two cases coincide" compresses "the two readings coincide".
- `inv.holding_quantity_updates_in_place.parallel_assumption` does not mention the tie; a pointer to hole.batch_identity is worth adding.
- Residual recorded, not closed: the native-side silence for a trade persisted with null pins persists at L2 and is caught upstream only; the contract chose text plus the converse invariant over restating current-trade-known, and the text now makes that visible.

## Note for L3 cycle 3

Implement the D scope as a whole-pair abstention (no D report anywhere for the pair), not a per-row filter; the per-row reading would demand a row for a mixed I+D pair and decide L1.hole.deletions in SQL.
