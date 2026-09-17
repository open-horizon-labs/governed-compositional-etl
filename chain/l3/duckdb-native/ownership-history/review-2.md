# Review 2 (sketch reviewer, scoped): ownership-history on duckdb-native, L3 cycle 3 (verdict: pass)

Scope: the five audits added under `change-contract-3.md` for the cycle-10 value-correctness invariants, their manifest registration, and the manifest's move to the selected snapshot. Entity SQL and the eleven earlier audits verified byte-unchanged. Evidence: check ok (16 audits); run ok, 16 at zero; mutate 18 mutations, zero unprotected, with the three previously unprotected swaps each caught by the audit built for it (`mutation-findings-2.md`).

Reviewer: Opus sketch reviewer, eight scope questions.

## Findings

1. **Faithfulness: pass.** Each audit restates its invariant's arms with the action-code sets the invariant names, matching `fields_present`. The customer status invariant's CDC clause is correctly absent (deferred handoff). The three carry-forward audits split arms by null-ness of the carried field rather than by code; under `fields_present` the two coincide.
2. **Non-circularity: pass.** Governed tables appear only as the compared column and the join keys; every expected value, direct and carried, is computed over the anchored sources ordered by their own timestamps.
3. **Join correctness: pass, caveat carried.** Customer audits join on the declared identifier. Account audits join `(account_number, effective_from)` to `(ca_id, action_ts)` or the ce row's timestamp, unique in practice but not declared. Two account actions at one timestamp with different customers would let the status audit pass silently and make the tax audit tie-order dependent, as `account.sql` already is; a ce row colliding with a historical row is caught by `inv.account_asof_has_unique_answer`. Authority-level item, not an L3 defect.
4. **Null sensitivity: pass.** `IS DISTINCT FROM` in all five; legitimately null expected values are excluded by invariants the entity SQL already cites.
5. **Status vocabulary: pass.** ACTV and INAC on both sides, matching the anchor's status_codes.
6. **Read containment: pass**, mechanically enforced.
7. **Manifest: pass.** Five entries with correct entity and invariant ids; `derived_from_model` now names the selected snapshot at the current review sha; nothing else moved.
8. **Standing caveat: encoded exactly, and now disclosed.** The audits encode active for NEW, UPDCUST, UPDACCT exactly as the invariants do. The reviewer found the headers attributing that to "the anchored meaning"; the Developer reworded both status audit headers to attribute it to the invariant's `parallel_assumption`. A code-set filter on the customer status join, added on this review's suggestion, was reverted after the sibling target's review showed the unfiltered form (exhaustive CASE falling to null) is stronger: it turns a statement wrongly produced from an account-subject action into a violation rather than a dropped row. Behavior unchanged on correct data, verified by check and run.

Failure class: none.

## Recorded, not failures

- The three carry-forward audits reuse the projection's window expression; they catch substituted values, not a mis-stated carry-forward rule.
- The L2 review's note on account audit joins was wrong (through the owning customer) and has been corrected in `review-10.md`; the L3 contract had the right join and the Developer followed the contract.

## For authority (CE proposals)

- `(ca_id, action_ts)` uniqueness in `raw.customer_mgmt_action`: an anchor amendment declaring account-subject uniqueness, or an L2 invariant asserting one producing row per `(account_number, effective_from)`.
- The NEW / UPDCUST / UPDACCT status reading, standing from review 10, now relied on in two engines' audits as well as the entity SQL: an anchor-authority question.

Rejected artifacts: none.
