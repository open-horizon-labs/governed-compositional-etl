# Review 7 (capable-model projection review): ownership-history on duckdb-native

Authority: `chain/l2/ownership-history/selected-model.json` (`model_sha256`
91da9864…8de8c6, matches `chain/l2/ownership-history/review.json`), restricted to the
61 ids in that review's `selected_element_ids`. Read in full: `account.sql`,
`customer.sql`, `manifest.json`, all 20 audits, `chain/anchors/DEVELOPER-CONTRACT-L2-L3.md`,
`chain/profiles/duckdb-native.json`, `counterexamples/proposed/ce-withdrawn-account-v1.json`.
Ran `check`, `run`, `mutate`, `twophase`, and `simulate --ce
counterexamples/proposed/ce-withdrawn-account-v1.json`.

Because this job cannot observe a withdrawal — it reads only
`raw.customer_mgmt_action`, and all seven CDC handoffs stay deferred under
`L1.hole.change-effective-time` — every zero in `run` is consistent with the
withdrawal rules being right and equally consistent with their being wrong. So
each withdrawal-path judgment below is a reading of the SQL, and where I could
not settle it by reading I built the missing population by hand in a scratch
DuckDB and ran the audit files unmodified against it. Two of those
hand-built populations produced wrong behavior. Both are audit-side, both are
latent for the same reason everything else here is latent, and both are the same
error the L2 had to reject twice: an owner relation keyed on the wrong thing.

## Q1 — the cross-entity branch in `logical.account.is_current`. Correct.

The branch is present, and it is the right form.

`account.sql` builds `customer_owner_withdrawals` as `SELECT DISTINCT
customer_number FROM governed.customer WHERE is_withdrawal` — the sibling entity's
own compiled table, not a re-derivation from `raw.customer_mgmt_action`, whose
`action_type` vocabulary cannot express a withdrawal and from which the branch
would therefore be dead on arrival. The branch then fires on

```sql
WHEN EXISTS (SELECT 1 FROM customer_owner_withdrawals cow
             WHERE cow.customer_number = a.owning_customer_number_carried) THEN FALSE
```

with no reference to `a.effective_from` anywhere inside it. That is existence, not
comparison. The two adjacent branches do compare dates (`a.is_withdrawal`, and
`aw.first_withdrawal_from <= a.effective_from` for reversal-foreclosure) and are
correct to, since both are about the account's own history; the owner branch sits
between them without inheriting their shape. The join key is
`owning_customer_number_carried` — this statement's own owner after carry-forward —
which is what the rule says ("this statement's own `owning_customer_number`'s
customer entity"), and the types match (`c_id` BIGINT on both sides).

It matches the `parallel_assumption`'s reasoning, and it matches the part of the
reasoning that is easy to lose. The assumption's argument is not merely "a
withdrawal creates no account statement" — that alone would only show the date
comparison is *usually* unable to fire. It is that `is_current` asks about
standing at an unbounded, ever-advancing present rather than at the statement's
own moment, so a withdrawal's date is irrelevant to the question; combined with
`L1.hole.owner-change-reversions-account` leaving open whether an owner-withdrawn
account is ever re-stated, the existence check is *the only mechanism that can
ever mark such an account not current*. The SQL's comment reproduces that
argument rather than just the conclusion, and names the condition under which it
must be revisited (a withdrawal dated later than the present at which "current"
is asked — unreachable today, since the only source supplying an `effective_from`
carries no withdrawal action and the withdrawal-capable sources supply no
`effective_from` and stay deferred).

I checked for the thing that would turn the asymmetry into a contradiction rather
than a distinction: an invariant asserting that `is_current` agrees with the as-of
answer at the present moment. There is none, in the selected set or the
projection. `inv.account_asof_carries_customer_asof` is the nearest, and it is
keyed on `T` (each statement's own `effective_from`), where a date comparison is
the *correct* form — an owner-withdrawn account's pre-withdrawal statements still
answer as-of questions dated before the withdrawal, which is what "earlier
statements and earlier as-of answers stand" requires. I confirmed by hand that
the two live together: an account whose owner is withdrawn in 2020 gets
`is_current` false on every statement while
`inv.account_asof_carries_customer_asof` stays at zero for its 2010 and 2015
statements, and fires only for a statement dated *after* the owner's withdrawal —
which would be a genuine half answer. The existence form and the date form are
each in the right place.

## Q2 — nullability. Correct in the SQL; the audit that the L2 *claims* covers the third fact does not, and that is the L2's gap, not this projection's.

Every null in the SQL is emitted by an explicit `CASE WHEN is_withdrawal THEN
NULL ELSE …`, and all three standing facts have one. The asymmetry the L2 carried
for two rounds is *not* inherited: `owning_customer_number` is nulled on
withdrawal exactly as `status` and `tax_treatment` are, in the same shape, in the
same SELECT (`account.sql`, final projection list). `customer.sql` does the same
for `status` and `tier`.

I traced the paths that could produce a null somewhere else:

- `status` (both entities): `CASE action_type WHEN … END` with no `ELSE`, but the
  producing `WHERE` restricts `action_type` to exactly the cases enumerated, so
  the CASE is total over its input. Not a null path.
- `tax_treatment` / `tier`: `COALESCE(direct, LAST_VALUE(… IGNORE NULLS) OVER …)`
  is NULL if the first statement of the identity omits the field. The model argues
  this is unreachable (`CLOSEACCT`/`INACT` presuppose an existing record), and if
  the argument ever failed, `inv.account_statement_has_content` /
  `inv.customer_statement_has_content` catch it directly. Protected.
- `owning_customer_number_carried`: NULL if a `ce.account_changes` row is an
  account's first statement. Blocked upstream by
  `inv.constructed_account_change_refers_to_known_account`, which is implemented
  with the strict `r.action_ts < cc.action_at` the carry-forward needs. Protected.
- `provenance` is nullable on a different license (a received record is not a
  constructed scenario), which the model states independently of `is_withdrawal`
  (`logical.account.provenance`, `nullable: true`, no withdrawal clause). Faithful.
- `COALESCE(status, NULL)` in `customer.sql`'s `carried` CTE is a no-op. Harmless,
  but it is the shape of a carry-forward with its second argument removed, sitting
  next to a real carry-forward on `tier`; a later reader may take it for one.
  Cosmetic, recorded as O1 below.

One thing worth stating precisely, because it looks like the inherited asymmetry
and is not. `logical.account.owning_customer_number`'s `note` says non-nullness on
a non-withdrawal statement is "checked by
`inv.account_owner_matches_producing_source`'s non-withdrawal branch". That
branch is `owning_customer_number IS DISTINCT FROM e.expected_owner`, and
`expected_owner` is recomputed by the same carry-forward from the same sources —
so in the one case where the projection could emit an unlicensed null (source
carry-forward finds nothing), expected is null too and the comparison agrees. The
audit is nonetheless a faithful implementation of the invariant's *statement*,
which is a value-equality requirement and says nothing about non-nullness; and
`mutate` confirms it is real protection rather than a tautology, because nulling
the persisted column while the expectation is recomputed from `raw`/`ce` does
fire it. The overclaim is in the L2 attribute note, not in this SQL. No defect
here; recorded as O2 so the next L2 cycle can tighten the note or the invariant.

## Q3 — zero current statements. The SQL is right. `inv.account_single_current` reports correct behavior as a violation. **F1.**

The SQL permits zero, on all three routes, and I checked each by hand rather than
by inspection alone:

- latest statement is the account's own withdrawal → that row false by branch 1,
  every earlier row false because the withdrawal holds `MAX(effective_from)`. Zero.
- withdrawal not latest (a report received after it) → the later row false by
  reversal-foreclosure, the withdrawal false by branch 1, earlier rows false by
  the MAX branch. Zero.
- owner withdrawn → every row false by the existence branch. Zero.
  `customer.sql` behaves the same way for the first two.

`inv.customer_single_current` and `inv.account_single_current` both allow zero
rather than requiring exactly one, and `inv.account_single_current` conditions its
zero-allowance on *existence* (`ow.customer_number IS NULL`), not on a date —
correctly refusing to repeat the rejected form. The review triggers in the model
are the strict ones ("an account whose own history or whose owner carries a
withdrawal has any statement flagged current, or an account with no withdrawal in
its own history and an owner with no withdrawal at all has zero or more than one
statement flagged current"), and the audit is written against them.

**F1 (defect).** `inv.account_single_current` resolves the account's owner with
`MAX(owning_customer_number)` aggregated over all of the account's statements.
That is not the account's owner; it is the numerically largest customer number
that has ever owned it. When an account's owner changes across its own statements
— which `UPDACCT` can express today, and which
`logical.account.is_current`'s `parallel_assumption` explicitly contemplates
("Assumes `owning_customer_number` is constant across an account's own statements
*unless a new account statement changes it*") — the audit checks the wrong
customer's withdrawal history. Concretely, with account 500 owned by customer 9
on its 2010 statement and by customer 5 on its 2015 statement, and customer 5
carrying a withdrawal:

- `account.sql` is correct: the 2015 row is false by the owner-existence branch,
  the 2010 row is false by the MAX branch. Zero current — which is exactly what
  `inv.account_single_current`'s own L2 statement requires, since the account's
  owning customer does not stand.
- The audit computes `MAX(9, 5) = 9`, finds no withdrawal for 9, and so treats
  `current_count = 0` as a violation. Ran against the audit file unmodified: it
  returns `[('500',)]`.

That is a must-hold audit failing on behavior the model demands — the same
failure mode as review-15 and review-16, where `inv.account_asof_carries_
customer_asof` fired as a must-hold failure for behavior nothing produced. Here
the direction is reversed (the projection is right and the audit is wrong) but the
cause is identical: the owner relation resolved per-account instead of
per-statement. `account.sql` already does it correctly, per statement, three
lines away; the audit should key the same way (or on the latest statement's
owner, which is what "its owning customer" means for a question about the
present). Note also the masking direction: with the owners reversed, the wrong
`MAX` can *disable* the zero-allowance and hide a genuine
all-statements-not-current bug.

Requires a withdrawal to fire, so it is unexercised today, exactly like the rule
it checks. That is the reason to judge it by reading, not a reason to discount it.

## Q4 — the `reports: true` invariant. Strict on its first branch; its second branch is not implemented. **F2.**

`inv.customer_withdrawal_with_standing_accounts_reported` is registered in the
manifest like any other audit, and the harness routes it correctly: `run` keeps
`ok` and lists nothing under `findings_for_the_business` (zero rows today, the
correct empty result of an unexercised condition), and `mutate` ignores it, so it
is contributing no false protection to the 20/0 result. Its rows would be
findings: each names `case_type`, the account, the withdrawn customer and the
withdrawal moment, which is what `L1.deletion-withdraws`' "reported for review"
asks for, and nothing about them would indicate a projection fault.

It is not weakened to keep the run quiet. The temptation was available and
declined: "would otherwise carry a standing at or after the withdrawal's
effective moment" could have been narrowed to a date comparison between the
account's last statement and the withdrawal, which would silence the population
the clause is actually about (an account whose last statement long predates its
owner's withdrawal). Instead it reads the phrase as "the account's own record has
not itself ended", states that reading in the comment, and reports regardless of
dates. It correctly excludes an account whose own latest statement is a
withdrawal (no standing to lose), and correctly keys on the latest statement's
owner so a former owner's withdrawal does not report an account it no longer owns.

**F2 (defect).** The invariant's statement has two unevaluable inputs: "When an
account's `owning_customer_number`, **or the `is_withdrawal` value of the customer
that `owning_customer_number` names**, cannot be resolved (for example because the
handoff that would supply it is still deferred), that account is itself reported
as unevaluable for this check, naming the account and which input could not be
resolved, rather than passed over as though the condition were false." The audit
implements only the first. Its `unresolvable_owner` branch is
`NOT is_withdrawal AND owning_customer_number IS NULL`, and its comment restates
the clause with the second input silently dropped ("When an account's
`owning_customer_number` cannot be resolved…"), so the narrowing is not disclosed
as a narrowing. An account whose `owning_customer_number` names a customer the
customer entity holds no statement for has an unresolvable owner `is_withdrawal`
and is passed over as though the condition were false. Ran by hand: account 700
owned by customer 77 with `governed.customer` empty of 77 returns `[]` from this
audit, while the must-hold `inv.account_asof_carries_customer_asof` fires.

That inverts the design. The L2's `necessity` says this case must be reported
"because both of its inputs can be genuinely unresolvable independently of each
other — the account-side and customer-side CDC handoffs are deferred separately
and need not be undeferred together", and the invariant's own `review_trigger`
names it ("an account whose `owning_customer_number` or owner `is_withdrawal` is
unresolvable is found neither reported as unevaluable nor excluded for a stated
reason"). In the undefer-one-before-the-other scenario the clause was written
for, the reviewer gets a must-hold break instead of a finding handed to the
business. It is also reachable without any CDC at all: a `c_id` appearing only on
account-subject actions (`ADDACCT`/`UPDACCT`/`CLOSEACCT`, which carry `c_id` but
produce no customer statement) and never on `NEW`/`UPDCUST`/`INACT` yields an
account whose owner the customer entity does not know. Today's fixture has a
single customer, 238, with a `NEW`, so it does not arise here.

## Q5 — the undeclared sibling dependency. Permitting it was right, and this is the legitimate case.

Permitting it was right, and the alternative was worse in both directions.
Containment is built from handoffs, and a handoff names a source or an upstream
job, never a sibling; the L2 schema has no element that can declare
`logical.account` depends on `logical.customer`. So a gate that refused the read
would have left a Developer three options: drop the branch (reinstating the defect
two L2 reviews found twice, and the exact failure
`DEVELOPER-CONTRACT-L2-L3.md`'s "The rule text governs" section was written to
prevent), invent a fake handoff to launder it (a lie in the model, which is worse
than a gap), or re-derive the owner's withdrawal from
`raw.customer_mgmt_action`, which cannot express a withdrawal — a branch that
compiles, passes, and is dead. Refusing correct SQL for want of a vocabulary item
is the gate being wrong about the model, not the model being wrong. Raising it as
a `question` rather than passing it silently is the right strength: the
dependency is real and is recorded nowhere in the model, so it should cost a
reviewer's attention every cycle until the schema can carry it. I would object if
it were downgraded to silence.

This projection's use of it is the legitimate case, on four counts. The read is of
`governed.customer`, an entity of *this same job*, compiled from the same selected
model, in the same review scope, by the same manifest — one unit, not a reach
across a governance boundary. It is the entity the rule names, and it is read for
the fact the rule names (`is_withdrawal`), not used as a back door to a source or
to re-derive something a declared handoff already supplies. There is no cycle:
`customer.sql` reads only `raw.customer_mgmt_action`, so the dependency is
one-directional. And the read is disclosed at the point of use — `account.sql`'s
header states it under `reads`, the manifest lists `governed.customer` in that
artifact's `reads`, and the comment explains why the label understates the rule and
why existence is the right form. That is the dependency being stated in prose
because the schema cannot state it structurally, which is the best available
outcome. I would have called it illegitimate had it been a sibling read used to
reach a table outside containment, a read of another job's entity without a
handoff, or an undisclosed one.

One fragility, not a defect: `account.sql`'s dependency on `customer.sql` having
run is satisfied only by the order of the `artifacts` array in `manifest.json`
(`execute()` in `scripts/chain_l3.py` runs them in list order). Reordering that
array would break the build. On this target it fails loudly with a missing table
rather than silently producing a wrong answer, so it is acceptable; recorded as O3.

## Q6 — `mutate`. Real protection, not a tautology.

`mutate` reports 20 mutations, `unprotected: []`. The two `is_withdrawal`-null
mutations the Developer closed are caught by the `is_withdrawal IS NULL` disjunct
added to `inv.account_statement_has_content` and
`inv.customer_statement_has_content`. That is real protection on three grounds.
It names a distinct wrong state rather than restating the mutation: a statement
whose withdrawal status is indeterminate, against an attribute the model declares
`nullable: false`, with a semantic type of its own (`type.statement_is_withdrawal`,
selected). It is non-circular — it asserts non-nullness of a column, it does not
read `is_withdrawal` back from a source and compare it with itself, which is the
shape a tautology here would have taken. And the extension is *required* by the
invariant's structure rather than bolted on to catch a mutation: both branches of
each content invariant are keyed on `is_withdrawal`, so a null value makes the
check unevaluable, and `L2-FORMAT`'s rule that an absent input be a separate
reported case rather than a quiet pass is what the disjunct implements. The
comments in both audits say exactly this.

The rest of the 20/0 is honest. Every `*_matches_producing_source` audit
recomputes its expectation from `raw.customer_mgmt_action` / `ce.account_changes`
with its own carry-forward and never reads the column under test back from
`governed.*`, which is why the `swap` mutations fire and not only the nulls. No
mutation is caught solely by the `reports: true` invariant (the harness excludes
it by design, and I confirmed it appears in no `fired` list). `is_withdrawal`
has no `swap` mutation in the set, being boolean; I checked by hand that a flip
to true on a non-withdrawal statement would fire both
`inv.account_statement_has_content`'s third clause and
`inv.withdrawal_never_reaches_account_status`, so the gap is covered even though
it is untested.

## Evidence

- `check`: `status: question`, `problems: []`. Both questions are the two named in
  the mandate and neither is a problem. `acceptance.accepted: false` with reason
  "the projection changed after the review that accepted it" — the normal
  mid-cycle state; stamping is not mine to do and I have not run it.
- `run`: `ok: true`, all 19 must-hold audits at 0 violations,
  `findings_for_the_business: {}`, 5 account statements and 2 customer statements.
- `twophase`: ok, `changed_columns: []`.
- `mutate`: 20 mutations, `unprotected: []`.
- `simulate --ce ce-withdrawn-account-v1.json`: `ok: true`, `silent: true`,
  `failures: {}`. Correctly silent: the counterexample's account half arrives on
  `raw.account_cdc`, which this job does not read, and the counterexample document
  itself records that under `blocked_on.L1.hole.change-effective-time`. I confirmed
  all seven CDC handoffs are still deferred in the selected model and that nothing
  was promoted to make the withdrawal cycle look exercised.

## Findings

- **F1 (defect, must fix).** `audits/inv.account_single_current.sql` resolves the
  account's owner with `MAX(owning_customer_number)` over all the account's
  statements instead of per statement (or from the latest statement), so an
  account whose owner changed across its own statements is checked against the
  wrong customer's withdrawal history; measured, it reports a correct
  zero-current account as a must-hold violation. Same mis-keying of the owner
  relation as the twice-rejected L2 form, now on the audit side.
- **F2 (defect, must fix).** `audits/inv.customer_withdrawal_with_standing_accounts_reported.sql`
  implements only the first of the invariant's two unevaluable inputs: an account
  whose `owning_customer_number` names a customer with no statement in
  `governed.customer` has an unresolvable owner `is_withdrawal` and is passed over
  as though the condition were false, which the invariant's second sentence
  forbids in as many words; the audit's comment restates the clause with that
  input dropped, so the narrowing is undisclosed.

## Observations (not defects, no action required of this projection)

- **O1.** `customer.sql`'s `COALESCE(status, NULL)` is a no-op standing where a
  carry-forward would stand, beside a real one on `tier`. Cosmetic.
- **O2.** `logical.account.owning_customer_number`'s L2 `note` claims
  `inv.account_owner_matches_producing_source`'s non-withdrawal branch checks
  non-nullness; its `IS DISTINCT FROM` form does not, since the expectation is
  recomputed by the same carry-forward and is null in the same case. The L3 audit
  faithfully implements the invariant's statement; the overclaim is the L2's, for
  a later cycle.
- **O3.** `account.sql`'s need for `customer.sql` to have run is enforced only by
  the order of `manifest.json`'s `artifacts` array. Fails loudly on this target.

## What would have changed my mind

On Q1, any of these would have made it a fail: the owner branch comparing the
withdrawal's moment to `a.effective_from`; the branch reading
`raw.customer_mgmt_action` instead of `governed.customer` (dead code, since that
source cannot express a withdrawal); the join keyed on anything but this
statement's own carried owner; or a selected invariant asserting that `is_current`
agrees with the as-of answer at the present moment, which would have made the
existence form contradict a must-hold rather than complement it — I searched for
one and there is none. I will also revisit it, as the `parallel_assumption`
requires, the moment a source can supply a withdrawal dated later than the
present at which "current" is asked.

Absent F1 and F2 this would be a pass: the entity SQL is right on every question
put to it, including the one the label understates, and the withdrawal machinery
is implemented rather than deferred to the day it can fire. Both findings are in
the audits, both are fixable by keying the owner relation the way `account.sql`
already keys it, and neither touches the derivation. But a must-hold audit that
fires on required behavior, and a selected invariant half of whose stated
requirement is missing while its comment reads as though it were present, are
each independently disqualifying — and in a job where no withdrawal can be
observed, an audit no one can exercise is the only thing standing between the
next cycle and the defect this one was written to prevent.

Rejected artifacts: `audits/inv.account_single_current.sql`,
`audits/inv.customer_withdrawal_with_standing_accounts_reported.sql`. Everything
else read is accepted as correct. I have not stamped, and have edited no `.sql`,
`manifest.json`, or `review.json`.

VERDICT: fail
