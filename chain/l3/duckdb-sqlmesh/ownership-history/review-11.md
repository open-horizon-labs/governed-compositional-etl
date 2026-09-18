# Review 11 (capable-model projection review): ownership-history on duckdb-sqlmesh

Authority: `chain/l2/ownership-history/selected-model.json` (`model_sha256`
91da9864…8de8c6, matching `chain/l2/ownership-history/review.json`), restricted to
the 61 ids in that review's `selected_element_ids`.

This review was performed against BOTH engine targets side by side, as instructed;
the native half is `chain/l3/duckdb-native/ownership-history/review-9.md`. Read in
full: `models/account.sql`, `models/customer.sql`, all 20 audits, `manifest.json`,
the native counterparts of all of the above, `chain/anchors/sources-v1.json`,
`chain/profiles/duckdb-sqlmesh.json`,
`chain/ce/accepted/ce.l1.deletion-withdraws.md`,
`chain/ce/accepted/ce.l1.withdrawal-reaches-standing.md`, and the model text of
every invariant named below. Prior reviews read: sqlmesh `review-9.md`,
`review-10.md`, native `review-7.md`, `review-8.md`.

Ran `check`, `run`, `twophase` for `duckdb-sqlmesh ownership-history`, and
`compare duckdb-native ownership-history --against duckdb-sqlmesh`. All green:
`check` status `question` with the two expected questions and no problems; `run` ok,
SQLMesh reporting 6 audits passed on `governed.customer` and 14 on
`governed.account`, 0 errors, 0 skipped; `twophase` both phases ok; `compare`
identical on both tables.

**None of that is evidence about anything in this review**, for the reason the
brief states: every producing branch hardcodes `FALSE AS is_withdrawal`, so the
whole withdrawal surface — which is all this rework touches — is dead code today,
and SQLMesh's twenty green checkmarks are twenty checks run against a population
containing no withdrawal. Every judgment below rests on the SQL text and on
populations I built by hand in a scratch DuckDB, against which I executed the
Developer's model SQL and audit files unmodified (only the `MODEL(...)`/`AUDIT(...)`
headers stripped and `@this_model` resolved). The single edit to their SQL was the
one the deferred handoff itself would make: admitting one extra `action_type` so
`is_withdrawal` can be true. Every window, partition and predicate is byte-identical
to what is on disk. Cases S1–S5 are defined identically in the native review and
were run against both engines from one fixture.

## Question 1 — do the two engines implement the same rule the same way? Yes.

The brief describes native as "a running count" and this target as a windowed
`SUM`. That is not what is on disk: both are the same windowed `SUM`, textually
identical modulo whitespace, in all four model files —

    SUM(CASE WHEN is_withdrawal THEN 1 ELSE 0 END) OVER (
      PARTITION BY <identity> ORDER BY effective_from
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)

— so the three sub-questions answer themselves, and I confirmed each by execution
rather than by reading. The frame includes `CURRENT ROW`, so a withdrawal counts
itself and is the **first row of the new group**, never the last of the old
(measured on S2: the 2014 withdrawal shares group 1 with the 2016 `CLOSEACCT`). A
first row of an identity gets 0, or 1 if it is itself a withdrawal, and never NULL.
Ties are nondeterministic on both engines by the same code — F2.

Executed side by side over the full S1–S5 population, the two engines produced
byte-identical `governed.customer` and `governed.account`, including every
withdrawal row, every post-withdrawal row and the tie. **On the withdrawal surface
the two models agree.** The divergences I found are in the audits (S1, S2 below)
and in one non-withdrawal carry-forward path (F4).

## S1 — BLOCKING. `inv.customer_withdrawal_with_standing_accounts_reported` still carries the date comparison L2 reviews 15 and 16 rejected. It cannot report the ordinary case.

This audit's withdrawn-owner arm reads:

    FROM @this_model AS a
    JOIN customer_withdrawals AS cw ON cw.customer_number = a.owning_customer_number
    WHERE a.is_withdrawal = FALSE
      AND a.effective_from >= cw.withdrawal_effective_from

That last predicate is the exact form `chain/l2/ownership-history/review.json`
records two L2 rounds rejecting: "it compared the customer's withdrawal to the
account statement's own `effective_from`, which can never fire because a withdrawal
creates no account statement and the account's real statements all predate it". The
native target fixed it — its join is on the customer alone, existence-only, with no
date comparison. This target did not.

Measured on S5 — customer 800 withdrawn 2020-01-01, account 910 owned by 800 whose
only statements are `NEW` 2010 and `UPDACCT` 2012, which is the *normal* shape
since a withdrawal creates no account statement:

- native returns `('withdrawn_owner_with_standing_account', 910, 800, 2020-01-01, NULL)`
- sqlmesh returns **nothing for account 910**

Account 910 is precisely "an account that would otherwise carry a standing at or
after the withdrawal's effective moment": it is unwithdrawn, so absent the owner
cascade its standing continues indefinitely and therefore reaches 2020. The model's
own `review_trigger` for this invariant fires verbatim — "a withdrawn customer's
account that carries a standing at or after the withdrawal is found not reported".

The audit does return a row for S2's account 900, and that is what makes this
dangerous rather than obvious: 900 fires only because it happens to have a
`CLOSEACCT` dated 2016, after its owner's 2015 withdrawal. That is an accident of
that account's history, not the rule. An account whose last statement predates its
owner's withdrawal — the overwhelmingly common case, and the only case the clause
was written for — is silently dropped. The arm reads as a working check and is
almost entirely dead.

`L1.deletion-withdraws` reports this "because a customer that still owns accounts is
one the brokerage may not have meant to withdraw". Under this implementation the
brokerage is not told about the accounts it most needs to be told about, and the
audit is declared `blocking false`, so nothing else catches it. This alone fails the
target.

## S2 — Finding. The same audit's two unevaluable arms report per statement, not per account.

Both unevaluable arms run over `@this_model` directly, so an account is reported
once for every non-withdrawal statement it has. Measured on S4: account 903 is
returned **three times** with the identical
`"unevaluable: owning customer's is_withdrawal could not be resolved"` finding, once
per statement. Native returns it once, because both its arms read
`account_own_standing` — the account's own latest, non-self-withdrawn statement.

The model says "that account is itself reported as unevaluable for this check,
naming the account and which input could not be resolved". One account, one report.
Native's arm-1 re-sourcing in this same rework was made for exactly this reason and
this target did not follow it, so the two engines now report different row counts
and different populations for the same invariant on the same data — a divergence
`compare` cannot see, since it compares tables and not audit output.

Not on its own blocking (the account does get reported, noisily), but it is a real
behavioural difference in a `reports: true` invariant whose output goes to the
business, and it should be fixed with S1.

## Question 3 — the tautological withdrawal arm. Unreachable as claimed, and the other two arms do fire. Accepted.

`inv.account_asof_carries_customer_asof` now has
`NOT aw.owner_withdrawn_by_t` in its precondition while retaining
`aw.owner_withdrawn_by_t` as an assertion disjunct. I verified unreachability rather
than accepting the file's own statement of it:

`owner_withdrawn_by_t` is `aa.owner_at_t IS NOT NULL AND EXISTS (...)`, an `AND` of
a non-nullable `IS NOT NULL` test and an `EXISTS` — **never NULL**, always exactly
TRUE or FALSE. So the `WHERE` is `NOT X AND (… OR X OR …)` with X two-valued, and
the disjunct contributes nothing under any data whatsoever. This is a proof, not a
belief, and it does not rely on the fixture. The file states the consequence
plainly and in the right place; I have no complaint about the honesty of it.

The question that mattered is whether the audit became wholly vacuous. It did not.
I built a case for each remaining arm and both fire substantively:

- **owner-not-yet-existing arm** (`NOT EXISTS (… c.effective_from <= aw.t)`): fires on S4, returning `(903, 2005-01-01)` — account 903's owner 702 has no statement in `governed.customer` at all. Identical row on native.
- **null-owner arm** (`aw.owner_at_t IS NULL`): this one needed construction, because every null owner the carry-forward boundary produces sits behind a withdrawal, and `NOT account_withdrawn_by_t` excludes it — S3's account 902 does *not* reach this arm. It is still reachable without any withdrawal: account 920, a `NEW` 2010 and `UPDACCT` 2012 whose `c_id` is NULL. Measured, the arm returns both statements, `(920, 2010-01-01)` and `(920, 2012-01-01)`.

So two of three arms are live and one is provably dead by design and says so. That
is a narrower audit than its name suggests but not a vacuous one, and the
precondition change is correct: it stops the audit asserting an as-of answer exists
at a T where `inv.account_asof_has_unique_answer` says it does not. Accepted.

One caveat I want on the record for whoever reads this next: the file's consequence
note says the audit "checks the null-owner case and the owner-not-yet-existing case
substantively". That is true only in the sense I demonstrated above — the null-owner
arm is reachable solely through a null `c_id` in the source, never through any null
owner the withdrawal machinery creates. The sentence is not wrong; it is thinner
than it reads. Not a defect.

## The tiebreak added to `inv.account_single_current`. Correct, and correctly reasoned — but added in the wrong place first.

The explicit `ORDER BY effective_from DESC, owning_customer_number DESC NULLS LAST, …`
does what its comment says, and the comment's argument for why it is not blocking
(a tie independently violates `inv.account_statements_no_overlap` and
`inv.account_asof_has_unique_answer`, so no tied data reaches acceptance) is sound —
I confirmed both fire on S4 on both engines. The audit itself returns zero rows
across S1–S5, correctly accepting "none current" for every withdrawn and
owner-withdrawn account and "exactly one" for the rest. Accepted.

But see F2. The identical unbroken tie sits in the `withdrawal_group` window that
actually computes the carry-forward boundary, in this same rework, and was not given
a tiebreak. The hazard was fixed where it was noticed, not where it lives.

## The rewritten carried-versus-suppressed join comment. Correct.

The claim is that using `owning_customer_number_carried` rather than the suppressed
output column in the `customer_withdrawn` join is not load-bearing. It holds: for a
non-withdrawal row the two are identical by construction, and for a withdrawal row
branch 1 (`WHEN f.is_withdrawal THEN FALSE`) short-circuits before `cw` is consulted.
Verified on S2, S3 and S4 — every withdrawal row is `is_current` false regardless.
Accepted.

## F1 — BLOCKING, shared with the native target. The carry-forward boundary contradicts five selected must-hold invariants.

Stated in full in the native review; identical here, same rows, same cause. In
summary: `withdrawal_group` stops `owning_customer_number`, `tax_treatment` and
`tier` being carried across a withdrawal, while the model text for
`inv.account_tax_treatment_matches_producing_source`,
`inv.customer_tier_matches_producing_source` and
`inv.account_owner_matches_producing_source` says each equals "the value carried by
the … immediately preceding statement", with no withdrawal boundary — and the first
two carry no withdrawal exception at all. Running the on-disk audit files unmodified
against S1–S3 on this target:

| audit | row returned | model gives | audit expects |
|---|---|---|---|
| `inv.account_statement_has_content` | `(900, 2016-01-01)` | `tax_treatment` NULL, `is_withdrawal` false | non-null |
| `inv.account_tax_treatment_matches_producing_source` | `(900, 2016-01-01)` | NULL | 2 (carried) |
| `inv.customer_statement_has_content` | `(700, 2018-01-01)` | `tier` NULL, `is_withdrawal` false | non-null |
| `inv.customer_tier_matches_producing_source` | `(700, 2018-01-01)` | NULL | 1 (carried) |
| `inv.account_owner_matches_producing_source` | `(902, 2013-01-01)` | owner NULL | 701 (carried) |

Five must-hold audits fail on the very population this rework exists to serve, and
SQLMesh would fail the model, not warn: none of these five is declared
`blocking false`.

Question 2's "does it overreach" is answered yes. `L1.hole.deletion-reversal`
forbids treating a post-withdrawal report as *resuming the record* — a statement
about currency, which `is_current`'s reversal-foreclosure branch already implements
completely and correctly (measured: S2's 2016 row and S3's 2013 row are both
`is_current` false). This rework extends an **open** hole from currency to content,
on reasoning stated in the file's own `withdrawal_group` comment, and the result is
`is_withdrawal = false` statements carrying no content at all — which
`L1.statement-content` calls an empty shell and two selected invariants call a
violation. `L1.deletion-withdraws` says a withdrawal erases nothing and every
statement before it stands; the pre-withdrawal statements are indeed untouched
(verified on S2 and S3), but the clause is being read as licence to blank facts that
stand.

The file comments assert the opposite of what executing them shows.
`models/account.sql` says the boundary exists so the derivation "must agree with
inv.account_statement_has_content's own withdrawal-direction assertion"; that audit
is one of the five that fail. `models/customer.sql` makes the same claim about
`inv.customer_statement_has_content`; it also fails.

I verified the alternative: with `withdrawal_group` removed from the four partition
clauses and nothing else changed, all five failures disappear and no
withdrawal-direction assertion begins to fail — the per-row
`CASE WHEN is_withdrawal THEN NULL` suppression already satisfies every one of them
on its own. F1 belongs at L2 as a question about whether
`L1.hole.deletion-reversal` reaches content, not back to the Developer as a patch: a
Developer told to make the audits pass will repartition the five audits and thereby
answer an open hole in SQL.

## F2 — Non-blocking. `withdrawal_group` is nondeterministic under tied `effective_from`.

`ORDER BY effective_from` with a `ROWS` frame and no tiebreak: among peers the frame
boundary follows physical row order. I enumerated all 24 physical orderings of S4's
four rows against the exact window text this target uses and got **two distinct
group assignments** — the tied 2007 `UPDACCT` lands in group 0 in some orders and
group 1 in others, keeping or losing its owner and tax accordingly. The same
nondeterminism reaches `LAST_VALUE(... IGNORE NULLS)`.

Non-blocking for the reason this target's own `inv.account_single_current` comment
gives about `ROW_NUMBER()`, and I confirmed the two invariants it names fire on S4.
Recorded because the reasoning was applied to the audit and not to the computation.

## F4 — Cross-engine divergence `compare` cannot see, in a non-withdrawal path. This target is the correct one.

`models/account.sql`'s `from_actions` takes
`CASE WHEN action_type IN ('NEW','ADDACCT','UPDACCT') THEN ca_tax_st ELSE NULL END`;
`native/account.sql` takes `ca_tax_st` unconditionally. Nothing enforces that a
`CLOSEACCT` row's `ca_tax_st` is NULL in the data. Measured on account 930 (`NEW`
2010 tax 2, `CLOSEACCT` 2012 carrying tax 9): sqlmesh gives the 2012 statement
tax 2, native gives 9. `compare` is blind because today's fixture carries NULL
there, and neither `inv.account_tax_treatment_matches_producing_source` catches it
because each engine's `expected` CTE mirrors its own model's shape — this one
reproduces this model's `CASE`, native's reads `ca_tax_st` unconditionally. Two
mirrors, no check.

The model text decides it for this target: the direct suppliers are enumerated as
"a historical action's `ca_tax_st` on NEW, ADDACCT, or UPDACCT", so a `CLOSEACCT`'s
value is not a direct supplier and must be carried forward. **This target is
right**; the finding is against native. Predates this rework; reported because it is
exactly the class of divergence the brief says only side-by-side reading finds.

## What I checked and found clean

- Every audit, comment, `necessity` and header mentioning carry-forward, `is_withdrawal` or the owner cascade, per instruction 5. Beyond F1, S1 and S2, the remaining prose matches the SQL as written; in particular the `depends_on (governed.customer)` declaration, the `blocking false` declaration on the reporting audit, and the existence-versus-as-of-now caveat in the owner-cascade comment are all accurate.
- `is_current`'s three branches measured rather than read: own-withdrawal (S2's 2014 row false), reversal-foreclosure (S2's 2016 and S3's 2013 rows false), owner cascade (S5's account 910 — both statements false from customer 800's withdrawal alone). The model's owner cascade uses the existence form and fires correctly; the defect in S1 is in the *audit*, not in `is_current`.
- `inv.account_statements_no_overlap`, `inv.account_asof_has_unique_answer`, `inv.customer_single_current`, `inv.customer_asof_has_unique_answer`, `inv.constructed_account_change_refers_to_known_account`, `inv.constructed_scenarios_labeled`, `inv.customer_status_matches_producing_source` and `inv.withdrawal_never_reaches_account_status` all behave correctly across S1–S5.
- The `check` containment question about `models/account.sql` reading `governed.customer` is the expected declared sibling read.

## Verdict and what would have changed my mind

Two independent blocking findings, either of which is sufficient: **S1**, which is
this target's alone and is a recurrence of the exact defect L2 rejected twice, and
**F1**, which it shares with native.

I would have passed S1 if the withdrawn-owner arm had joined on the customer alone,
as native's does, and I confirmed that form reports account 910 correctly. I would
have passed F1 if the five audits had been repartitioned on
`(identity, withdrawal_group)` **and** the three model statements had carried a
withdrawal-boundary clause authorizing it, or if the boundary had been left out
entirely. Neither holds.

I explicitly did **not** reject on the three items the brief flagged for hardest
scrutiny on this target — the tautological arm, the `ROW_NUMBER()` tiebreak and the
rewritten join comment. All three are correct, and the tautology is genuinely
unreachable rather than merely believed to be, by a proof that does not depend on
the fixture. The two live arms of that audit fire substantively, demonstrated on
accounts 903 and 920.

**I do not think more evidence is needed before deciding.** Both blocking findings
reproduce by executing on-disk files against fixtures of three and four rows.

I have stamped nothing, and have edited no `.sql`, `manifest.json`, or
`review.json`. The only file I wrote on this target is this review.

VERDICT: fail
