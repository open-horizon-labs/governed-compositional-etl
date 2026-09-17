# Review 3 (sketch reviewer, scoped): ownership-history on duckdb-sqlmesh, L3 cycle 3 (verdict: fail, one artifact)

Scope: the five AUDIT files added under `change-contract-3.md`, their registration in `manifest.json` and in the two models' `audits (...)` lists. The git diff is exactly three hunks: two lines in customer.sql's audits list, three in account.sql's, and the manifest; no SELECT body or other MODEL property moved. Evidence: check ok (16 audits); run ok, 16 at zero; mutate 18 mutations, zero unprotected; the three previously unprotected swaps each caught by the audit built for it.

Reviewer: Opus sketch reviewer, eight scope questions.

## Rejected artifact

`audits/inv.account_status_matches_producing_source.sql`, constructed arm. The invariant says status equals the ce row's own `status_id`. The audit computes expected as `CASE status_id WHEN 'ACTV' THEN 'ACTV' WHEN 'INAC' THEN 'INAC' END`, a copy of the model's `from_constructed` line rather than the invariant's text. A `status_id` outside that pair yields expected null on both sides and the audit reports nothing; `ce.account_changes.status_id` is an unconstrained string in the anchor, so the case is reachable. The residual surfaces as a null status under `inv.account_statement_has_content`, with the wrong name. Fix: expected is `status_id` unwrapped, as the native counterpart already has it. Failure class: restatement infidelity on the one arm where the projection's expression and the invariant's text differ.

## Other findings

1. **Faithfulness:** four of five faithful; action-code sets match `fields_present`. The tier and tax audits encode the `fields_present` gate explicitly, more faithfully than native.
2. **Non-circularity: pass.** Style note: the tier, tax and owner audits are structurally identical to the model's `filled` CTE; clone-and-compare still catches mutations and the window is equivalent to "immediately preceding statement".
3. **Join correctness:** as the corrected review-10 note directs. `(ca_id, action_ts)` is unique in practice, not declared; ties would make the tax and owner audits inherit the model's tie nondeterminism, with the duplicate statements themselves caught by `inv.account_statements_no_overlap` and `inv.account_asof_has_unique_answer`.
4. **Null sensitivity, 5. vocabulary, 6. read containment: pass.**
7. **Manifest and headers: pass.** Operational note taken: `group_fingerprints` are the coordinator's to refresh with `stamp` on acceptance.
8. **Standing caveat:** encoded exactly as the invariants, not disclosed in comments. One line per status audit requested.

## Coordinator decision on conflicting advice

The native review asked for a code-set filter on the customer status join for uniformity; this review shows the filter turns a would-be violation (a customer statement wrongly produced from an account-subject action) into a dropped row. The unfiltered form, with the exhaustive CASE falling to null, is stronger at no cost on correct data. Both targets align on the unfiltered form.

## For authority (CE proposals filed)

- `ce.k.account-action-uniqueness`: declare `(ca_id, action_ts)` unique for account-subject actions, or add an L2 invariant asserting one account action per key.
- `ce.k.constructed-status-vocabulary`: `ce.account_changes.status_id` has no declared vocabulary; if it is restricted to the anchored status codes the anchor should say so, otherwise the model's narrowing CASE in `from_constructed` is itself an unauthorized projection decision.

Rejected artifacts: `audits/inv.account_status_matches_producing_source.sql`. Alignment edits requested on `audits/inv.customer_status_matches_producing_source.sql` and both status audits' headers.
