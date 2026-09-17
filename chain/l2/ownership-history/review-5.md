# Sketch review 5: job ownership-history (verdict: pass, no exclusions)

Reviewer: Opus judge, given S, K, the accepted CE, change-contract-4, review-3, and the model only. Cycle 4 fixed the enumerations; cycle 5 applied the clarified L1.constructed-scenarios.

Holds: two versioned entities, per_statement on every non-identity attribute; is_current computed; owner handed off from the historical file and otherwise carried forward; exactly the five authorized standing facts; all CDC handoffs deferred under L1.hole.change-effective-time; no batch_date, cdc_flag, cdc_dsn, ca_name, or ca_b_id handoffs; every clause grouped; derivations subset of group parents; four feedback conditions map to invariants; no engine, SQL, table, or file names.

Review-3 findings: all addressed; nothing regressed.

Cache adjudication (Jev had routed both to review): sg.statement-content unchanged by the clause clarification, could have been kept; sg.constructed-scenarios changed, had to add inv.constructed_account_change_refers_to_known_account and tighten the constructed identity handoff's trigger.

Wording tightenings for the next cycle's contract, not blocking: the constructed identity handoff's parallel assumption still says "already or separately established" (loosen than the clause); the known-account invariant's statement is stronger than the clause and its parallel assumption looser; an account known only through an incremental change file has no projectable earlier statement while L1.hole.change-effective-time is open.
