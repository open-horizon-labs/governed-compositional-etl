# Sketch review 2: job ownership-history (verdict: fail)

Reviewer: Opus judge, given S, K, the accepted CE, change-contract-2, review-1, and the model only.

Findings (full text retained in the session transcript, 2026-09-17):

1. The one fully projectable account source, `ce.account_changes`, produces content-free statements: no handoffs from its `status_id` and `tax_status_id` although the anchor lists them and nothing blocks them. Violates the model's own `inv.account_statement_has_content` and `nullable: false`. `sg.constructed-scenarios` claims `gap: none` dishonestly.
2. `questions_for_authority` is empty while five elements say "see questions_for_authority".
3. `logical.customer.status` and `logical.account.status` are `nullable: false` with only deferred handoffs; a next-level Developer is told status is mandatory and given no source.
4. `sg.statement-content` overclaims for the historical source (tier and tax treatment only, no status) and its gap does not bound the status shortfall.
5. `L1.hole.closed-account-activity` and `L1.hole.batch-identity` neither recorded nor dismissed in the model; closed-account-activity is now more relevant because account status is derived content.

Review-1 findings: 1, 3, 4, 7 addressed; 2 partly; 5 addressed in form, open in substance; 6 still open.

Retained and must not regress: same-moment owner lookup; no batch_date to effective_from handoff; no cdc_flag handoff; no status invented from action_type (now anchored for cycle 3); standing facts limited to the five the CE authorizes; no engine, SQL, table, or file names.

Reviewer's proposed anchor rule (K, not S): a group whose members include a source handoff into a versioned entity must cover that source's standing-fact fields or record why not. Mechanized in the gate as: a source that supplies a candidate effective time for a versioned entity must supply a candidate handoff for every non-nullable attribute of that entity, or the attribute must be nullable, deferred, or rejected with a reason.
