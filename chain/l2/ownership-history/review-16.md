# Review 16 (L2 semantic-model reviewer): job ownership-history — verification of the review-15 rework

Scope: verification. `review-15.md` failed this model with six findings; this review checks whether the
rework on disk genuinely addresses each, and whether it introduced anything new.

## What I checked

- `sketches/l1-brokerage-intent-v1.md` in full, with attention to `L1.deletion-withdraws`,
  `L1.current-version`'s amendment, `L1.owner-standing`'s extended second sentence,
  `L1.statement-content`'s three account facts, `L1.unknown-codes`, and
  `L1.hole.deletion-reversal` / `L1.hole.owner-change-reversions-account`.
- `chain/ce/accepted/ce.l1.deletion-withdraws.md`, `ce.l1.withdrawal-reaches-standing.md`,
  `ce.l1.statement-content.md`; `chain/anchors/L2-FORMAT.md` (the reported-invariant section, the
  derived-attribute and omitted-field rules, the sufficiency-group and `blocks` rules) and
  `DEVELOPER-CONTRACT-L1-L2.md`.
- The whole of `chain/l2/ownership-history/semantic-model.json`: 11 types, 2 entities and every
  attribute's nullability, note, derivation, necessity, `parallel_assumption` and `review_trigger`, all
  23 handoffs, all 20 invariants, all 7 groups, all 4 holes, the 2 filed questions. I read the rework as
  a diff against the model `review-15` reviewed (`9703823..HEAD`) and then re-read the changed elements
  whole.
- `counterexamples/proposed/*.json`, in particular `ce-withdrawn-account-v1.json` and
  `ce-report-after-withdrawal-v1.json`.
- `.venv/bin/python scripts/chain_l2.py check ownership-history` → status `question`, **zero problems**,
  two filed questions, four holes carried. The two new gate rules are both satisfied:
  `ce-withdrawn-account-v1.json` names `inv.customer_withdrawal_with_standing_accounts_reported`, and
  every hole named in a field (`L1.hole.deletion-reversal`, `L1.hole.owner-change-reversions-account`)
  is carried by the model. `weave ownership-history` → 13 named gaps, zero unnamed, zero contradictions.

Before the findings: five of the six reported defects are genuinely fixed, and several are fixed more
thoroughly than prescribed. The deferral discipline `review-15` praised is intact — no handoff was
promoted to make the recompile look exercised, and the three newly restricted handoff notes
(`c_tier`, `ca_tax_st`, `c_id`) pre-commit undeferred behavior instead of claiming it now. The model
also filed the question `review-15` said belonged in `questions_for_authority` rather than leaving the
blocker implicit. F3, however, is not fixed; it is narrowed, which is the outcome the rework brief
named as the same defect, and the rework wrote a factually false claim about it into two coverage
claims. And the F2 fix introduced a must-hold contradiction with an invariant it did not touch.

## Per-finding verification

### F1 — VERIFIED (fixed)

`logical.account.owning_customer_number` is now `nullable: true` with a note reading "null for a
statement whose is_withdrawal is true"; the carry-forward rule states in as many words that it does not
apply to a withdrawal; `necessity` argues the parity from `L1.statement-content` naming all three facts
together; `review_trigger` gained "a statement with `is_withdrawal` true carries a non-null
`owning_customer_number`". `inv.account_owner_matches_producing_source` is narrowed to `is_withdrawal =
false` and states the null bidirectionally, with `L1.deletion-withdraws` added to `derived_from` (and
present in `sg.owner-standing`'s parents, so the subset rule holds).
`inv.withdrawal_never_reaches_account_status` now covers `tax_treatment` as well as `status` and says
where the third fact is covered. The three deferred handoff notes (`c_id`, `ca_tax_st`, `c_tier`) each
carry the I/U-only restriction, matching `ca_st_id`'s and `c_st_id`'s.

I checked for the fourth leak. Enumerating every route by which a standing fact can reach a statement:
for the account, `status` (action_type, `ce.account_changes.status_id`, deferred `ca_st_id`),
`tax_treatment` (`ca_tax_st` historical, `ce.account_changes.tax_status_id`, deferred `ca_tax_st`) and
`owning_customer_number` (historical `c_id`, carry-forward, deferred `c_id`); for the customer,
`status` (action_type, deferred `c_st_id`) and `tier` (`c_tier` historical, carry-forward, deferred
`c_tier`). Every non-CDC route is on a source that cannot express a withdrawal at all; every CDC route
now carries the I/U-only note; both carry-forwards are excluded for a withdrawal; all five attributes
are nullable with a withdrawal-licensed-null note and a `review_trigger` naming the non-null-on-
withdrawal violation. I found no fourth place. Two asymmetries I looked at and do not call findings:
there is no customer-side parallel of `inv.withdrawal_never_reaches_account_status`, but both customer
facts are closed at the handoff, attribute and content-invariant level, so no behavior is missing; and
`inv.account_statement_has_content`'s withdrawal branch enumerates status and tax_treatment but not
owner, which is covered instead by `inv.account_owner_matches_producing_source`'s own branch and
`review_trigger`, so the check exists, just not in that sentence.

### F2 — VERIFIED (fixed), but see N1

Both `is_current` rules now foreclose from the withdrawal's own moment: "false when a withdrawal
statement of the same customer_number has an `effective_from` at or before this statement's
`effective_from`". I traced the W(2017-07-08)-then-U(2018-01-01) case: W is false by branch 1, U is
false by branch 2, every earlier statement is false by having a later one, so no statement is current —
the hole's "no job may treat a report received after a withdrawal as resuming the record" is honored.
Both `*_asof_has_unique_answer` invariants now read "no answer if **some** withdrawal statement ... has
an `effective_from` at or before T", which is monotonic and correct. `sg.current-version` and
`sg.history-asof` both name `L1.hole.deletion-reversal` in their gaps and say the foreclosure is this
job's reading of the hole's "until answered" sentence, not an answer to it;
`hole.deletion_reversal.blocks` lists both groups. This is the fix `review-15` asked for, and the
monotonic reading matches `trade-lifecycle`. The construction is sound on the customer side and on the
account's own-withdrawal side, because the withdrawal is itself a statement in the same partition and
therefore dominates every earlier statement of that record. That dominance argument is exactly what
does not transfer to the owner cascade — see F3.

### F3 — NOT FIXED. The cascade is compiled in a form that cannot fire for the population the clause is about.

`logical.account.is_current` gained the branch:

> false when this statement's own `owning_customer_number`'s customer entity has a withdrawal statement
> with an `effective_from` **at or before this statement's `effective_from`**

The comparison is against the *account statement's own* effective moment. `L1.owner-standing` says the
account has no standing **at a moment when its owner has none** — that is a statement about the moment
the question is asked, not about when the account's last statement was dated. Because a withdrawal
"creates nothing" and generates no account statement, and because whether a customer-only change
reversions the account is `L1.hole.owner-change-reversions-account` and left open (the derivation's own
`parallel_assumption` says it assumes the owner is constant unless a new *account* statement changes
it), an owner-withdrawn account's statements are precisely the ones dated **before** the withdrawal.
The branch's condition is therefore false for exactly them.

Wrong behavior, on the model's own fixture. `ce-withdrawn-account-v1.json` names the population: "The
row-producing case is a withdrawal of customer 238 while accounts 428 and 624 still stand". Take
customer 238 withdrawn 2017-07-08, account 428's latest statement 2012-11-15:

- Branch 1: 428's 2012 statement is not itself a withdrawal → not false.
- Branch 2: 428 has no withdrawal of its own → not false.
- Branch 3 (the new cascade): is there a withdrawal of 238 with `effective_from` ≤ 2012-11-15? No; the
  withdrawal is 2017-07-08. → not false.
- Fallback: no later statement of 428 → **`is_current = true`**.

So an account whose owner has been withdrawn still has a current statement. That is `review-15`'s F3
wrong behavior unchanged, and the rework brief's own test — "does some route still reach `is_current =
true` on an owner-withdrawn account?" — answers yes, on the ordinary route, for the canonical fixture.
The model's own reporting invariant defines the target population as accounts that "would otherwise
carry a standing **at or after** the withdrawal's effective moment"; the cascade branch covers only the
disjoint complement, accounts with a statement at or after the withdrawal, which no source produces
today and which `L1.hole.owner-change-reversions-account` leaves open in any case.

The as-of side is worse: it got no owner branch at all. `inv.account_asof_has_unique_answer` — the
element that actually produces "does this account have an as-of answer at T" — says there is no answer
only "if some withdrawal statement **of that account**" is at or before T. The owner's withdrawal is
not a statement of that account. So at T = 2018: customer 238 has no as-of answer (by
`inv.customer_asof_has_unique_answer`, correctly), and account 428 answers with its 2012 statement.
`inv.account_asof_carries_customer_asof` then fires as a **must-hold failure** — reporting the L3
projection as defective for behavior no derivation in the model asks it to implement. That is F3's harm
reproduced verbatim, and it is now reproduced despite two elements asserting it has been fixed.

Two factually false claims were written to cover this:

1. `inv.account_asof_carries_customer_asof`'s statement: "This invariant is now the direct check of the
   same rule `logical.account.is_current`'s own derivation compiles ... generalized here to arbitrary T
   using the same `effective_from`-ordered reasoning ... it does not introduce the cascade on its own."
   It is not the same rule. The invariant is keyed on T; the derivation is keyed on the statement's own
   `effective_from`. The invariant is the correct rule and the derivation is not an instance of it; the
   invariant still introduces the cascade on its own, for every T at which the derivation is silent.
   Its `necessity` repeats the claim ("checks that compiled behavior rather than asserting a requirement
   with nothing behind it").
2. `sg.owner-standing`'s coverage claim: "The owner-standing cascade this group covers ... is now
   produced, not merely asserted", and its gap: "The cascade and the reporting invariant are fully
   expressed". The cascade is not produced for the population the clause is about, so "fully expressed"
   is false. `sg.current-version`'s coverage claim carries the same false claim in the other direction
   ("which is where `L1.owner-standing`'s extended second sentence is actually compiled").

Also unfixed on the same element: `logical.account.is_current`'s `review_trigger` was **not** updated.
It still reads "zero or more than one statement of the same account_number is flagged current, or a
statement with `is_withdrawal` true is flagged current" — no condition for a statement dated at or after
the account's own withdrawal being current, and none for an owner-withdrawn account being current, while
its customer sibling's trigger did gain the reversal condition. So neither new branch has a violation
condition on the attribute that compiles it.

Fix: the cascade must be keyed on the moment the question is asked, not on the statement's own date. For
`is_current`: false for every statement of an account whose owning customer carries a withdrawal at or
before the present, full stop. For the as-of side: `inv.account_asof_has_unique_answer` needs the owner
branch, so that "no answer at T" is *produced* when the owner has no answer at T, and
`inv.account_asof_carries_customer_asof` becomes a check of it rather than its only source. Then the two
coverage claims above become true and can stay. Alternatively, file the question `review-15` offered as
the second option — whether an owner-withdrawn account has a current statement — and say plainly in
`sg.owner-standing` that the cascade is asserted and not produced. What is not acceptable is the present
state, which claims production and delivers a branch that cannot fire for the clause's own population.

### F4 — VERIFIED (fixed, within the Developer's authority)

Requirement 2 is met and met as a behavior, not a restated assumption. The invariant's `statement` —
the behavior slot — now says an account whose `owning_customer_number`, or whose owner's
`is_withdrawal`, cannot be resolved "is itself reported as unevaluable for this check, naming the
account and which input could not be resolved, rather than passed over as though the condition were
false". That is a row-producing rule with a stated payload and a stated trigger, and it is restated in
`parallel_assumption` where `L2-FORMAT.md` requires it, with the concrete mechanism (the account-side
and customer-side CDC handoffs are deferred separately and need not be undeferred together) in
`necessity`. `review_trigger` is now a violation condition on both branches, replacing the lifecycle
milestone. I checked it is not circular: the unevaluable branch keys on inputs the model elsewhere
declares deferred, so it is checkable the moment either source is promoted.

Requirement 1 is still formally unmet — no counterexample names a non-zero expected row count — but the
Developer discharged it as far as its authority reaches. `ce-withdrawn-account-v1.json`'s own
`blocked_on` explains why the row-producing scenario is unwritable: it needs a labeled customer-level
constructed source this job does not have, which is an anchor shape change. `L2-FORMAT.md` says anchor
limitations go in `questions_for_authority`, and the rework filed a precise question asking for a
`ce.customer_changes` source. Both the invariant's `parallel_assumption` and `sg.owner-standing`'s gap
now say the counterexample is absent and point at the question. I would not fail a Developer for this;
I flag it for the coordinator as a live `reports: true` flag with no row-producing witness.

### F5 — VERIFIED (fixed)

`sg.unknown-codes`' gap now names `raw.customer_cdc.cdc_flag` and `raw.account_cdc.cdc_flag` alongside
`c_st_id`/`ca_st_id`, and says in as many words that nothing in the group projects the hold yet. Both
`is_withdrawal` rules now enumerate I and U as false and state that a flag outside the anchored
{I, U, D} vocabulary is held under `L1.unknown-codes`, with "no fact, including `is_withdrawal`, is
derived from it at all" — closing the fall-through-to-false route F5 named.

One residual I considered and do not raise as a finding. `is_withdrawal` remains `nullable: false` on
both entities while its rule says the attribute "is not populated" for a held row, and its
`review_trigger` still contemplates "a statement ... with an indeterminate `is_withdrawal` value" — a
state `nullable: false` cannot represent. Read against `L1.unknown-codes` ("a held report changes
nothing and creates nothing"), the only consistent resolution is that a held CDC row produces no
statement row at all, in which case `nullable: false` is correct and no cell exists. That is the right
reading and it is the one the clause forces, so I am not naming a wrong behavior. I note it because the
model does not say it in one place, and an L3 Developer resolving the conflict the other way lands back
on F5. One sentence on the attribute — that a held row yields no statement of that customer or account
rather than a statement with an unpopulated flag — would remove the ambiguity.

### F6 — VERIFIED (fixed)

The "both" clause is gone from `inv.unknown_codes_held`'s `necessity`, which now says the invariant
checks `action_type` only and that whether `ce.account_changes.status_id` has a vocabulary at all is the
model's open question. `necessity`, `statement` and `sg.unknown-codes`' coverage claim now agree.

## New findings

### N1 (major, introduced by the F2 fix) — `inv.customer_single_current` / `inv.account_single_current` contradict the new `is_current` rules on the reversal case

Neither single-current invariant was touched. Both read: "If any statement of that customer exists and
its latest statement **is not a withdrawal**, exactly one is current; if the latest statement is a
withdrawal, none is current."

Take the W(2017-07-08)-then-U(2018-01-01) case the F2 fix exists for. The latest statement is U, which
is not a withdrawal, so this must-hold invariant requires **exactly one** current statement. The new
`is_current` derivation produces **zero**. So the F2 fix makes a must-hold invariant fail on precisely
the case it was written to handle, and an L3 projection that implements the fixed derivation is reported
as defective by an invariant in the same model. This is the same species of internal inconsistency
`review-15` rejected `inv.account_asof_carries_customer_asof` for in F3 — two elements asserting
opposite things — and the rework created a fresh instance of it while fixing F2.

The same defect is visible from the other side in `logical.customer.is_current`'s own `review_trigger`,
which lists "**zero** ... statement of the same customer_number is flagged current" as a violation in
the same sentence that now lists "a statement dated at or after a withdrawal ... is flagged current".
Under the new rule, zero-current is the *correct* outcome for any record with a withdrawal anywhere in
its history, so the attribute's own trigger fires on its own correct behavior.

Fix: restate both single-current invariants as `L1.current-version` actually reads — at most one
current statement always; exactly one only while the record stands, where "stands" means no withdrawal
at or before the present, per the same reversal-foreclosure bound the derivations now carry — and drop
"zero" from the `is_current` triggers, or qualify it to records with no withdrawal. This is cheap and
the wording is already available in `L1.current-version`'s own text.

### N2 (medium, introduced) — `sg.owner-standing` is bounded by `L1.hole.deletion-reversal` and neither names it nor is listed in its `blocks`

`inv.account_asof_carries_customer_asof`'s statement now invokes "the reversal-foreclosure reading of
`L1.hole.deletion-reversal`" as one of the three ways the customer can lack an as-of answer. So the
hole bounds this group's member. But `sg.owner-standing`'s gap names only
`L1.hole.owner-change-reversions-account` and `L1.hole.change-effective-time`, and
`hole.deletion_reversal.blocks` lists only `sg.current-version` and `sg.history-asof`. This is exactly
F2's second half — "a gap omits a hole that in fact bounds it" — reintroduced in a third group by the
rework that fixed it in the first two. Fix: name the hole in `sg.owner-standing`'s gap and add the group
to `hole.deletion_reversal.blocks`.

### N3 (low, introduced) — a false file path in a gap and in a filed question

`sg.owner-standing`'s gap and the new `questions_for_authority` entry both cite
`chain/ce/proposed/ce-withdrawn-account-v1.json`. That file does not exist:
`chain/ce/proposed/` holds only `.md` clause proposals, and the counterexample is at
`counterexamples/proposed/ce-withdrawn-account-v1.json`. The model's older citation of
`chain/ce/proposed/ce.k.constructed-status-vocabulary.md` is correct, so this is a new error, not a
house style. It matters because the citation is the whole evidence for the claim that the reporting
invariant's missing counterexample is an explained absence: a reviewer who follows it finds nothing.

## Interactions I checked and found benign

- F1's null `owning_customer_number` on a withdrawal statement feeds F3's cascade branch ("this
  statement's own `owning_customer_number`") and
  `inv.account_asof_carries_customer_asof`'s "that account's `owning_customer_number`". Both are safe
  only because a withdrawal statement is never itself current (branch 1) and never an as-of answer, so
  the null is never read. That holds under the model as written; it is worth stating somewhere, because
  it is load-bearing and currently implicit.
- `L1.owner-standing` was added to `sg.current-version`'s `parent_clauses` and to
  `logical.account.is_current`'s `derived_from`; the subset rule holds, and `weave` reports no new
  cross-job contradiction from the clause now parenting two groups.
- The two new gate rules change nothing here: the `reports: true` invariant is named by
  `ce-withdrawn-account-v1.json`, and every hole named in a field is carried.
- Not re-litigated, per `review-15`'s list: a withdrawal as a statement row; reading `cdc_flag = 'D'`
  as a withdrawal (the handoff notes' reworded stale-anchor sentence is an improvement — it now flags
  the anchor for cleanup instead of claiming to supersede it); the unexercisable
  `L1.constructed-scenarios` withdrawal exception.

## Elements I would REJECT (not select as authority for L3)

- `logical.account.is_current` (F3, N1) — the owner-cascade branch cannot fire for the population
  `L1.owner-standing`'s second sentence is about, and its `review_trigger` names neither new branch.
- `inv.account_asof_has_unique_answer` (F3) — no owner branch at all, so nothing produces the account's
  loss of an as-of answer through its owner.
- `inv.account_asof_carries_customer_asof` (F3) — still the only source of the cascade, and its
  statement and `necessity` now claim falsely that it merely checks a compiled behavior.
- `sg.owner-standing` (F3, N2, N3) — coverage claim and gap assert the cascade is produced and fully
  expressed when it is not; gap omits `L1.hole.deletion-reversal`; false file path.
- `sg.current-version` (F3, N1) — coverage claim asserts the account's `is_current` is where
  `L1.owner-standing`'s second sentence is compiled.
- `inv.customer_single_current`, `inv.account_single_current` (N1) — "exactly one" contradicts the new
  reversal-foreclosure derivations.
- `logical.customer.is_current` (N1, minor) — correct rule; `review_trigger` flags its own correct
  zero-current outcome as a violation.

Everything else in the rework I would select, including all five withdrawal-licensed-null attributes and
their notes, `inv.account_owner_matches_producing_source`, the three newly restricted deferred handoff
notes, the extended `inv.withdrawal_never_reaches_account_status`, both
`*_asof_has_unique_answer` invariants' monotonic withdrawal bound, both `is_withdrawal` rules'
unknown-code branch, `sg.unknown-codes`' extended gap, `inv.unknown_codes_held`, and
`inv.customer_withdrawal_with_standing_accounts_reported` — whose unevaluable-input behavior is the best
element in this rework.

## What would have changed my mind

On F3, the only finding that carries this verdict on its own: a cascade keyed on the moment the question
is asked rather than on the account statement's own `effective_from`, plus an owner branch on
`inv.account_asof_has_unique_answer` so the as-of loss of standing is produced and not only asserted.
Either of those would have made `sg.owner-standing`'s "now produced, not merely asserted" true; with
both, I would have passed this model even with N1, N2 and N3 outstanding, since all three are wording
fixes to elements whose behavior is otherwise right. Concretely, the test I applied and would apply
again: take `ce-withdrawn-account-v1.json`'s own row-producing case — customer 238 withdrawn
2017-07-08, accounts 428 and 624 with statements dated 2008 through 2012 — and ask whether any element
in the model makes those accounts stop being current and stop answering as of 2018. Today none does,
and one fires a must-hold failure because none does.

I want it on the record that the deferral discipline is still intact, that F1 was fixed completely
across all five standing facts rather than patched at the one attribute named, and that F4's
unevaluable-input behavior is a real behavior. The rework is close. It fails on the finding the brief
said to check hardest, in the form the brief predicted: the same defect, narrowed, with a coverage claim
asserting it was widened.

VERDICT: fail
