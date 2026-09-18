# Review 10 — `chain/l3/duckdb-sqlmesh/ownership-history/` (rework of review-9)

Reviewer: projection reviewer (capable model), verification of the rework against
`chain/l2/ownership-history/selected-model.json` restricted to
`chain/l2/ownership-history/review.json`'s `selected_element_ids`.

Runs, all from the integrated tree (not a worktree): `check` → `question`, zero problems, the
same two questions review-9 answered. `run` → `ok`, 20/20 audits pass, 6 on `governed.customer`
and 14 on `governed.account`. `twophase` → `ok`, `changed_columns: []`, account 428's three
statements unchanged across the rollover. `compare duckdb-native ownership-history --against
duckdb-sqlmesh` → `both_ok: true`, `identical: true`, 2/2 and 5/5 rows, `columns_match: true`.

None of that is evidence about anything this review is for. Every producing branch hardcodes
`FALSE AS is_withdrawal`, so every withdrawal CTE in both models and in every audit is an empty
relation; `run`'s zeros and `compare`'s `identical` describe only accounts and customers that
have never been withdrawn, which is all the fixture contains. I judged the SQL by reading it and,
where I wanted a fact, by building the withdrawal data myself and executing the audit files
verbatim against it in DuckDB 1.5.5 (`@this_model` → a synthetic account relation,
`governed.customer` → a synthetic customer relation; the audit bodies were read from the files,
not retyped).

Diff surface of the rework, confirmed against `HEAD~1`: six audit files and a comment block in
`models/account.sql`. No `.sql` model logic, no `manifest.json`, no `review.json` changed. I have
written only this file and have not stamped.

---

## F1 — fixed. Verified.

`audits/inv.account_statement_has_content.sql` is now

```sql
WHERE is_withdrawal IS NULL
   OR (NOT is_withdrawal AND (status IS NULL OR tax_treatment IS NULL))
   OR (is_withdrawal AND (status IS NOT NULL OR tax_treatment IS NOT NULL));
```

and `inv.customer_statement_has_content.sql` is the same shape over `status`/`tier`. Checked
against the three things that made F1 blocking:

- The direct contradiction is gone. A withdrawal statement with null `status` and null
  `tax_treatment` — the shape `logical.account.status`/`tax_treatment`'s `nullable: true` licenses
  and `audits/inv.withdrawal_never_reaches_account_status.sql` positively requires — now passes
  both audits. There is no longer a row that two must-hold audits over one model forbid in
  opposite directions. I re-read `inv.withdrawal_never_reaches_account_status`'s body and the two
  are now aligned rather than opposed (the withdrawal arm of `has_content` duplicates it for
  `account`; duplication is not contradiction).
- The exception is in the header prose, not only in the predicate, and it names
  `L1.deletion-withdraws` as its ground. The pre-move text is gone from both files.
- The `is_withdrawal IS NULL` disjunct is a real strengthening, not padding: an unresolvable flag
  now fails rather than falling through both guarded arms into a silent pass. It cannot fire
  today (`is_withdrawal` is a `FALSE` literal in every producing branch) and costs nothing.

No false-fire path found. The constructed-arm `status` null on an unknown `status_id` still fails
blocking, now through the `NOT is_withdrawal` arm of this audit and through
`inv.account_status_matches_producing_source` comparing against `c.status_id` unwrapped, so
review-9's Q2 note that F1 removed a net is answered.

## F2 — fixed, and the reasoning holds. Verified, with one qualification (O1).

`inv.account_single_current.sql` now keeps `own_withdrawn` as `MAX(...)` over every statement of
the account and computes `owner_withdrawn` from a `latest_statement` CTE filtered to `rn = 1`.

**Question 1: is the load-bearing claim true?** I read `logical.account.is_current`'s rule in
full, in the L2 and as projected. The `CASE` is:

```
WHEN f.is_withdrawal THEN FALSE
WHEN aw.first_withdrawal_from IS NOT NULL AND aw.first_withdrawal_from <= f.effective_from THEN FALSE
WHEN cw.customer_number IS NOT NULL THEN FALSE
ELSE f.effective_from = MAX(f.effective_from) OVER (PARTITION BY f.account_number)
```

`TRUE` is reachable from exactly one place, the `ELSE`, and the `ELSE` is an equality against the
partition maximum. The three preceding branches can only turn a row `FALSE`. So no branch can
leave a non-maximal statement current — the claim's first half is unconditionally true.

The second half — "the latest not current while an earlier one is" — is likewise impossible:
if the latest statement is forced `FALSE` by own-withdrawal, then a withdrawal exists at some
moment `w`; any earlier statement either sits at or after `w` (`FALSE` by the same branch) or
before `w`, and then fails the `ELSE` because the withdrawal statement itself is later. If the
latest is forced `FALSE` by the owner branch, an earlier statement can only be current by being
maximal, which it is not. I built both configurations and executed the model expression: account
900 (single owner, owner withdrawn) yields zero current statements, and the audit's
`own_withdrawn = 0, owner_withdrawn = 1 → current_count <> 0` arm passes.

So keying the owner flag on the latest statement is sound, and it fixes what review-9 named. The
divergent case review-9 built — account with a statement at t1 owned by withdrawn C1 and at t2
owned by standing C2 — I reproduced (account 901): the model gives t1 `FALSE`, t2 `TRUE`,
`current_count = 1`, and the reworked audit returns zero rows. Under the old `MAX` form it
returned the account. The fix is real and I tested it rather than reading it.

**Question 2: the missing tiebreak.** `ROW_NUMBER() OVER (PARTITION BY account_number ORDER BY
effective_from DESC)` with `rn = 1` and no secondary key. Two statements of one account sharing an
`effective_from` are *not* prevented anywhere in the projection: `unioned` is a bare `UNION ALL`
of `from_actions` and `from_constructed` with no dedupe, and nothing stops a `ce.account_changes`
row from carrying the same `(account_id, action_at)` as a `raw.customer_mgmt_action` row's
`(ca_id, action_ts)`, nor two raw rows from sharing both. The anchored sources declare no
uniqueness that forbids it. So the tie is producible.

When it happens the pick is arbitrary: DuckDB's `ROW_NUMBER` over an unresolved tie is
unspecified, and if the two tied latest statements name different owners — one withdrawn, one not
— the audit's verdict flips with the pick. I built that case (account 910, tied statements owned
by withdrawn C10 and standing C20) and the audit returned the account on every run in my
environment, but that stability is incidental, not guaranteed by the query.

I am **not** making this blocking, for one reason I checked rather than assumed: a tie is itself a
blocking violation of two other must-hold audits that are present and correct —
`inv.account_statements_no_overlap` (`GROUP BY account_number, effective_from HAVING COUNT(*) > 1`)
and `inv.account_asof_has_unique_answer`'s second arm — and both are bare `AUDIT (name ...)`
headers, so no tied data can reach acceptance regardless of what `single_current` decides. The
residual exposure is a nondeterministic extra failure attributed to the wrong invariant, not data
escaping. It is worth an explicit tiebreak (any total order, e.g. `ORDER BY effective_from DESC,
owning_customer_number DESC`) and a sentence in the header saying the latest statement's
uniqueness is guaranteed by `inv.account_statements_no_overlap`, not by this audit — because the
header currently asserts "the account's own latest-dated statement" in the singular, and the
model's `ELSE` arm marks *both* tied rows current, which is the one case where the header's
premise is false. Recorded as O1.

## F3 — not fixed. The widened T set turns a vacuous audit into a blocking failure on correctly-projected data. **This is the rejection.**

The union is exactly what review-9 asked for, and that is the problem: widening T without
widening the audit's notion of "the account has an as-of answer at T" makes the audit fire on
the single case it exists to bless.

`inv.account_asof_has_unique_answer`'s selected statement says an account has **no** as-of answer
at T when "the customer named by this account's `owning_customer_number` has some withdrawal
statement with an `effective_from` at or before T ... an owner withdrawn at or before T forecloses
the account's answer at T even when the account's own last statement long predates the owner's
withdrawal." `inv.account_asof_carries_customer_asof` states the pairing and says of itself that
it "does not produce the cascade itself, and should not be read as its source."

The reworked audit's fire condition is

```sql
WHERE aa.account_has_statement_by_t
  AND NOT aa.account_withdrawn_by_t
  AND ( aa.owner_at_t IS NULL
     OR EXISTS (... cw.first_withdrawal_from <= aa.t)
     OR NOT EXISTS (... c.effective_from <= aa.t) )
```

`account_has_statement_by_t AND NOT account_withdrawn_by_t` is its proxy for "the account has an
as-of answer at T". That proxy omits the owner-withdrawal foreclosure — the very branch this
audit is designated to check. So at `T = the owner's first withdrawal moment`, which the union
has now put into the T set, the audit concludes the account still has an answer, finds the owner
has none, and reports a violation — for an account whose answer the model has correctly
withdrawn.

Built and executed, with the audit body taken verbatim from the file:

| account | statements | owner history | reworked audit |
|---|---|---|---|
| 900 | 2010-01-01, owner C10 | C10 withdrawn 2015-06-01 | **fires at T=2015-06-01** |
| 901 | 2010 owner C10, 2012 owner C20 | C10 withdrawn 2015-06-01 | passes |
| 902 | 2010 owner C10, 2016 owner C20 | C10 withdrawn 2015-06-01 | **fires at T=2015-06-01** |

Account 900 is review-17's account-428 shape: a single owner, withdrawn long after the account's
last statement. The model handles it correctly — zero current statements, no as-of answer at
2015-06-01 — and `inv.account_single_current` passes it. `inv.account_asof_carries_customer_asof`
is a bare `AUDIT (name ...)` header, therefore blocking, therefore the build fails.

This is, precisely, the failure mode `chain/l2/ownership-history/review.json`'s notes record as
the reason L2 reviews 15 and 16 were rejected: "an owner-withdrawn account went on reporting
is_current true while `inv.account_asof_carries_customer_asof` fired as a must-hold failure for
behavior nothing produced." Half of it has been fixed — the model now reports `is_current false`
— and the rework has reinstated the other half from the opposite direction. Review-17's stated
acceptance criterion was "the carrying invariant agreeing rather than firing." It fires.

Account 902 is worse, because it is a contradiction between two must-hold audits over one model
rather than a single wrong failure. The rework's own F2 justification says in prose that "an
account whose owner changed from a withdrawn C1 to a standing C2 has its latest statement owned
by C2, and is correctly current." `inv.account_single_current` agrees and passes 902.
`inv.account_asof_carries_customer_asof` fails 902. Two blocking audits, one model, no data that
satisfies both — the F1 class exactly, moved from `has_content` into the pair the rework touched.

There is a correct form, and it is small. Add the owner-foreclosure to the precondition, where
the L2 puts it, and drop the now-redundant disjunct:

```sql
WHERE aa.account_has_statement_by_t
  AND NOT aa.account_withdrawn_by_t
  AND NOT EXISTS (
    SELECT 1 FROM customer_withdrawal_bound AS cw
    WHERE cw.customer_number = aa.owner_at_t AND cw.first_withdrawal_from <= aa.t)
  AND ( aa.owner_at_t IS NULL
     OR NOT EXISTS (
          SELECT 1 FROM governed.customer AS c
          WHERE c.customer_number = aa.owner_at_t AND c.effective_from <= aa.t) );
```

I ran this against the same synthetic data: zero rows for 900, 901 and 902, and it still fires on
the two genuine violations — an account statement with a null `owning_customer_number`, and an
account whose owner has no statement at all by T (T preceding the customer's first statement).
Those two arms are worth keeping and are not vacuous.

This form does make the withdrawal arm of the pairing tautological — with the owner branch in the
precondition, "account answers and owner does not, by withdrawal" cannot arise by construction.
That is the honest outcome, and it is what review-9's F3 described as the state of affairs: with
no materialized as-of answer column, this audit cannot both check the owner cascade and be
non-contradictory. The choice is between documented vacuity on that arm and a blocking false
failure. The rework chose the second without noticing. If the projection wants a genuine check of
the owner cascade it has to materialize the as-of answer (or an `answers_at_t` relation) and check
that against the customer's, which is a larger change than this cycle; keeping T narrow and the
limitation stated, as review-9 proposed in its non-blocking form, was also acceptable. What is not
acceptable is the current file, which refuses correct data.

The header comment is also now wrong in a way a later Developer will trust: it says the widened T
"tests the moment the owner's answer actually disappears, not only moments before it." What it
tests at that moment is a condition the model is required to violate.

## Q4 — `blocking false`. Re-enumerated across all twenty audit headers, in both directions. Correct.

`grep -n blocking audits/ models/` over the reworked tree returns two lines, both in
`audits/inv.customer_withdrawal_with_standing_accounts_reported.sql`: the header
`AUDIT (name "inv.customer_withdrawal_with_standing_accounts_reported", blocking false);` and a
comment explaining it. I then printed the first line of all twenty audit files: the other nineteen
are bare `AUDIT (name "...")` with no second argument and therefore default to blocking —
`account_asof_carries_customer_asof`, `account_asof_has_unique_answer`,
`account_owner_matches_producing_source`, `account_single_current`,
`account_statement_has_content`, `account_statement_never_created_by_activity`,
`account_statements_no_overlap`, `account_status_matches_producing_source`,
`account_tax_treatment_matches_producing_source`,
`constructed_account_change_refers_to_known_account`, `constructed_scenarios_labeled`,
`customer_asof_has_unique_answer`, `customer_single_current`, `customer_statement_has_content`,
`customer_statements_no_overlap`, `customer_status_matches_producing_source`,
`customer_tier_matches_producing_source`, `unknown_codes_held`,
`withdrawal_never_reaches_account_status`.

Other direction, from the model: enumerating `reports` across all twenty selected invariants
returns exactly one key, `reports: true` on
`inv.customer_withdrawal_with_standing_accounts_reported`, and no other invariant carries the key
at all. The two singletons are the same element. Four of the six files the rework touched are
must-hold audits and all four kept bare headers; none acquired `blocking false`, and the
reporting audit did not lose it. Nothing was quietly declared non-blocking.

## Q5 — what else the rework introduced.

- The null `c_id` gap review-9 traced in Q2 is genuinely closed. Both
  `inv.customer_status_matches_producing_source` and
  `inv.customer_tier_matches_producing_source` now use `LEFT JOIN` plus an explicit
  `m.customer_number IS NULL` disjunct, so a statement with a null `customer_number` — a
  `nullable: false` violation that previously passed all six customer audits — is reported. I
  checked the change cannot false-fire on a correct row: with a matching producing row the
  expected value is computed as before, and for a (future) withdrawal statement with a null
  `status` no producing row matches, expected computes to `NULL`, and `IS DISTINCT FROM` is false.
- The future-dating revisit condition is now in `models/account.sql`'s comment above
  `customer_withdrawn`, in the form the L2 review prescribed, naming
  `L1.hole.change-effective-time` and the as-of-now form the branch must move to. That closes
  review-9's non-defect gap.
- O1: `inv.account_single_current`'s untiebroken `ROW_NUMBER`, above.
- O2 (observation, not a finding, and not a reason for this verdict): the two `has_content`
  audits and `inv.account_owner_matches_producing_source` now assert, in the withdrawal
  direction, that a withdrawal statement carries null facts — but neither model has a branch that
  would produce that. `filled` in both `account.sql` and `customer.sql` carries `tax_treatment`,
  `owning_customer_number` and `tier` forward with `LAST_VALUE(... IGNORE NULLS)` across *all*
  statements of a key, with no `is_withdrawal` suppression. The moment
  `L1.hole.change-effective-time` is answered and a withdrawal row exists, the carry-forward will
  populate those columns on it and three blocking audits will fire against the models' own SQL.
  `customer.sql`'s comment already flags the branch as unexercised. No currently-producible row
  misbehaves and the suppression belongs in the cycle that undefers the CDC handoff, so I am not
  counting it as a defect of this deliverable — but the audits now assert a shape the models do
  not implement, and whoever answers that hole should fix both halves in one move.

## What would have changed my mind on F3

- If the account genuinely retained an as-of answer at T after its owner's withdrawal, the audit
  would be right to fire. `inv.account_asof_has_unique_answer`'s statement says the opposite in
  its own words, twice, and `inv.account_asof_carries_customer_asof` disclaims producing the
  cascade itself. I read both in full.
- If the audit were non-blocking, the firing would be a finding for the business rather than a
  build failure. Its header is bare; the only `blocking false` in the tree is on the reporting
  audit, as Q4 enumerates.
- If the owner-withdrawn shape were unreachable even after the hole is answered, this would be
  theoretical. `logical.account.is_current`'s own rule and the accepted
  `ce.l1.withdrawal-reaches-standing` describe it, and `ce-report-after-withdrawal-v1` /
  `ce-withdrawn-account-v1` build it; it is the population the L2 spent three rounds on.
- If the union had been paired with a widened precondition, there would be no finding. It was not;
  the diff touches only `t_values` and the header comment.
- On F2, I would have failed the fix if any `is_current` branch could make a non-latest statement
  current. None can — `TRUE` is reachable only through the partition-maximum equality, and I
  executed both directions of the claim rather than reading them.

F1 and the Q2 null path are properly fixed and I tested them on data the fixture cannot produce.
F2 is fixed and its stated reasoning is true under this model, subject to O1. F3's fix is the
third consecutive instance of this cycle's pattern: the reported defect was removed and the thing
asserting the old shape beside it — here, the audit's own precondition — was not moved with it.

VERDICT: fail
