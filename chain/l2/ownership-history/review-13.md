# Review 13 (sketch reviewer, scoped): job ownership-history (verdict: accept the element, cycle incomplete)

Scope: cycle 13 under `change-contract-13.md`, compiled from the business's answer to `L1.hole.closed-account-activity`. Gate question, zero problems, diff confined, byte hygiene clean.

## Findings

1. **`inv.account_statement_never_created_by_activity`: accepted.** It asserts only that an account statement is produced by an anchored action, an account change record or a labeled constructed row, never by a trade or holding, and that list is exactly this job's handoffs into `logical.account`. Correctly a must-hold and not a report: a statement traced to a trade would mean the projection is wrong.
2. **Independent of the two holes bounding its group**, correctly: change-effective-time bounds when a statement takes effect, deletions bounds what a deletion does to standing facts, and this invariant asserts neither.
3. **Finding A, substantive:** `sg.statement-content.coverage_claim` gained the clause as a parent and says nothing a reader can check against it. The gate sees structure, not prose. This job covers one part of a four-part clause checkably; the claim silently covers the whole.
4. **Finding B:** two review_triggers still treat activity after a closing statement as a reason to reassess, which the business has settled. On the received fixture they fire by design.
5. **The handoff sentence stays on the statements side** and disclaims the trade side by name.
6. **Nothing decides, re-attributes or unwinds.** The two 2017 trades remain attributed exactly as before.

Failure class: incomplete cleanup of an answered hole, in two directions: a sufficiency claim extended structurally but not in the prose a reader checks, and element triggers still firing on a settled condition. Rejected element ids: none. Corrections in `change-contract-14.md`.

## On the cheap screen

It pointed at the right element and called the depth correctly, and its contract-scope uncertainty was well earned. Its one mechanical flag was a false lead. It could not see Finding A at all: the defect is the *absence* of an edit, and a diff-scoped screen is blind to that by construction. Finding B was within reach, and the reviewer named the feature that would catch it: compare a changed field against the unchanged fields of the same element. Built and calibrated the same day; it scores 0.76 on this exact case against 0.42 on a control, but only when the settled question is supplied in the state.
