# Review 9 (capable-model projection review): ownership-history on duckdb-native

Authority: `chain/l2/ownership-history/selected-model.json` (`model_sha256`
91da9864…8de8c6, matching `chain/l2/ownership-history/review.json`), restricted to
the 61 ids in that review's `selected_element_ids`.

This review was performed against BOTH engine targets side by side, as instructed;
the sqlmesh half is `chain/l3/duckdb-sqlmesh/ownership-history/review-11.md`. Read
in full: `account.sql`, `customer.sql`, all 20 audits, `manifest.json`, the sqlmesh
counterparts of all of the above, `chain/anchors/sources-v1.json`,
`chain/profiles/duckdb-native.json`, `chain/ce/accepted/ce.l1.deletion-withdraws.md`,
`chain/ce/accepted/ce.l1.withdrawal-reaches-standing.md`, and the model text of
every invariant named below. Prior reviews read: native `review-7.md`,
`review-8.md`, sqlmesh `review-9.md`, `review-10.md`.

Ran `check`, `run`, `mutate`, `twophase` for `duckdb-native ownership-history`, and
`compare duckdb-native ownership-history --against duckdb-sqlmesh`. All green:
`check` status `question` with the two expected questions (moved groups; the
declared sibling read of `governed.customer`) and no problems; `run` ok with no
findings; `mutate` reports every protected role protected; `twophase` both phases
ok; `compare` identical on both tables.

**None of that is evidence about anything in this review.** Every producing branch
hardcodes `FALSE AS is_withdrawal`, so every withdrawal CTE in this job is an empty
relation and the entire withdrawal surface — which is all this rework touches — is
dead code under today's fixture. Accordingly every judgment below rests on the SQL
text and on populations I built by hand in a scratch DuckDB, against which I
executed the Developers' model SQL and audit files unmodified. The only edit made
to their SQL was the edit the deferred handoff itself would make: admitting one
extra `action_type` so that `is_withdrawal` can actually be true. Every window,
every partition, every audit is byte-identical to what is on disk. The hand-built
cases are named S1–S5 below.

Hand-built population (single `raw.customer_mgmt_action` + `ce.account_changes`
fixture, all cases present at once):

- **S1** customer 700: `NEW` 2010 (tier 1), withdrawal 2015, `INACT` 2018 (omits `c_tier`).
- **S2** account 900 (owner 700): `NEW` 2010 (tax 2), `ADDACCT` 2011, own withdrawal 2014, `CLOSEACCT` 2016 (omits `ca_tax_st`).
- **S3** account 902 (owner 701): `NEW` 2009 (tax 3), own withdrawal 2011, then a labeled `ce.account_changes` row at 2013 carrying no owner of its own.
- **S4** account 903: `ADDACCT` 2005, `UPDACCT` 2007 **and** a withdrawal at the same instant 2007, `CLOSEACCT` 2009 — the tie case.
- **S5** customer 800 withdrawn 2020; account 910 owned by 800 whose only statements are `NEW` 2010 and `UPDACCT` 2012, i.e. every statement predates the owner's withdrawal. This is the *normal* shape, not an exotic one: a withdrawal creates no account statement.

## Question 1 — do the two engines implement the same rule the same way? Yes.

I compared the two `withdrawal_group` implementations directly. The brief describes
native as "a running count" and sqlmesh as a windowed `SUM`; that is not what is on
disk. Both are the same windowed `SUM`, textually identical modulo whitespace:

    SUM(CASE WHEN is_withdrawal THEN 1 ELSE 0 END) OVER (
      PARTITION BY <identity> ORDER BY effective_from
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)

in all four files (`account.sql` and `customer.sql` on each engine). So the three
sub-questions answer themselves and I confirmed each by execution:

- **The group a withdrawal row itself belongs to.** The frame includes `CURRENT ROW`, so a withdrawal counts itself: it is the first row of the new group, never the last of the old. Same on both. Measured on S2: the 2014 withdrawal and the 2016 `CLOSEACCT` share group 1; the 2010 and 2011 statements are group 0.
- **The first row of an identity.** `UNBOUNDED PRECEDING` with no preceding rows gives 0 for an ordinary first row and 1 for a first row that is itself a withdrawal. Same on both, and never NULL — `SUM` over a non-empty frame of a `CASE` that returns 0, not NULL.
- **Ties in `effective_from`.** See F2. Both engines are equally nondeterministic here, by the same code, so they agree on the rule and can still disagree with each other run to run.

Executed side by side over the full S1–S5 population, the two engines produced
byte-identical `governed.customer` and `governed.account`, including every
withdrawal row, every post-withdrawal row and the tie. On the withdrawal surface the
two models agree. The divergences I found are in the **audits** (see the sqlmesh
review's S1) and in one non-withdrawal carry-forward path (F4).

## F1 — BLOCKING. The carry-forward boundary contradicts three selected must-hold invariants, whose SQL was not updated with it.

This is the defect. It is present on both engines, it is the direct and sole
consequence of the change under review, and it is the same "rework fixed its defect
and broke the thing asserting the old shape" pattern the brief warned about.

`withdrawal_group` stops `owning_customer_number` and `tax_treatment` (and `tier`
on the customer side) from being carried across a withdrawal. Three selected
must-hold invariants say, in the model's own words, that they must be. None of
their audit SQL was repartitioned to match, and none of them can be, because the
model text is what they check:

- `inv.account_tax_treatment_matches_producing_source`: "for one whose producing historical action omits it (CLOSEACCT), `tax_treatment` equals the value carried by the account's **immediately preceding statement**". No withdrawal boundary, and unlike its sibling invariants, **no withdrawal exception at all**.
- `inv.customer_tier_matches_producing_source`: same sentence for `tier`/`INACT`. No boundary, no withdrawal exception.
- `inv.account_owner_matches_producing_source`: "for one produced by a constructed scenario row … equals the value carried by the account's immediately preceding statement". Has a withdrawal exception, but only for a withdrawal statement itself, not for a statement after one.
- `inv.account_statement_has_content` / `inv.customer_statement_has_content`: every non-withdrawal statement "carries a non-null status and a non-null tax_treatment" / "tier".

Measured, running the on-disk audit files unmodified against S1–S3 (identical rows
on the sqlmesh target):

| audit | row returned | model gives | audit expects |
|---|---|---|---|
| `inv.account_statement_has_content` | `(900, 2016-01-01)` | `tax_treatment` NULL, `is_withdrawal` false | non-null |
| `inv.account_tax_treatment_matches_producing_source` | `(900, 2016-01-01)` | NULL | 2 (carried) |
| `inv.customer_statement_has_content` | `(700, 2018-01-01)` | `tier` NULL, `is_withdrawal` false | non-null |
| `inv.customer_tier_matches_producing_source` | `(700, 2018-01-01)` | NULL | 1 (carried) |
| `inv.account_owner_matches_producing_source` | `(902, 2013-01-01)` | owner NULL | 701 (carried) |

Five must-hold audits fail, on the very population this rework exists to serve. A
green `run` today hides all five behind `FALSE AS is_withdrawal`.

This is not a bug in the audits that L3 may fix by editing them. **Question 2's
"does it overreach" is answered yes**, and the overreach is a governing-boundary
crossing, not a coding slip:

- `L1.deletion-withdraws` says a withdrawal erases nothing and every statement before it stands exactly as it stood. The boundary honours that — group 0 rows are untouched, confirmed on S2 (900's 2010 and 2011 statements keep owner 700 and tax 2) and S3 (902's 2009 statement keeps owner 701 and tax 3). That half is right.
- `L1.hole.deletion-reversal` forbids treating a post-withdrawal report as **resuming the record**. That is a statement about currency and existence. `is_current`'s reversal-foreclosure branch already implements it, correctly and completely: measured on S2, the 2016 `CLOSEACCT` is `is_current` false, and on S3 the 2013 constructed statement is `is_current` false. The record does not resume.
- The rework then extends the open hole's instruction from currency to **content**, on the reasoning stated in `account.sql`'s "Carry-forward boundary" note ("applied to content rather than currency"). The hole is open. L3 does not get to decide it, and this decision is not a free one: it produces `is_withdrawal = false` statements that carry no content at all, which `L1.statement-content` calls an empty shell and two selected invariants call a violation.

So the boundary suppresses exactly what the brief asked me to check for: facts the
clause requires to stand. The correct disposition is an L2 question, not an L3
choice. Either the three invariants gain a withdrawal-boundary clause (an L2 change
to selected must-holds, which needs the hole answered), or the boundary comes out
and the per-row `CASE WHEN is_withdrawal THEN NULL` suppression stands alone — it
already fully satisfies every withdrawal-direction assertion in every audit, and I
verified that it does: with `withdrawal_group` removed from the four partition
clauses and nothing else changed, all five failures above disappear and no
withdrawal-direction assertion begins to fail.

I note that both Developers' own file comments assert the opposite of what I
measured. `account.sql` says the boundary is "wired so the derivation and the
withdrawal-direction audits (`inv.account_statement_has_content`,
`inv.account_owner_matches_producing_source`) agree structurally rather than by
coincidence once `raw.account_cdc` is undeferred". Those are two of the five audits
that fail. `customer.sql` makes the identical claim about
`inv.customer_statement_has_content`, which also fails. The claim was never
executed against a withdrawal population; it is wrong in the specific direction the
comment guarantees.

## F2 — Non-blocking finding. `withdrawal_group` is nondeterministic under tied `effective_from`.

`ORDER BY effective_from` with a `ROWS` frame and no tiebreak: among peers the
frame boundary follows physical row order, which DuckDB does not fix. I enumerated
all 24 physical orderings of S4's four rows against the exact window text both
engines use and got **two distinct group assignments**: the tied 2007 `UPDACCT`
lands in group 0 in some orders and group 1 in others. In group 0 it keeps owner 702
and tax 5; in group 1 it loses both. The same nondeterminism reaches
`LAST_VALUE(... IGNORE NULLS)` directly.

Not blocking, for the reason sqlmesh's own `inv.account_single_current` comment
gives about its `ROW_NUMBER()`: a tie independently violates
`inv.account_statements_no_overlap` and `inv.account_asof_has_unique_answer`, so no
tied data reaches acceptance. I confirmed both fire on S4 on both engines. But I
record it because the reasoning was applied asymmetrically: sqlmesh added an
explicit tiebreak to an *audit's* `ROW_NUMBER()` in this very rework while leaving
the identical unbroken tie in the window that actually computes the boundary, and
native has no tiebreak in either place. The hazard was fixed where it was noticed,
not where it lives.

## F3 — Stale comment falsified by the rework it shipped with, and a false report to the business.

`audits/inv.customer_withdrawal_with_standing_accounts_reported.sql`, unevaluable
arm 1, says:

> governed.account only ever leaves `owning_customer_number` null for a withdrawal
> statement of the account itself (see account.sql), which asserts no standing to
> lose in the first place, so this branch is currently vacuous but is checked
> directly rather than assumed.

That was true before this rework and is false after it. The carry-forward boundary
creates a second way for `owning_customer_number` to be null: a statement *after* a
withdrawal whose producing row carries no owner. Measured on S3 — account 902's
2013 constructed statement has `is_withdrawal = false` and `owning_customer_number`
NULL, and arm 1 **fires on it**, returning
`('unresolvable_owner', 902, NULL, NULL, 'owning_customer_number')`.

The substantive half matters more than the stale sentence. That account's owner is
not unresolvable. It is 701, stated plainly by the account's own 2009 `NEW`
statement, which `L1.deletion-withdraws` says stands exactly as it stood. The
boundary erases it from the projection, and this audit then reports a resolvable
input to the business as unevaluable. Per the model's statement for this invariant,
an unevaluable report is for an input that "cannot be resolved (for example because
the handoff that would supply it is still deferred)". This one can. It is a false
finding handed to the business under `reports: true`, which is worse than a silent
pass because it will be acted on.

This resolves with F1: fix the boundary and this report disappears. The comment
must be corrected either way.

## Question 4 — native's arm 1 re-sourcing. Correct. Verified.

Sourcing unevaluable arm 1 from `account_own_standing` rather than
`governed.account` is right, and I verified the three properties asked for against
S1–S5 rather than reading for them:

- **Both unevaluable arms reachable.** Arm 1 fires on S3 (account 902). Arm 2 fires on S4 (account 903, whose owner 702 has no statement in `governed.customer` at all). Neither is vacuous.
- **Disjoint.** Arm 1 requires `s.owning_customer_number IS NULL`, arm 2 requires `s.owning_customer_number IS NOT NULL`. Complementary on the same relation, so disjoint by construction, and no account appeared under both in the measured output.
- **Same population, as the file's own comment now claims.** Both arms now read `account_own_standing`, so an account whose own record has already ended is excluded from both, exactly as it is from the withdrawn-owner branch.
- **The ordinary case still reports.** S2's account 900 and S5's account 910 both return `withdrawn_owner_with_standing_account` rows naming the account, the withdrawn customer and the withdrawal moment.

S5 is worth stating explicitly, because it is where this engine is right and the
other is wrong: native joins `account_own_standing` to `withdrawn_customers` on the
customer alone, with no date comparison, so account 910 is reported even though
every one of its statements predates the 2020 withdrawal. That is the existence
form L2 review-17 confirmed, and it is what makes the branch fire at all. The
sqlmesh target still carries the date comparison and does not report 910 — see that
review's S1.

## F4 — Cross-engine divergence `compare` cannot see, in a path that has nothing to do with withdrawals.

Found only by reading the two files side by side. `native/account.sql`'s
`historical` CTE takes `ca_tax_st AS tax_treatment` unconditionally.
`sqlmesh/models/account.sql`'s `from_actions` takes
`CASE WHEN action_type IN ('NEW','ADDACCT','UPDACCT') THEN ca_tax_st ELSE NULL END`.
The anchor says `CLOSEACCT` omits `ca_tax_st`, but nothing in either projection and
no audit enforces that it is NULL in the data.

Measured: account 930, `NEW` 2010 with `ca_tax_st` 2, `CLOSEACCT` 2012 with
`ca_tax_st` 9. Native returns `tax_treatment` = 9 for the 2012 statement; sqlmesh
returns 2. `compare` is blind to it because today's fixture happens to carry NULL
on `CLOSEACCT`, and neither engine's
`inv.account_tax_treatment_matches_producing_source` catches it because each one's
`expected` CTE mirrors its own model's shape rather than the model text
independently — native's reads `ca_tax_st` unconditionally, sqlmesh's reproduces
sqlmesh's `CASE`. Two mirrors, no check.

The model text decides it: `tax_treatment` equals the producing row's value "where
supplied directly", and the enumeration of direct suppliers is "a historical
action's `ca_tax_st` on NEW, ADDACCT, or UPDACCT". A `CLOSEACCT`'s `ca_tax_st` is
not a direct supplier under that sentence, so sqlmesh is right and native is wrong
here. Predates this rework; reported because it is exactly the class of divergence
the brief says only side-by-side reading finds, and because it is one anomalous
source row away from being live.

## What I checked and found clean

- Every audit, comment, `necessity` and header that mentions carry-forward, `is_withdrawal` or the owner cascade, per instruction 5. Beyond F1 and F3, the remaining `is_withdrawal` prose in `account.sql`, `customer.sql` and the 20 audits matches the SQL as written.
- `is_current`'s three branches, measured rather than read: own-withdrawal (S2's 2014 row false), reversal-foreclosure (S2's 2016 row false, S3's 2013 row false), owner cascade (S5's account 910 — both its statements false, driven by customer 800's withdrawal alone). The existence form fires; the date form L2 rejected would not have.
- `inv.account_single_current` returns zero rows across S1–S5, correctly accepting "none current" for every withdrawn or owner-withdrawn account and "exactly one" for the rest.
- `mutate` reports every protected role protected; I re-read the swap/null results rather than taking the summary line.
- The `check` containment question about `account.sql` reading `governed.customer` is the expected declared sibling read, and the derivation's rule text states it in full.

## Verdict and what would have changed my mind

I would have passed this if the five audits in F1 had been repartitioned on
`(identity, withdrawal_group)` **and** the three model statements had carried a
withdrawal-boundary clause to authorize that. They have neither. I would also have
passed if the boundary had been left out and the per-row suppression left to stand
alone — I verified that configuration satisfies every withdrawal-direction
assertion in the projection.

What I am rejecting is not the idea. It is that an open hole was answered at L3, in
a direction that makes five selected must-holds fail, and that the file comments
assert the opposite of what executing them shows.

**I do not think more evidence is needed before deciding.** The five failures are
reproducible by executing the on-disk audit files against a three-row fixture, and
they are identical on both engines. F1 should go back to L2 as a question about
whether `L1.hole.deletion-reversal` reaches content, not back to the Developer as a
patch — a Developer told to make the audits pass will repartition the five audits
and thereby quietly answer the hole in SQL, which is the outcome this chain exists
to prevent.

I have stamped nothing, and have edited no `.sql`, `manifest.json`, or
`review.json`. The only file I wrote on this target is this review.

VERDICT: fail
