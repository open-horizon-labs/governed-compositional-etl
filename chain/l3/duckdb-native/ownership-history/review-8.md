# Review 8 (capable-model projection review): ownership-history on duckdb-native

Authority: `chain/l2/ownership-history/selected-model.json` (`model_sha256`
91da9864…8de8c6, matching `chain/l2/ownership-history/review.json`), restricted to
the 61 ids in that review's `selected_element_ids`. Rework under review: commit
e20fc2d, whose only `.sql` changes in this projection are the two audits rejected
by review-7 plus the O1 cosmetic in `customer.sql`. I read the full diff, both
reworked audits in full, `account.sql`, `customer.sql`, `manifest.json`, the six
other audits that mention the owner cascade or `is_withdrawal`,
`logical.account.is_current` and `logical.account.owning_customer_number` in full,
`inv.account_single_current`, `inv.account_statements_no_overlap`,
`inv.account_asof_has_unique_answer`, `inv.account_asof_carries_customer_asof`,
`inv.customer_withdrawal_with_standing_accounts_reported`,
`chain/anchors/sources-v1.json`, and `chain/profiles/duckdb-native.json`. Ran
`check`, `run`, `mutate`, `twophase`.

Review-7's standing caveat governs this review too and I have applied it
throughout: every producing branch hardcodes `FALSE AS is_withdrawal`, so every
withdrawal CTE in this job is an empty relation, `run` exercises only the
non-withdrawal arm, and a green run is not evidence about any question below. Every
judgment here is either a reading of the SQL or a measurement against a population
I built by hand in a scratch DuckDB and ran the audit files against unmodified. The
hand-built cases are named S1–S11 below.

## F1 — `inv.account_single_current`. Fixed. Verified.

The `MAX(owning_customer_number)` aggregate is gone; the owner is resolved from a
`latest_statement` CTE keyed on `MAX(effective_from)` per account, and the join
moved from `acct.owning_customer_number` to `ls.owning_customer_number`. Measured:

- **S1**, review-7's exact repro (account 500, owner 9 in 2010, owner 5 in 2015,
  customer 5 withdrawn, all statements correctly not current): the audit returns
  `[]`. It returned `[('500',)]` before. The false must-hold violation is gone.
- **S2b**, the masking direction, which matters more: account 501, owner 5
  (withdrawn) in 2010 then owner 9 (standing) in 2015, with a genuine
  all-statements-not-current bug injected. The audit returns `[('501',)]`. The
  fix did not buy the false negative back — under the old `MAX(5,9)=9` this
  happened to fire too, but under a `MIN`-shaped or first-statement-shaped fix it
  would not have. Keying on the latest statement is the form that keeps it.
- **S2**, the same shape without the injected bug (exactly one current, on the
  statement whose owner stands): `[]`. Correct.
- **S6**, latest statement is the account's own withdrawal, so `latest_statement`
  hands up a NULL owner and `ow.customer_number IS NULL`: not reported, because
  `own_withdrawal_count = 0` is false. The NULL owner cannot leak into the
  zero-allowance.
- `mutate` still reports `is_current` null and swap as protected by this audit, so
  the rework did not hollow out the protection it already carried.

### Question 1 — is F1's load-bearing reasoning true?

Yes, under this model, and I tested it rather than accepting it.
`logical.account.is_current`'s rule has exactly one branch that can produce TRUE:
"otherwise true when no statement of the same `account_number` has a later
`effective_from` than this one". Every other branch produces FALSE. So `is_current`
= true entails "no later statement exists", i.e. the statement is the latest.
`account.sql` implements that branch as `a.effective_from = MAX(a.effective_from)
OVER (PARTITION BY a.account_number)`, which is the same predicate. No branch can
leave a non-latest statement current.

The converse direction also holds, which is the half that would have broken the
fix if it did not: there is no branch that can leave the latest statement not
current while an earlier one is current, because an earlier statement fails the
only TRUE-producing branch outright. So the set of possibly-current statements is
exactly the set of latest statements, and keying the audit's owner condition on the
latest statement's owner is not merely defensible but is what "its owning customer"
must mean in an invariant about which statement is current. The audit's comment
reproduces this argument rather than just the conclusion.

I looked for the branch that would defeat it and there is none: the owner-cascade,
own-withdrawal and reversal-foreclosure branches are all FALSE-producing, and the
reversal-foreclosure branch (`first_withdrawal_from <= a.effective_from`) can only
subtract from the candidate set, never move currency to an earlier row.

### Question 2 — ties on `MAX(effective_from)`

Ties are permitted. `action_ts` is anchored as part of the row envelope with no
per-account uniqueness constraint (`chain/anchors/sources-v1.json`), two
account-subject actions for one `ca_id` at the same `action_ts` are expressible,
and `ce.account_changes.action_at` can coincide with a received `action_ts`. The
model knows it: `inv.account_statements_no_overlap`'s `review_trigger` is "two
statements of the same `account_number` share an `effective_from`",
`inv.account_single_current`'s `review_trigger` names the same case, and that
invariant's `parallel_assumption` says in as many words that "two statements
claiming the same effective moment would make the current one undecidable".

So yes, the CTE produces two rows and the `JOIN` duplicates. I measured what that
does, in all three directions it could go:

- **S5**, tie with no withdrawals anywhere: `account.sql`'s `MAX() OVER` marks both
  tied rows current, `current_count = 2`, the audit fires — twice (`[('504',),
  ('504',)]`). Duplicate rows in a violations relation, so the count is inflated
  but never zeroed. Cosmetic.
- **S4**, tie where both tied owners are withdrawn, `current_count = 0`: both
  joined rows find a withdrawn owner, correctly not reported.
- **S3**, the dangerous mixed tie — one tied owner withdrawn, one standing: the
  standing-owner row is marked current by `account.sql`, so `current_count = 1` and
  neither the `> 1` nor the `= 0` branch applies. No false violation.

There is no double-count that produces a **false positive**, and I checked why
rather than only observing it: the zero-allowance requires `current_count = 0` with
`own_withdrawal_count = 0`, which can only arise when *every* latest row was falsed
by the owner branch, which means *every* `latest_statement` row joins a withdrawn
owner, so no joined row can have `ow.customer_number IS NULL`. And there is no
**false negative**, because the joined rows are independent: a genuine
all-not-current bug leaves `ow.customer_number IS NULL` on every one of them.

Independently, every tie is caught unconditionally by
`inv.account_statements_no_overlap`, which is a plain `GROUP BY account_number,
effective_from HAVING COUNT(*) > 1` and fired in S3, S4 and S5. So a tie can never
reach a reviewer as a quiet pass of this audit; the run is already red from another
must-hold. The tie is a real property of the CTE and it produces duplicate rows, but
it produces no wrong verdict. Not a finding.

## F2 — `inv.customer_withdrawal_with_standing_accounts_reported`. Fixed. Verified.

### Question 3 — are both arms real, is the second reachable, does the ordinary case survive?

**Arm 2 is real and reachable, including with no CDC at all.** Measured in **S7**:
account 700 owned by customer 77 with `governed.customer` holding no statement for
77 now returns `[('unresolvable_owner', '700', None, None, 'owner_is_withdrawal')]`,
where review-7 measured `[]`. I confirmed the reachability claim through the
derivation rather than taking the comment's word: `customer.sql` filters
`raw.customer_mgmt_action` to `action_type IN ('NEW','UPDCUST','INACT')` while
`account.sql` filters to `('NEW','ADDACCT','UPDACCT','CLOSEACCT')`, and both
`ADDACCT` and `UPDACCT` carry `c_id` per the anchored `fields_present`. A `c_id`
appearing only on account-subject actions therefore yields an account whose owner
the customer entity has never heard of, with no deferred handoff involved. The arm
is not waiting on `L1.hole.change-effective-time` to become exercisable.

**Arm 2 is not a duplicate of arm 0.** The withdrawn-owner arm is an inner `JOIN`
against `withdrawn_customers`, which requires a matching customer statement; arm 2
requires `NOT EXISTS` any customer statement. Disjoint by construction, so no
account can be reported under both.

**Arm 1 still fires.** **S9**: a non-withdrawal statement with a NULL
`owning_customer_number` returns `('unresolvable_owner', '702', None, None,
'owning_customer_number')`. It is unreachable while the derivation holds — the only
NULL owner `account.sql` emits is on a withdrawal row — but it is reachable in the
defect state it exists to catch (a `ce.account_changes` row that is an account's
first statement, which `inv.constructed_account_change_refers_to_known_account`
guards). A defensive check against an unreachable-by-construction state is not the
same as an arm that can never fire.

**The ordinary case the audit exists for still reports.** **S8**: a standing account
whose owner carries a withdrawal returns
`('withdrawn_owner_with_standing_account', '701', 5, 2020-01-01, None)`, naming
account, withdrawn customer and withdrawal moment. **S10**: the same owner
withdrawal where the account's own latest statement is itself a withdrawal is
correctly *not* reported — no standing to lose. The "would otherwise carry a
standing" reading review-7 accepted is intact and the new arm did not perturb it.

**No report became a must-hold failure.** The added arm only adds rows to this one
audit, and `reporting_invariants_for()` reads `reports: true` off the selected L2
model, so `record_audit` files its count under `reported`; `must_hold_failures`
selects only on `violations`, and `mutate` excludes reported invariants from
protection evidence. The non-blocking-declaration cross-check at `chain_l3.py:358`
is `sqlmesh_target`-only and does not bear on this target. `run` is `ok: true` with
all 19 must-hold audits at zero and `findings_for_the_business: {}`.

One thing I want stated precisely rather than left implicit, because it looks like a
regression and is not. In S7 the must-hold `inv.account_asof_carries_customer_asof`
*also* fires. That is not the rework converting a report into a failure: that audit
is byte-identical to the version review-7 accepted, it fired on this same population
when review-7 measured it, and its firing follows from its own selected statement
(the account answers at T while the customer has no answer at T). What the rework
changed is that the reviewer now *also* gets the finding the L2's `necessity` says
they must get, instead of only the must-hold break. That is exactly the inversion F2
named, corrected.

## Question 4 — did the rework introduce anything adjacent?

The cycle's pattern at L2 was that each fix left something asserting the old shape
un-updated. I checked for it directly. `git show e20fc2d` touches exactly three
files in this projection: the two rejected audits and `customer.sql`'s O1 no-op
`COALESCE(status, NULL)`, now `status AS status_raw` — a correct, behavior-free
cleanup of the observation review-7 recorded. No entity SQL logic changed, so
everything review-7 accepted about `account.sql` and `customer.sql` stands unaltered
and I did not re-litigate it.

I then read every audit that mentions the owner cascade or `is_withdrawal` —
`inv.account_owner_matches_producing_source`, `inv.account_asof_carries_customer_asof`,
`inv.account_statement_has_content`, `inv.customer_statement_has_content`,
`inv.customer_single_current`, `inv.withdrawal_never_reaches_account_status`, plus
the two reworked ones — looking for a comment or a predicate still asserting the
pre-fix shape. All six unchanged audits are consistent with the new keying; none of
them resolves an account's owner by aggregate, and none of their comments describes
the owner relation in terms the fix invalidated.

I found one comment that does not match its own SQL, in the reworked file. It is
recorded as O1 below rather than as a defect, and I say why there.

## Question 5 — is `mutate`'s 20/0 real protection for the newly nullable attributes?

Not a tautology, but I want the boundary of what it proves stated, because the
`is_withdrawal IS NULL` disjunct is weaker than "protected" sounds.

It is not circular. The disjunct asserts non-nullness of a persisted column against
the model's `nullable: false` declaration on `logical.account.is_withdrawal`; it
does not read the value back from the expression that produced it and compare it
with itself, which is the shape a tautology here would take. Compare
`inv.account_owner_matches_producing_source`, which recomputes its expectation from
`raw.customer_mgmt_action` and `ce.account_changes` with its own carry-forward and
never reads `governed.account.owning_customer_number` back — which is why its `swap`
mutations fire and not only its nulls.

It is also required by the invariant's structure rather than bolted on: both
branches of each content invariant are keyed on `is_withdrawal`, so a NULL makes the
check unevaluable, and `L2-FORMAT`'s rule that an absent input be a separate reported
case rather than a quiet pass is what the disjunct implements.

What it does *not* prove: because the derivation emits the literal `FALSE`, the
disjunct is unreachable in the compiled output, so what `mutate` demonstrates is
protection of the persisted table against corruption, not protection of the
derivation. A derivation that said FALSE where an undeferred CDC handoff would say
TRUE is caught by nothing here. That is licensed by `L1.hole.change-effective-time`
and by `logical.account.is_withdrawal`'s own `parallel_assumption`, not a defect —
but it is the reason the 20/0 should not be read as covering the withdrawal path.

`is_withdrawal` has only a `null` mutation in the set and no `swap`, being boolean;
I confirmed by reading that a flip to TRUE on a non-withdrawal statement fires both
`inv.account_statement_has_content`'s third clause (`is_withdrawal AND (status IS
NOT NULL OR tax_treatment IS NOT NULL)`) and
`inv.withdrawal_never_reaches_account_status`, and additionally
`inv.account_owner_matches_producing_source`'s second clause. The gap is covered
even though it is untested.

## Evidence

- `check`: `status: question`, `problems: []`. The two questions are the two named
  in the mandate — the moved group fingerprints awaiting a reviewer's stamp, and
  `account.sql`'s declared sibling read of `governed.customer`. Neither is a
  problem. `acceptance.accepted: false`, reason "the projection changed after the
  review that accepted it": the normal mid-cycle state. Stamping is not mine and I
  have not run it.
- `run`: `ok: true`, 19 must-hold audits at 0 violations,
  `findings_for_the_business: {}`, 5 account statements and 2 customer statements.
- `twophase`: ok, `changed_columns: []`.
- `mutate`: 20 mutations, `unprotected: []`. `inv.account_single_current` still
  protects `is_current` null and swap after the rework.
- Hand-built populations S1–S11, run against the audit files unmodified in a
  scratch DuckDB. Per the standing caveat, these and not the run are the evidence
  for every withdrawal-path judgment above.

## Findings

None blocking. Both rejected artifacts are fixed, and I could not construct a
population in which either produces a wrong verdict.

## Observations (not defects, no action required of this projection)

- **O1.** In `inv.customer_withdrawal_with_standing_accounts_reported`, the new
  sentence "Both unevaluable arms are checked over the same population (each
  account's own latest, non-self-withdrawn statement)" is not true of arm 1. Arm 1
  selects from `governed.account` directly, not from `account_own_standing`, so it
  scans every non-withdrawal statement and includes accounts whose latest statement
  *is* a withdrawal. Measured in S9: account 702, whose own record has already
  ended, is reported as unevaluable — a finding handed to the business for an
  account with no standing to lose, which contradicts the audit's own reading of
  "would otherwise carry a standing" three paragraphs above it. It is an
  observation rather than a defect on two grounds: arm 1 is unreachable while the
  derivation holds, and the only state that reaches it is one in which
  `inv.constructed_account_change_refers_to_known_account` is already failing as a
  must-hold, so the over-report can never be the only signal. But it is precisely
  this cycle's recurring shape — a comment asserting an alignment the SQL does not
  have, added in the same edit that claimed it — and the cheapest correction is to
  source arm 1 from `account_own_standing` too, which would also deduplicate it
  (today it reports once per offending statement, not once per account).
- **O2.** The `JOIN latest_statement` in `inv.account_single_current` is an inner
  join, which narrows the audit from unconditional to conditional on the account
  having at least one non-NULL `effective_from`. Measured in S11: an account all of
  whose statements have a NULL `effective_from` and zero current statements is
  silently skipped by this audit, where the pre-fix aggregate form would have
  reported it. Not reachable under the anchors (`action_ts` is the row envelope and
  is present on every action) and loudly covered in the same breath by
  `inv.account_statements_no_overlap` and `inv.account_asof_carries_customer_asof`,
  both of which fired on S11. Recording it so the narrowing is on the record rather
  than discovered later.
- **O3.** Under a tie on `MAX(effective_from)`, both reworked audits emit duplicate
  rows for the same account (S3, S4, S5). Harmless in a violations relation and in
  a findings relation, and every tie is independently caught by
  `inv.account_statements_no_overlap`. Cosmetic.
- **O4.** Review-7's O2 (the `logical.account.owning_customer_number` note
  overclaiming that `inv.account_owner_matches_producing_source`'s non-withdrawal
  branch checks non-nullness) and O3 (`account.sql`'s dependency on `customer.sql`
  enforced only by `manifest.json`'s `artifacts` order) both still stand. Both are
  for other cycles — O2 is the L2's, O3 fails loudly on this target — and neither
  was in scope for this rework.

## What would have changed my mind

On F1: any branch of `logical.account.is_current` capable of producing TRUE for a
non-latest statement, or of leaving the latest statement not current while an
earlier one is — I traced the rule's every branch and there is exactly one
TRUE-producing branch, whose predicate *is* "is the latest". A tie that produced a
false violation or a false pass rather than a duplicate row would also have failed
it; I built the mixed-owner tie specifically to find that and it does not occur, for
a reason I could state (the zero-allowance is unreachable unless every tied latest
row has a withdrawn owner). And had S2b come back empty — the fix buying back a
false negative on the masking direction — I would have failed it regardless of S1.

On F2: an arm 2 that could not fire without an undeferred CDC handoff would have
been the same defect wearing a fix, so I traced its reachability through
`customer.sql`'s and `account.sql`'s differing `action_type` filters rather than
trusting the comment. An arm 2 overlapping arm 0, an ordinary withdrawn-owner case
lost to the new arm (S8), an account whose own record has ended newly reported by
arm 0 (S10), or the added rows counting as must-hold failures would each have failed
it.

I remain bound by the caveat I opened with: nothing in `run`, `twophase` or
`compare` is evidence about any of this, and every claim above rests on the SQL text
and on S1–S11.

Accepted: `audits/inv.account_single_current.sql`,
`audits/inv.customer_withdrawal_with_standing_accounts_reported.sql`, and the
`customer.sql` O1 cleanup. I have not stamped, and have edited no `.sql`,
`manifest.json`, or `review.json`.

VERDICT: pass
