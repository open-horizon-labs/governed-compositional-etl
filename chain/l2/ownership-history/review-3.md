# Sketch review 3: job ownership-history (verdict: fail, one defect)

Reviewer: Opus judge, given S, K, the accepted CE, change-contract-3, review-2, and the model only.

Defect: the necessity text of `handoff.raw.customer_mgmt_action.ca_id->logical.account.account_number` enumerates account actions as (ADDACCT, UPDACCT, CLOSEACCT, INACT), omitting NEW and including INACT. Its sibling `action_type->logical.account.status` enumerates (NEW, ADDACCT, UPDACCT, CLOSEACCT). A next-level Developer holding only the model would: create an account statement when a customer becomes inactive (silently answering L1.hole.owner-change-reversions-account, the derivation change-contract-3 forbids); leave those statements without derivable status; and give first accounts no opening statement, so the carried-forward owner has nothing to carry from. Lesser instance: the customer identity handoff omits INACT from its enumeration while the status handoff requires INACT rows to produce customer statements.

Everything else holds: all clauses grouped; derivations subset of group parents; per_statement everywhere; is_current computed; owner carried forward under L1.identity and L1.history; no batch_date, cdc_flag, ca_name, or ca_b_id handoffs; five authorized standing facts only; the four job feedback conditions each map to an invariant. Review-2 findings 1 to 5 all addressed.

Authorized corrections (projection defects under the current Sketch and anchors): align the account action set to {NEW, ADDACCT, UPDACCT, CLOSEACCT} in the account identity and owner handoffs, state that INACT and UPDCUST are customer changes yielding no account statement and that re-versioning is L1.hole.owner-change-reversions-account; align the customer action set to {NEW, UPDCUST, INACT} in the customer identity handoff; add a review trigger for an INACT or UPDCUST row claimed to require an account statement; mention the first-statement case in the carried-forward owner rule.

Reviewer's K rule, mechanized in the gate: enumerations of received action codes across handoffs into the same entity must be identical, and every code named must be one the anchors define as applying to that entity's subject.
