# Review 8 (coordinator, scoped): ownership-history on duckdb-sqlmesh (verdict: pass)

Scope: one audit added under the new clause `L1.closed-account-activity`, `audits/inv.account_statement_never_created_by_activity.sql`, its manifest registration and the provenance move. Read in full.

The audit checks that every persisted account statement traces to a permitted producer: an account-subject customer management action (NEW, ADDACCT, UPDACCT, CLOSEACCT) or a labeled constructed change row. It is non-circular, reading the sources rather than the column under test; it reads only `governed.account` and those two sources; and the customer-subject codes are correctly absent, since they produce no account statement. The two engines express it differently, a union and a left join against two left joins, with the same semantics.

Evidence: run ok with every audit at zero; two-phase ok; mutate zero unprotected. The statement is the checkable half of "activity never reopens an account: no trade creates a statement"; the other half of the clause, the post-closure trade report, is trade-lifecycle's and is stated as such in the group's coverage claim.

Process note: both Developers correctly refused to stamp their own work and said so, one of them also disclosing a self-stamp from an earlier cycle that predated the contract section. That disclosure is the behaviour the boundary is for. Rejected artifacts: none.
