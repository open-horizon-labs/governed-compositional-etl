# Review 19 (sketch reviewer, scoped): job trade-lifecycle (verdict: pass with one revision)

Scope: cycle 19 under `change-contract-19.md`, the chain's first invariant carrying `reports: true`. Gate ok, zero problems.

## Findings

1. **`reports: true` is right and the clause forces it.** A projection that made these rows disappear, by dropping, re-pinning or unwinding, would be the defect. The clause names why the chain cannot resolve it: only the brokerage can say which of the closure and the trade is wrong.
2. **Restatement only, deterministic, and the upstream read is legitimate**: the pinned account statement's status is projectable and not deferred, and the dependency is stated in the parallel assumption rather than faked as a handoff. Verified against the built database: it fires on exactly trades 353232 and 372101, both pinning account 428's 2012 statement.
3. **Attribution untouched**, structurally confirmed.
4. **Nothing decides whether the closure or the trade is wrong.**
5. **Rejected: `sg.placement-moment.coverage_claim`.** It gained the clause as a parent and was edited only by deletion. Three sentences of the clause go unaddressed, including one this job genuinely carries: closing unwinds nothing already attributed, which `inv.trade_placement_reference_frozen` meets.
6. **Unchanged elsewhere**, structurally confirmed.
7. **The `reports` mechanism needed tightening, and got it:** the format anchor had landed four times with a wording variant; the flag was a free boolean no gate checked; it silently withdraws the invariant from mutation evidence while documenting only the relabeling; and it was silent on the unevaluable case. All four are now fixed, including a gate rule requiring `reported_because_clause` to name one of the element's own clauses.
8. **One question owed, and it is one statement from live.** The clause says "after that account's closing statement"; the invariant reports a trade whose pinned statement records the account closed. These diverge for a trade placed after a closure and after a later reopening, and the fixture already carries a reopened account.

Failure class: a sufficiency claim not checkable against the clause text. Rejected element ids: `sg.placement-moment` (coverage_claim). Corrections in `change-contract-20.md`.

## On the cheap screen

Contract scope 0.10 at high confidence was correct. The one score that looked like a signal was a trap, and the reviewer named why: an invariant carrying `reports: true` is supposed to add no decision, so a correctly built one scores near the floor. The scale inverts for that class. Recorded in the calibration evidence before the mechanism is used again.
