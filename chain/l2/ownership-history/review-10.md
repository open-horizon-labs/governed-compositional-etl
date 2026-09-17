# Review 10 (sketch reviewer, scoped): job ownership-history (verdict: pass)

Scope: the cycle-10 delta to `semantic-model.json` (commit 864827a vs. abc6651: 8 hunks, +123/-4) against `change-contract-10.md`, read alongside the L1 Sketch, `L2-FORMAT.md`, `sources-v1.json` (action_type_meanings: codes, fields_present, subjects, status_codes) and `chain/l3/duckdb-native/ownership-history/mutation-findings-1.md`. The reviewer also ran the L2 gate read-only: status ok, no problems, no questions, 16 invariants.

Reviewer: Opus sketch reviewer (scoped review, six questions: restatement fidelity, citations, determinism, attribute feedback, unchanged elsewhere, mutation firing).

## Findings

1. **Restatement, no more.** Each new invariant reproduces what its handoff or the attribute's own derivation already states. `inv.customer_status_matches_producing_source` reproduces the `status_from_action_meaning` mapping (NEW, UPDCUST active; INACT inactive) and its deferred-CDC counterpart. `inv.account_status_matches_producing_source` reproduces the account action mapping plus the `ce.account_changes.status_id` pass-through. The tier and tax-treatment invariants reproduce the direct handoff where `fields_present` carries the field and the attribute's `carried_forward_from_previous_statement` rule where it does not (INACT, CLOSEACCT). The owner invariant reproduces the c_id handoff plus the carry-forward already declared for ce rows. No invariant resolves a hole or decides a code meaning not already decided by its handoff.
2. **Citations.** `derived_from` on each invariant equals the union of the clauses cited by the handoffs and derivations it checks; all five are subsets of their group's `parent_clauses` (`sg.statement-content`, `sg.owner-standing`).
3. **Determinism.** All five are recomputable from anchored sources: status from `action_type` via `action_type_meanings.codes` or the ce row's `status_id`; tier and tax from the row's own field where present, otherwise from the immediately preceding statement, which L1.identity and L1.history make well defined. The historical/constructed partition is available from `provenance`, guaranteed both ways by `inv.constructed_scenarios_labeled`.
4. **Feedback.** All five appear in the checked attributes' `feedback` (customer.status, customer.tier, account.status, account.tax_treatment, account.owning_customer_number). Handoff feedback lists untouched, as the contract authorized attribute feedback only.
5. **Firing on the three unprotected mutations.** Yes for all three. Status swaps: expected status recomputes from `action_type` or `status_id`, columns the mutation does not touch. Tax swap: directly sourced statements compare to `ca_tax_st`/`tax_status_id`; a CLOSEACCT statement compares to its predecessor; the only swap that leaves both sides consistent is between two consecutive carry-forward statements holding the same value, which is not a value-changing mutation. Every carry-forward chain terminates at a direct-source statement, so no blind spot.
6. **Unchanged elsewhere.** The 8 hunks are exactly five `feedback` additions, one block adding five invariants, and two group edits (members and one appended coverage sentence each). No type, entity, handoff, hole, question, gap, disposition or parallel_assumption outside the new elements changed.

Failure class: none. Rejected element ids: none.

## Caveat carried forward (not a cycle-10 defect)

`sources-v1.json` states a status only for INACT, CLOSEACCT and by wording ADDACCT. It states none for UPDCUST or UPDACCT and none explicitly for NEW. "Active"/"open" for those codes is the reading the `status_from_action_meaning` handoffs took at an earlier cycle and recorded in `parallel_assumption`; the new invariants restate that reading verbatim. An L3 audit built from them is exactly as strong as that assumption. Standing anchor-authority question, recorded here so the CE archive can pick it up if business disagrees.

## Notes for the L3 Developers (both targets)

- Audits must not be circular. Customer audits join the producing action by `(customer_number, effective_from)` against `(c_id, action_ts)`, the declared identifier. Account audits (status, tax, owner) join by `(account_number, effective_from)` against `(ca_id, action_ts)`, which is unique in practice though not a declared identifier of `raw.customer_mgmt_action`; joining account audits through the owning customer would multiply rows for a customer holding more than one account. (Corrected after the L3 review of cycle 3 on duckdb-native found the first wording wrong; the L3 contracts had the right join.)
- Carry-forward arms are best recomputed from the anchored source rather than from the projected column; either implementation is swap-sensitive.
- Asymmetry faithful to the contract: the customer status invariant states the CDC-undeferred case in its `statement`; the account status invariant leaves the deferred case to `parallel_assumption`.
