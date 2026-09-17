# Review 17 (L2 semantic-model reviewer): job ownership-history — verification of the third rework

Scope: verification of the third attempt at `review-15`'s F3 (the owner-standing cascade) and of the
three findings `review-16` introduced as N1, N2, N3. `review-16` failed this model on F3 alone and said
in as many words that, with F3 fixed, N1–N3 outstanding would not have carried the verdict. This review
holds itself to that bar: F3 checked on the fixture rather than on the Developer's trace, then every
invariant and trigger over `is_current` and over the as-of answer re-read for the adjacent-defect
pattern that carried the last two cycles.

## What I checked

- `sketches/l1-brokerage-intent-v1.md` in full: `L1.deletion-withdraws`, `L1.current-version` as
  amended, `L1.owner-standing`'s extended second sentence, `L1.statement-content`,
  `L1.hole.deletion-reversal`, `L1.hole.owner-change-reversions-account`,
  `L1.hole.change-effective-time`.
- `chain/ce/accepted/ce.l1.deletion-withdraws.md` and `ce.l1.withdrawal-reaches-standing.md`, including
  the "adjacent behavior not authorized", "tempting wrong repair" and "deterministic assertion"
  sections; `counterexamples/proposed/ce-withdrawn-account-v1.json` in full, including `blocked_on` and
  `expected.reported_rows`.
- `chain/anchors/L2-FORMAT.md` (derived attributes and the two permitted `derivation.kind` values, the
  reported-invariant section, the sufficiency-group and `blocks` rules) and
  `semantic-model-v2.schema.json`'s `derivation` definition.
- The whole model: 11 types, 2 entities and every attribute over `is_current`/`is_withdrawal`/
  `effective_from`/`owning_customer_number`, all 23 handoffs and their dispositions, all 20 invariants,
  all 7 groups, all 4 holes, both filed questions.
- `review-15.md` and `review-16.md`.
- `.venv/bin/python scripts/chain_l2.py check ownership-history` → status `question`, **zero problems**,
  two filed questions, four holes carried. `weave ownership-history` → 13 named gaps, zero unnamed gaps,
  **zero contradictions**, 3 overlaps, 7 dependencies.
- Deferral discipline re-verified from the handoff list itself: all seven CDC handoffs, including both
  `cdc_flag -> is_withdrawal` handoffs, are still `deferred` under `L1.hole.change-effective-time`.
  Nothing was promoted to make this cycle look exercised.

## Item 1 — the fixture, re-traced from the model text rather than from the Developer's trace

Population, from `ce-withdrawn-account-v1.json`'s own `expected.reported_rows`: customer 238 withdrawn
2017-07-08, accounts 428 and 624 whose own statements run 2008-03-14 to 2012-11-15. Take account 428's
2012-11-15 statement, owner 238.

`logical.account.is_current`, branch by branch as written:

1. this statement's own `is_withdrawal` — false. Does not fire.
2. a withdrawal of account 428 with `effective_from <= 2012-11-15` — none. Does not fire.
3. the owning customer 238 has **any** withdrawal statement at all, at any `effective_from`, with no
   comparison to 2012-11-15 — the 2017-07-08 withdrawal exists. **Fires: `is_current` = false.**

So `is_current` comes out **false**, and it comes out false through the branch that is supposed to
produce it, not through the fallback. The date comparison that could never fire is gone; the condition
no longer mentions the account statement's own `effective_from` at all. Verified.

`inv.account_asof_has_unique_answer` at T = 2018-01-01: the third disjunct reads "the customer named by
this account's `owning_customer_number` has some withdrawal statement with an `effective_from` at or
before T". 2017-07-08 ≤ 2018-01-01, so there is **no answer** for 428 at T = 2018. Verified, and the
invariant's own text says the comparison is against T "not against any of the account's own statement
dates", naming the exact error of the last two rounds. This invariant is now genuinely the producer of
the general-T cascade: it is a member of `sg.history-asof`, it takes `L1.owner-standing` into its
`derived_from`, and `sg.history-asof` carries `L1.owner-standing` in `parent_clauses`, so the subset
rule holds and the gate agrees.

`inv.account_asof_carries_customer_asof` at T = 2018: customer 238 has no as-of answer (its own
withdrawal is at or before T, by `inv.customer_asof_has_unique_answer`); account 428 has no as-of answer
by the branch above. The pairing holds, so the invariant **agrees** rather than firing as a must-hold
failure. Its statement and `necessity` now say it checks `inv.account_asof_has_unique_answer`'s owner
branch and "should not be read as its source" — which is true as written, because that branch now
exists and is keyed the same way. Both false coverage-claim sentences `review-16` named are gone:
`sg.owner-standing`'s claim now says the cascade "is produced in two places, neither of them this group"
and names them, and `sg.current-version`'s claim now says the general-T form lives on
`inv.account_asof_has_unique_answer` instead of claiming it for `is_current`. Both statements are now
accurate.

Also checked and now consistent, which it was not last cycle: the reporting invariant's population,
"accounts that would otherwise carry a standing at or after the withdrawal's effective moment". 428
would otherwise answer at T ≥ 2017-07-08 from its 2012 statement, so 428 and 624 are inside the
population the producing rules now cover, rather than in the disjoint complement.

`logical.account.is_current`'s `review_trigger`, the thing not updated last cycle, now carries both new
branches: "a statement dated at or after the account's own withdrawal is flagged current, a statement of
an account whose owning customer carries any withdrawal at all is flagged current". Verified.

## Item 2 — the existence-vs-date asymmetry. It is sound. Here is what makes it sound, so no one re-derives it.

The asymmetry is real: `logical.account.is_current`'s owner branch keys on the mere existence of an
owner withdrawal, while `inv.account_asof_has_unique_answer`'s owner branch keys on T. I tried to break
it with the future-dated withdrawal and could not. Three things make it sound, and only the third is
contingent.

**(a) The two elements answer different questions, and L1 keys them differently.** `L1.as-of` asks what
held at a named moment, so its rule must compare to that moment. `L1.current-version` does not name a
moment at all: the current statement is "the one with no later statement", and there is none "once its
latest statement is a withdrawal". Neither half of that text compares anything to the present instant.
So `is_current` is not "the as-of answer at now", and a divergence between the two at some T is not an
inconsistency — it is the two clauses being about different things.

**(b) Existence, across entities, is exactly what within-partition ordering already does within one.**
This is the argument worth keeping. Take an account whose own withdrawal is dated in the future, W(2030),
with an ordinary statement S(2020). Branch 2 does not fire for S (2030 > 2020). But the fallback does:
W is a later statement of the same account, so S is not current, and W itself is not current by branch 1.
Zero current. The same holds for the customer entity, whose `is_current` has no existence branch at all:
a future-dated customer withdrawal is still a later statement in its own partition, so it zeroes every
earlier statement through the fallback. So the model's `is_current` **already** treats any withdrawal
anywhere in a record's history as foreclosing currency, whatever its date and whatever its relation to
the present. The owner's withdrawal is not a statement of the account, so no fallback can see it;
existence is the only available form that reproduces, across entities, the outcome the record's own
partition produces for itself. A date comparison here would be *less* faithful, not more — it is the
very comparison that failed twice.

**(c) The future-dated case cannot produce a half answer, which is the harm `L1.owner-standing` names.**
Suppose customer 238's withdrawal were dated 2030. Then: account 428 has zero current statements
(existence branch), and customer 238 also has zero current statements (its 2030 withdrawal is the latest
statement in its own partition). The account is never denied standing at a moment its owner has
standing, in the `is_current` sense. On the as-of side both are keyed on T, so at T = 2026 both answer
and at T = 2031 neither does. The pairing `inv.account_asof_carries_customer_asof` requires holds at
every T, and I found no invariant anywhere in the model asserting that the current statement equals the
as-of answer at the present moment — I looked for one specifically, because that is the one assertion
that would turn this asymmetry into a must-hold contradiction. There is none, and none should be added.

**Can the anchored sources produce a future-dated withdrawal at all?** Today, no, by two independent
routes: the only source that supplies an `effective_from` is `raw.customer_mgmt_action.action_ts`, whose
`action_type` vocabulary names no withdrawal action; and the sources that can mark a withdrawal supply
no effective moment of their own, which is why every `cdc_flag` handoff is deferred under
`L1.hole.change-effective-time`. If that hole is answered with the file's batch date, a withdrawal's
moment is a past file date and "now" is genuinely always after it, making the existence branch and a
"withdrawal at or before now" branch equivalent. The one way to get a future-dated withdrawal is for the
business to answer that hole with a forward-dated effective moment. Per (b) and (c) the branch stays
sound even then, so I am not raising this as a finding — but the model nowhere says that the branch's
soundness does not depend on the answer to that hole, and `is_current`'s `parallel_assumption` would be
the place for one sentence recording argument (b). That is a prescription, not a defect.

## Item 3 — N1, the zero-current case

Trace, W(2017-07-08) then U(2018-01-01) on a customer, which is the case the reversal-foreclosure branch
exists for. `is_current`: W false by branch 1, U false by branch 2, earlier statements false by having a
later one — zero current.

- `inv.customer_single_current` now reads "at most one ... always", exactly one only where "no statement
  of that customer is a withdrawal", and "if the record does not still stand -- its latest statement is
  a withdrawal, **or any earlier statement is a withdrawal** and no later report is treated as resuming
  the record -- none is current". Zero is permitted on exactly this case. Verified.
- `inv.account_single_current` adds the owner condition in the existence form that matches the
  derivation ("the owning customer carries no withdrawal statement at all, at any moment"), and "if
  either condition fails, none is current". Zero is permitted for the owner-withdrawn account too, which
  is the account-side case `is_current`'s new branch produces. Verified, and the two are keyed the same
  way, which is the thing that went wrong in cycle 16.
- Both `single_current` `review_trigger`s now condition the zero clause: "a customer/account with no
  withdrawal anywhere in its history has zero or more than one statement flagged current". Both
  `is_current` `review_trigger`s drop the unconditional zero and replace it with "every statement of a
  customer_number with no withdrawal anywhere in its history is flagged not current". Verified: none of
  these four fires on the model's own correct zero-current output.

N2: `sg.owner-standing`'s gap names `L1.hole.deletion-reversal` and says why it bounds the group, and
`hole.deletion_reversal.blocks` now lists all three of `sg.current-version`, `sg.history-asof`,
`sg.owner-standing`. Verified. N3: both citations now read `counterexamples/proposed/ce-withdrawn-account-v1.json`,
and I confirmed that file exists and that the older `chain/ce/proposed/ce.k.constructed-status-vocabulary.md`
citation is still correct. Verified.

## Item 4 — what this rework introduced

One finding, and it is the same species as the last two cycles, one notch smaller.

### R1 (low) — the amended `L1.current-version` did not reach `type.statement_is_current`

N1 was fixed on both `single_current` invariants and on both `is_current` `review_trigger`s. It was not
fixed on the type those four elements are about. `type.statement_is_current`, a member of
`sg.current-version`, still carries:

- `review_trigger`: "more than one **or zero** statements of the same identity are flagged current" —
  unconditional, the exact wording `review-16`'s N1 asked to be dropped, surviving in the one place it
  was not enumerated.
- `necessity`: "L1.current-version defines the current statement as the one with no later statement and
  **requires exactly one** per customer or account" — the pre-amendment reading of a clause that now
  says "at most one ... and none once its latest statement is a withdrawal".

Wrong behavior it names: an L3 projection that correctly produces zero current statements for a
withdrawn record, or for an owner-withdrawn account, trips this type's own review trigger and is handed
to a reviewer as suspect for behaving exactly as the model's derivations require. The harm is review
noise and a traceability claim that misquotes its own clause, not a must-hold failure — every element
that could *fail* the projection now permits zero. That is why this is low and not a repeat of N1.

Minor, same family: `sg.current-version`'s coverage claim opens "The is_current flag, true for exactly
the statement of a customer or account with no later statement and false for every other", the
unamended shape, before the same sentence goes on to state the amendment correctly and the following
sentences add the two bounds. Self-correcting in context; worth a rewrite of the opening clause when
R1 is fixed.

Fix for both: condition the type's `review_trigger` on records with no withdrawal in their own or their
owner's history, and restate its `necessity` to "at most one, exactly one while the record stands".
Cheap, and the wording is already in `L1.current-version` and in the two invariants.

### Recorded, not findings

- **`derivation.kind` for the owner-cascade branch.** `logical.account.is_current` is declared
  `computed_within_entity`, and both `L2-FORMAT.md` and the schema describe that kind as computed "from
  this entity's other statements or attributes" — while branch 3 reads another entity's withdrawal
  history. The schema offers only two kinds, so there is no correct label available, and the normative
  part (the rule text) is explicit, checkable, and names the sibling entity. The dependency is also
  contained: `logical.customer.is_withdrawal` is itself a member of `sg.current-version`, so the group
  is self-sufficient over its own inputs. I am not naming a wrong behavior here. I flag it for the
  coordinator because an L3 Developer who implements the *label* rather than the *rule* partitions by
  `account_number`, never reads `logical.customer`, and lands back on F3 — which is how this defect
  survived two cycles. A sentence in the rule ("this branch reads the sibling customer entity; it is not
  computable from the account's own statements") plus a filed question about the missing cross-entity
  kind would close it.
- **The reporting invariant still has no counterexample naming a non-zero expected row count.**
  Unchanged from `review-16`'s F4 finding, unchanged in its justification: `ce-withdrawn-account-v1.json`'s
  own `blocked_on` explains that the row-producing scenario needs a labeled customer-level constructed
  source that does not exist, the model files a precise question asking for `ce.customer_changes`, and
  both the invariant's `parallel_assumption` and `sg.owner-standing`'s gap say so and point at the
  question. Outside the Developer's authority; flagged for the coordinator as a live `reports: true`
  flag with no witness.
- Not re-litigated, per `review-15`'s and `review-16`'s lists: a withdrawal as a statement row; reading
  `cdc_flag = 'D'` as a withdrawal; the unexercisable `L1.constructed-scenarios` withdrawal exception;
  the five withdrawal-licensed nulls and F1's closure across all three account standing facts.

## Verdict, plainly

It is right this time. F3 is fixed in the form `review-16` prescribed — the cascade is keyed on the
moment the question is asked, the as-of invariant has the owner branch and is the producer, and the
check invariant is now a check of something that exists. N1, N2 and N3 are fixed. The one residue, R1,
is N1's wording surviving on the type, and it can fail nothing. The deferral discipline that has held
through all three cycles is intact: every CDC handoff is still deferred, and the withdrawal branches are
declared unexercised in every group gap, on every attribute, and in every affected invariant's
`parallel_assumption`.

What would have changed my mind: (1) `is_current` coming out true for account 428's 2012 statement, or
the as-of invariant answering at T = 2018 — I traced both from the element text and neither happens;
(2) a construction in which the existence branch denies an account standing at a moment its owner has
standing, or any invariant asserting that the current statement equals the as-of answer at the present
moment, which would make the existence/T asymmetry a must-hold contradiction rather than two clauses
keyed differently — I searched for both and found neither; (3) either `single_current` invariant or
either `is_current` trigger still requiring one current statement where the derivations produce zero —
all four now condition on the absence of a withdrawal.

## Elements I would still reject

None. `type.statement_is_current` I would select with R1 filed as a required follow-up wording fix
rather than reject, since its trigger and necessity misdescribe correct behavior without constraining
it, and every element that constrains the projection now agrees with the derivations.

VERDICT: pass
