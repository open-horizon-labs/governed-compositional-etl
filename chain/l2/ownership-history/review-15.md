# Review 15 (L2 semantic-model reviewer): job ownership-history

Scope: cycle 15, the withdrawal recompile. Five groups changed: `sg.current-version`, `sg.history-asof`,
`sg.owner-standing`, `sg.statement-content`, `sg.constructed-scenarios`.

## What I checked

- `sketches/l1-brokerage-intent-v1.md` in full: the new `L1.deletion-withdraws`, the amended
  `L1.current-version`, the extended `L1.owner-standing`, the narrowed `L1.constructed-scenarios`
  exception, and `L1.hole.deletion-reversal` as newly opened.
- `chain/ce/accepted/ce.l1.deletion-withdraws.md` and `ce.l1.withdrawal-reaches-standing.md`, including
  their "adjacent behavior not authorized", "tempting wrong repair" and "deterministic assertion"
  sections.
- `chain/anchors/L2-FORMAT.md` (especially "An invariant that reports rather than holds", the derived-
  attribute rules, the omitted-field rule, and the sufficiency-group/gap rules),
  `DEVELOPER-CONTRACT-L1-L2.md`, `sources-v1.json` (`cdc_flag`, `action_type_meanings`,
  `status_codes`), `semantic-model-v2.schema.json`.
- Every element of `chain/l2/ownership-history/semantic-model.json`: 11 types, 2 entities and all
  their attributes with derivations and nullability, all 23 handoffs and their dispositions, all 20
  invariants, all 7 groups, all 4 holes, the one filed question.
- `counterexamples/proposed/*.json`, in particular `ce-withdrawn-account-v1.json` and
  `ce-report-after-withdrawal-v1.json`.
- `.venv/bin/python scripts/chain_l2.py check ownership-history` → status `question`, zero problems,
  one filed question (constructed status vocabulary), four holes carried.
  `weave ownership-history` → 13 named gaps, zero unnamed; no cross-job type conflict introduced.
- `review-13.md` and `review-14.md` for what was already prescribed and closed.

What is right, and I want it on the record before the findings: every CDC handoff is still `deferred`
with a note naming `L1.hole.change-effective-time` — including the two new `cdc_flag -> is_withdrawal`
handoffs, which the Developer could easily have promoted to make the recompile look exercised and did
not. Every changed group's gap says in as many words that the withdrawal behavior is unexercised and
why. `is_withdrawal` is not defaulted: its derivation enumerates which sources determine it false and
says the true branch is unreachable today. The `ca_st_id`/`c_st_id` handoff notes pre-commit the
undeferred handoff to reading only I/U rows. That is honest deferral, and it answers question 2 in
the affirmative for the sources. The findings below are about rules the model wrote *around* the
deferral, which L3 will compile whether or not a withdrawal row ever arrives.

## Findings

### F1 (major) — `logical.account.owning_customer_number` makes a withdrawal statement assert a standing fact

`L1.statement-content` names three standing facts for an account: open/closed, tax treatment, and
**which customer owns it**. `L1.deletion-withdraws` says a withdrawal "creates nothing" and that the
record "has no standing" from its moment. The recompile made `status` and `tax_treatment` nullable and
wrote, on each, a note that they are null when `is_withdrawal` is true. `owning_customer_number` was
left `nullable: false`, with no withdrawal branch anywhere: not in its `necessity`, not in its
`carried_forward_from_previous_statement` rule (which, unlike `tier`'s and `tax_treatment`'s, does not
say "the carried-forward derivation does not apply to a withdrawal"), not in its
`parallel_assumption`, and not in `inv.account_owner_matches_producing_source`, which received none of
the non-withdrawal narrowing its four sibling value-correctness invariants got and flatly requires
`owning_customer_number` to equal the producing source's `c_id`.

Wrong behavior this produces: once `raw.account_cdc` is undeferred, a `cdc_flag = 'D'` row is a
statement with `is_withdrawal` true, null status, null tax treatment — and a **non-null owner**,
supplied either by `handoff.raw.account_cdc.c_id -> logical.account.owning_customer_number` (whose
note carries no I/U restriction, unlike the `ca_st_id` handoff's) or by the carry-forward derivation.
The withdrawal statement then asserts "account 624 is owned by customer 238" at a moment the clause
says account 624 has no standing at all. Worse, the `NOT NULL` is load-bearing at L3: an L3 Developer
projecting a D row must either invent an owner or drop the withdrawal statement, and dropping it
loses the `is_withdrawal` marker the whole recompile depends on.

Fix: make `owning_customer_number` nullable with the same note the other two carry, add the
withdrawal exception to `inv.account_owner_matches_producing_source`, add the I/U restriction to the
`raw.account_cdc.c_id` handoff note, and extend `inv.withdrawal_never_reaches_account_status` (or add
siblings) to cover tax treatment and owner, not only status. Either all three of
`L1.statement-content`'s account facts are absent on a withdrawal or none is; the model currently
splits them two-to-one with no clause behind the split.

### F2 (major) — `is_current` and `inv.customer_asof_has_unique_answer` silently answer `L1.hole.deletion-reversal`

`L1.hole.deletion-reversal` is explicit: "Until answered, no job may treat a report received after a
withdrawal as resuming the record." `hole.deletion_reversal` is present in the model as `deferred` —
and is cited by no changed element, has no `blocks`, and is named in no group's gap.

Meanwhile the new `is_current` rule reads: "false when this statement's own `is_withdrawal` is true;
otherwise true when no statement of the same `account_number` has a later `effective_from`." And
`inv.customer_asof_has_unique_answer` reads: "no answer ... if the latest statement of that customer
effective at or before T is a withdrawal ... otherwise exactly one statement — the latest one
effective at or before T — is the as-of answer."

Wrong behavior: for a customer with statements W (withdrawal, 2017-07-08) then U (an ordinary CDC
update, 2018-01-01), both rules make U current and make U the as-of answer for every T ≥ 2018-01-01.
The record resumes its standing — exactly the behavior the hole forbids, reached by a rule the model
wrote rather than by an omission. `trade-lifecycle` got this right for the same clause: its `withdrawn`
attribute is monotonic and its group's gap names `L1.hole.deletion-reversal` as the bound. This job's
`sg.current-version` and `sg.history-asof` gaps name only `L1.hole.change-effective-time` and do not
mention the reversal hole at all. This also answers question 5's second half: yes, a gap omits a hole
that in fact bounds it.

Fix: `is_current`'s rule and the two as-of invariants must be bounded on the reversal case — either
"a statement later than a withdrawal of the same record is not treated as resuming, pending
`L1.hole.deletion-reversal`" (matching trade-lifecycle's monotonic reading, which the hole's own
"until answered" sentence licenses), or the reversal case is excluded from both rules and the affected
behavior deferred. Either way `sg.current-version` and `sg.history-asof` must name
`L1.hole.deletion-reversal` in their gaps, and `hole.deletion_reversal.blocks` must list them.

### F3 (major) — `inv.account_asof_carries_customer_asof` states the owner-standing cascade as a check with no derivation producing it, and contradicts `is_current`

`ce.l1.withdrawal-reaches-standing` says `sg.owner-standing` "gains a projectable rule where it had
none". What it gained is one invariant — a must-hold assertion that the account's as-of answer is
absent whenever its owner's is. No attribute, derivation or handoff produces that behavior. `is_current`
is computed *only* from the account's own statements and its own `is_withdrawal`, so after customer
238 is withdrawn, account 428 still has `is_current = true` and still resolves an as-of answer at
every moment from its own last statement.

Wrong behavior: the required outcome (the account has no standing) is nowhere compiled, so an L3
projection that does the obvious thing produces an account with a current statement and an as-of
answer, and `inv.account_asof_carries_customer_asof` fires as a **must-hold failure** — reporting the
projection as defective for behavior the model never asked it to implement. And the model is internally
inconsistent while it does so: `is_current` claims the account has a current statement at the same
moment the invariant claims it has no as-of answer. `L1.current-version` reads current-ness off the
record's *own* latest statement; `L1.owner-standing` removes standing through the *owner*. L1 does not
say which governs "current" for an account whose owner is withdrawn, and this is precisely the kind of
gap `L2-FORMAT.md` says to put in `questions_for_authority` — not to leave as two elements asserting
opposite things.

Fix: either give the cascade a derivation (an as-of resolution rule stating that an account statement
resolves as an answer only when the owner's as-of answer at the same moment exists — derivable from
`L1.owner-standing` plus `L1.as-of` without touching
`L1.hole.owner-change-reversions-account`, since it creates no new account statement), or file a
question for authority on whether an owner-withdrawn account has a current statement, and say in
`sg.owner-standing`'s coverage claim that the cascade is asserted but not produced. As written the
coverage claim says the invariant "requires" the pairing — true — while the claim reads as though the
model delivers it.

### F4 (medium) — `inv.customer_withdrawal_with_standing_accounts_reported`: reporting is right, but two of `L2-FORMAT.md`'s requirements are unmet

Reporting *is* the right mechanism. `ce.l1.withdrawal-reaches-standing` lists "deciding which of a
customer withdrawal and its standing accounts is the error" under adjacent behavior **not** authorized,
and `L1.deletion-withdraws` says the withdrawal "is reported for review". Applying `L2-FORMAT.md`'s
test: a projection that made these rows disappear would itself be the defect, since the rows mean the
received records contain something only the brokerage can resolve. `reports: true` and
`reported_because_clause: L1.deletion-withdraws` (a member of its own `derived_from`) are correctly
formed. Two requirements from the same section fail:

1. **No counterexample names the rows it is expected to report.** `L2-FORMAT.md`: "a reported
   invariant carries its weight only through the counterexample that names the rows it is expected to
   report; write one." `ce-withdrawn-account-v1.json` names the invariant and then says the expected
   row count is **ZERO**, and that "the row-producing case is a withdrawal of customer 238 while
   accounts 428 and 624 still stand, which would report two rows" — a scenario that exists nowhere in
   `counterexamples/proposed/`. So the flag's second relaxation is live (the mutation harness stops
   using this invariant as evidence that audits protect anything) while nothing yet demonstrates the
   invariant reports anything at all. Fix: write the customer-238 withdrawal scenario, and note that
   `L1.constructed-scenarios`' new exception does not help here — 238 is a *received* customer, so the
   scenario needs no exception; what it needs is a labeled customer-level constructed source, which
   this job does not have (`logical.account.provenance`'s own `parallel_assumption` concedes "no
   equivalent labeled source exists yet for customer statements"). That absence is the real blocker
   and belongs in `questions_for_authority`, not left implicit.
2. **It states its preconditions instead of its behavior when its condition cannot be evaluated.**
   `L2-FORMAT.md`: "Say in `parallel_assumption` what it does when its condition cannot be evaluated,
   because silence is the default and an absent input is a separate question, not a quiet pass." The
   `parallel_assumption` handles the condition being *false* well ("reports zero rows; that is the
   correct empty result of an unexercised condition") but for the unevaluable case says only "Holds
   while `is_withdrawal` is knowable ... and while an account's `owning_customer_number` is knowable" —
   an assumption, not a behavior. Both inputs can genuinely be unknown by the model's own account:
   `handoff.raw.account_cdc.c_id -> owning_customer_number` is deferred, so once the customer CDC
   source is undeferred before or independently of the account one, an account whose owner is only
   resolvable from the deferred source is silently not reported. That is a withdrawal with standing
   accounts going unreported — the exact thing the clause requires be surfaced — reached by silence.
   Fix: state the behavior, e.g. that an account whose `owning_customer_number` or whose owner's
   `is_withdrawal` is not resolvable is itself reported as unevaluable rather than passed over.

Minor, same element: its `review_trigger` ("the change-effective-time hole is resolved and a withdrawn
customer's accounts can be evaluated end to end") is a lifecycle milestone, not a condition that would
make the derivation wrong. Every other invariant in this model states a violation condition.

### F5 (medium) — `sg.unknown-codes`' gap omits `cdc_flag`, which this recompile turned into a read coded field

Before this cycle, `cdc_flag` derived nothing in this job. The recompile added two handoffs reading it
into `is_withdrawal`. `cdc_flag` has an anchored vocabulary in `sources-v1.json` ({I, U, D}), so
`L1.unknown-codes` now applies to it in this job, and `inv.unknown_codes_held` covers only
`raw.customer_mgmt_action.action_type`. `sg.unknown-codes`' gap was extended in an earlier cycle to
name `c_st_id` and `ca_st_id` as deferred coded fields it must eventually cover — and was not extended
this cycle to name `cdc_flag`.

Wrong behavior: `is_withdrawal`'s derivation enumerates false for the two withdrawal-incapable
sources and true for `cdc_flag = 'D'`, and says nothing about any other value; with `nullable: false`
the attribute must take a value, so an undeferred `cdc_flag = 'Q'` row (exactly the case
`ce-held-for-review-trades-v1` exercises for trades, where flag Q is held) resolves to `is_withdrawal
= false` by falling through — reading a meaning into an unnamed code, which `L1.unknown-codes` forbids
in as many words, and it is reported by nothing. Fix: name `cdc_flag` in `sg.unknown-codes`' gap
alongside `c_st_id`/`ca_st_id`, and state in `is_withdrawal`'s rule that a `cdc_flag` outside the
anchored vocabulary holds the record under `L1.unknown-codes` rather than yielding false.

### F6 (low) — `inv.unknown_codes_held`'s `necessity` overclaims against its own `statement`

The `necessity` says this job reads "`ce.account_changes` rows, whose `status_id` it reads directly
with no anchored vocabulary at all; this invariant is the direct, deterministic check that **both** are
reported". The `statement` checks only `raw.customer_mgmt_action.action_type`, and the group's
`coverage_claim` correctly says "the one coded field". Given that whether `status_id` has a vocabulary
at all is the model's one open question, checking it would be premature — so the `statement` and
`coverage_claim` are right and the `necessity` is the error. Fix: drop the `both` clause from
`necessity`. Not a cycle-15 change, but it is the one place a coverage claim in this model claims more
than its member delivers.

### Not findings, recorded so the next reviewer does not re-litigate them

- **A withdrawal as a statement row.** I looked for the argument that a withdrawal should not be a
  `logical.customer`/`logical.account` statement at all. `L1.current-version` itself says "none once
  **its latest statement** is a withdrawal", so L1's own language treats a withdrawal as a statement.
  The model follows L1 here; I would not reject it.
- **Reading `cdc_flag = 'D'` as a withdrawal.** The handoff's `parallel_assumption` says this
  supersedes the anchor's own note ("meaning is `L1.hole.deletions`"). That looks like a Developer
  overriding an anchor, but `sources-v1.json` states as shape that a D row is "the record is marked
  deleted", and `L1.deletion-withdraws` opens with "A report marking a record deleted withdraws...".
  The interpretation is licensed by the anchor's shape fact plus the clause; only the anchor's stale
  hole reference needs cleaning up, and by `L2-FORMAT.md` that is anchor authority's, best raised as a
  question rather than settled in a handoff note. Low, not blocking.
- **The `L1.constructed-scenarios` withdrawal exception.**
  `inv.constructed_account_change_refers_to_known_account`'s narrowing is a faithful restatement, and
  the element says plainly that `ce.account_changes` as anchored has no field that could mark a row a
  withdrawal, so the exception is stated but unexercisable here. That is the honest shape. The
  Developer did not widen the clause or invent a withdrawal field. Correct.
- **Coverage claims on the recompiled groups** otherwise check out against clause text: each names
  which part of which clause it covers, which part belongs to another group, and which belongs to
  another job. `sg.statement-content`'s claim that
  `inv.withdrawal_never_reaches_account_status` is the parallel of
  `inv.account_statement_never_created_by_activity` is accurate.

## Question 3, answered directly: should `status`, `tier` and `tax_treatment` be nullable?

Yes — nullable is the right expression, with one reservation and one thing the model must say and does
not.

`ce.l1.deletion-withdraws` names "a statement whose standing facts are null" as a tempting wrong
repair, so this needs care. But read the reason it gives: "the second leaves the record **current**
with empty facts, which is an answer where the clause says there is none." The harm is the record
remaining current and answerable, not the nulls. This model closes both routes to that harm:
`is_current` is false for a withdrawal statement by its own derivation rule, and
`inv.customer_asof_has_unique_answer` / `inv.account_asof_has_unique_answer` make the as-of answer
absent at or after it. So the nulls here are not an answer where the clause says there is none; they
are the absence of one, on a row that is reachable only as history. `L1.omitted-facts-stand` is not
weakened, because it governs "a change that does not mention a standing fact" — a change that still
asserts the record stands. A withdrawal is not such a change: it withdraws the assertion entirely, so
there is no standing statement for a fact to stand *in*. Carrying tier forward onto a withdrawal
statement would be the real violation of `L1.deletion-withdraws`, and `tier`'s and `tax_treatment`'s
derivation notes say explicitly that the carry-forward does not apply there. That is the correct
reading.

Reservation: the nullability is declared at the attribute level, so it is unconditional, and the only
thing standing between it and a content-free *non-withdrawal* statement is
`inv.customer_statement_has_content` / `inv.account_statement_has_content`. Making these attributes
nullable is not needed for the omitted-field gate rule (`status` is entailed from `action_type` on
every action; `tier` and `tax_treatment` carry forward), so the nulls exist purely for the withdrawal
case and widen the type for every other statement. Given the coordinator has tightened the gate so
nullability no longer discharges carry-forward, I accept it — but the attributes should say the null is
licensed *only* by `is_withdrawal = true`, and `status`'s `derived_from` should cite
`L1.deletion-withdraws` (its note and `parallel_assumption` both reason from that clause; only its
`derived_from` does not list it).

Can the narrowed content invariants be satisfied vacuously? Not today, and not in the direction that
would matter. Today every statement has `is_withdrawal = false`, so the `is_withdrawal = false` guard
selects every row and the invariant quantifies over the whole entity — the narrowing subtracts nothing.
Once a D row exists, that row leaves the first branch but is caught by the second, which both
invariants state bidirectionally ("A withdrawal statement carries neither status nor tier"), and both
`review_trigger`s name the reverse violation. The genuinely vacuous part is that second branch, which
has zero rows to check — and both invariants and `sg.statement-content`'s gap say so in as many words.
So the narrowing is tight; the hole in the same construction is F1, where the third standing fact was
left out of it entirely.

## Elements I would REJECT (not select as authority for L3)

- `logical.account.owning_customer_number` (F1) — non-nullable with no withdrawal branch; makes a
  withdrawal statement assert ownership.
- `inv.account_owner_matches_producing_source` (F1) — requires that assertion.
- `handoff.raw.account_cdc.c_id -> logical.account.owning_customer_number` (F1) — no I/U restriction
  in its note, unlike its `ca_st_id` sibling.
- `logical.customer.is_current`, `logical.account.is_current` (F2) — their derivation rules resume a
  withdrawn record's standing, answering `L1.hole.deletion-reversal`.
- `inv.customer_asof_has_unique_answer`, `inv.account_asof_has_unique_answer` (F2) — same, in as-of
  form.
- `inv.account_asof_carries_customer_asof` (F3) — asserts the owner-standing cascade with no
  derivation producing it, and contradicts `is_current`.
- `inv.customer_withdrawal_with_standing_accounts_reported` (F4) — `reports: true` without the
  counterexample naming its rows, and without stated behavior for an unevaluable condition.

Everything else in the five recompiled groups I would select, including `is_withdrawal` on both
entities, the two `cdc_flag` handoffs as `deferred`, both narrowed content invariants,
`inv.withdrawal_never_reaches_account_status`, and
`inv.constructed_account_change_refers_to_known_account`.

## What would have changed my mind

On F1: an element saying why the owner is a fact a withdrawal may still assert while open/closed and
tax treatment are not. There is none, and `L1.statement-content` lists all three together.
On F2: `L1.hole.deletion-reversal` named in `sg.current-version`'s or `sg.history-asof`'s gap, or a
monotonicity clause in `is_current`'s rule matching what `trade-lifecycle` wrote for the same hole.
On F3: a derivation, or a filed question, for the account's loss of standing through its owner.
On F4: a counterexample expecting a non-zero row count from that invariant, and a sentence saying what
it does when `is_withdrawal` or the owner cannot be evaluated.
If those four existed I would have passed this model, because the deferral discipline (question 2) and
the nullability reading (question 3) are both sound.

VERDICT: fail
