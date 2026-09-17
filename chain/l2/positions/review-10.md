# Review 10 (L2 semantic-model reviewer): job positions

Cycle under review: the recompile of `sg.holding-shape` after the business answered `L1.hole.deletions`
with `L1.deletion-withdraws`, plus the Developer's touch of `sg.no-phantom-positions` on a cache
adjudicator's KEEP. Element-level diff read against `746381a..0b8a6b4`.

## What I checked

- `sketches/l1-brokerage-intent-v1.md` clause by clause for `job:positions`, in particular
  `L1.deletion-withdraws` sentence by sentence and `L1.hole.deletion-reversal`'s standing directive.
- `chain/ce/accepted/ce.l1.deletion-withdraws.md` and `ce.l1.withdrawal-reaches-standing.md`.
- `chain/cache-adjudications.jsonl`: the two positions verdicts for clause `L1.hole.deletions`
  (`sg.holding-shape` invalidate, `sg.no-phantom-positions` keep), read against what was actually built.
- `chain/anchors/sources-v1.json` (`raw.holding_history` fields and identifiers, `cdc_flag`,
  `report_order.applies_to`).
- The model: every element of `sg.holding-shape` and `sg.no-phantom-positions`, the four
  `raw.holding_history` handoffs and their selectors, the `holes` list, `questions_for_authority`.
- Prior `review-1.md` .. `review-9.md` and `change-contract-9.md`.
- Upstreams: `chain/l2/trade-lifecycle/selected-model.json` (what positions consumes today) and
  `chain/l2/trade-lifecycle/semantic-model.json` (what it will consume), plus
  `chain/l2/ownership-history/selected-model.json`.
- `counterexamples/proposed/ce-withdrawn-account-v1.json` and `ce-report-after-withdrawal-v1.json`.
- The received records directly: `raw/generated/tpcdi-sf3-review/Batch{1,2,3}/HoldingHistory.txt`
  and the `-final` fixture.
- `.venv/bin/python scripts/chain_l2.py check positions` -> `status: ok`, zero problems, zero
  questions, six holes carried, `L1.hole.deletions` correctly gone from `holes_carried`.
  `weave positions` -> 0 contradictions, 0 unnamed gaps, 13 named gaps.

I did not run the L3 projection. Finding 3's claim about `ce-withdrawn-account-v1` is from the
received source rows, and the coordinator should re-measure rather than take my reading on faith.

The gate is clean and the model is internally well formed. Every defect below is a semantic one the
gate cannot see.

## Findings

### F1 (blocking) `inv.eligible_holding_report_persisted` -- the narrowing re-commits the error it was ordered to fix

The adjudicator's instruction was exact: "the abstention must narrow from any-`D` to `D`-only and
become a positive rule." The Developer did not narrow to `D`-only. It narrowed to *`D`-only, plus a
second exclusion*: "none of whose cdc_flag D reports is followed by a later non-D report."

Take a pair with reports I (t1), D (t2), U (t3). It has genuine pre-withdrawal history: the brokerage
asserted a holding at t1. `L1.deletion-withdraws` is unambiguous about it -- "a holding or a position
that followed a trade before that trade was withdrawn stands as history, because it records what the
brokerage held at the time, and nothing is recomputed backwards." A row is owed, carrying the t1
quantities. The new statement drops the pair from the claim entirely, because its D report is followed
by a later non-D report.

That is the same species of error as the old any-`D` abstention, one ordering over: a pair whose
standing history the clause protects is dropped from the row claim because of a report that arrived
after it. The narrowing went from any-`D` to (`D`-only OR any-`D`-then-non-`D`), which is strictly
weaker than the `D`-only the adjudicator ruled and than what the clause entails.

**Fix.** Claim exactly one row for any pair with at least one anchored non-`D` report earlier than
every one of its `D` reports. Confine the deferral to the one thing the hole actually reserves:
whether the *post-withdrawal* report may be read into the row's quantities. That is precisely the
shape `trade-lifecycle` adopted -- see F2.

### F2 (blocking) `inv.holding_quantity_updates_in_place` decides the deferred ordering, in the direction `L1.hole.deletion-reversal` forbids

`sg.holding-shape` now asserts that a pair with a `D` report followed by a later non-`D` report "is
`L1.hole.deletion-reversal`'s case, not claimed by either invariant." That is false at the model
level. `inv.holding_quantity_updates_in_place` (group `sg.no-phantom-positions`, selected, untouched
this cycle) says, without any ordering qualification:

> For any (original_trade_number, current_trade_number) pair, a later raw.holding_history report of
> that same pair with cdc_flag I or U replaces before_qty and after_qty with its newly reported values
> on the same row.

For an I, D, U pair that invariant affirmatively *requires* the post-withdrawal U's quantities to be
written onto the row. That is reading a report received after a withdrawal as resuming the record,
which `L1.hole.deletion-reversal` forbids in as many words: "Until answered, no job may treat a report
received after a withdrawal as resuming the record." The `latest_change` selector, which excludes `D`
and takes the latest surviving I/U, produces exactly that behavior today.

The same invariant's statement then closes with "what it means for the holding change's quantities is
`L1.hole.deletions`, not decided here" -- naming a hole L1 closed on 2026-09-17.

So the model both refuses to claim the ordering in one group and decides it, wrongly, in another. The
abstention in `sg.holding-shape` does not defer the question; it conceals a decision another group is
already making.

`trade-lifecycle` shows the row-existence half was avoidable. Its recompiled
`inv.every_received_trade_persisted` keeps the row claimed "whether or not that trade_number also has
one or more anchored cdc_flag D reports", pins `withdrawn` true, and makes it monotonic *because* the
hole forbids resumption; its `sg.trade-identity` gap reserves only whether the flag could ever be
reset. Positions instead deferred row existence and left the behavior unconstrained.

But `trade-lifecycle` did *not* avoid the selector half, and while I was writing this a concurrent
review verified it at L2 and recorded it in `ce-report-after-withdrawal-v1`'s
`expected.under_the_open_hole`: its `latest_change` "ranks anchored I/U reports by (batch_date,
cdc_dsn) with no bound relative to the D, so the post-withdrawal report wins". Positions' own
`latest_change` on `hh_before_qty` and `hh_after_qty` is the identical construction with the identical
missing bound. So this is not a positions-specific slip but one defect now confirmed in two jobs from
one shared selector pattern, and it should be fixed in both with the same words. The one mercy for
positions is that `inv.holding_quantities_present` makes `before_qty` and `after_qty` non-nullable, so
positions cannot suffer the per-field null erasure that the concurrent review found in
`trade-lifecycle`'s nullable outcome attributes -- the post-withdrawal report overwrites the
pre-withdrawal quantities rather than erasing them. That is a smaller wrong, not a different one.

**Fix.** Narrow the invariant to "a later I or U report with no earlier `D` report of the same pair",
add `L1.deletion-withdraws` to its `derived_from`, and state the positive rule its no-reach-back
sentence supplies: an I-then-`D` pair's quantities are its last pre-withdrawal report's values, held
there and not recomputed. Bound only the post-`D` reading on `hole.deletion_reversal`.

### F3 (blocking) `inv.holding_change_absent_for_withdrawn_only_pair` is vacuous, and the counterexample said to exercise it does not

The invariant is a real absence claim, not a tolerance -- it is stated as an existence negation over
the source pair set, so a phantom row fires it. On that narrow point the Developer got it right, and
the model now holds a rule where it previously had an accident of nullability.

But nothing exercises it, including the scenario everyone believes does.
`raw/generated/tpcdi-sf3-review/Batch2/HoldingHistory.txt` line 1 is:

```
I|1488406|353232|372101|5225|0
```

Against the anchor's field order that is `cdc_flag=I`, `cdc_dsn=1488406`, `hh_t_id=353232`,
`hh_h_t_id=372101`, `hh_before_qty=5225`, `hh_after_qty=0`. The pair `(372101, 353232)` **already has a
received I report.** Identical in both `tpcdi-sf3-review` and `tpcdi-sf3-review-final`; the loader's
default batch count is 2, so it is loaded.

`ce-withdrawn-account-v1` adds a `D` row for that same pair at `cdc_dsn 1488501`, and says in its own
note that it echoes the row's last values -- because it is echoing *this* row. So the scenario does not
build a `D`-only pair. It builds an I-then-`D` pair: exactly F1's case, and exactly the case the new
`inv.eligible_holding_report_persisted` claims must have one row.

Three consequences.

1. `inv.holding_change_absent_for_withdrawn_only_pair` has zero witnesses. No `HoldingHistory` row in
   any received batch carries `D` (verified: count 0 in all three batches, both fixtures), and no
   proposed counterexample supplies a `D`-only pair. The invariant is vacuously true everywhere.
2. The model and an accepted-CE-backed counterexample now contradict. `ce-withdrawn-account-v1`'s
   `expected.deletion_only_holding` and its `deterministic_assertion` both require "no
   holding_change exists for the pair (372101, 353232)". The model's new invariant requires exactly
   one. The model is right and the counterexample is wrong -- the clause's no-reach-back sentence
   governs, not its never-held sentence -- but the Developer shipped a new must-hold claim in direct
   conflict with the only fixture that touches the change, and did not notice.
3. `ce-withdrawn-account-v1`'s `observed` line -- "positions produces no holding change for the
   deletion-only pair" -- cannot be a correct measurement. The received I row is a `latest_change`
   candidate on its own, and trade 353232 resolves with a pinned owner (per
   `ce-report-after-withdrawal-v1`), so a row for that pair should already exist in the base projection
   with no scenario loaded at all.

**Fix.** `sg.holding-shape`'s coverage_claim must record that no received record and no proposed
counterexample exercises the `D`-only absence claim, the way `ownership-history/sg.statement-content`
records its withdrawal narrowing as unexercised. Then route a correction of `ce-withdrawn-account-v1`
to the coordinator: it needs a pair carrying no received report, which
`L1.constructed-scenarios`' new withdrawal exception now permits and which its `blocked_on` note
wrongly believes is already satisfied by `(372101, 353232)`.

### F4 (major) three stale `L1.hole.deletions` references survive, including in the group the Developer says it cleaned

The Developer described its `sg.no-phantom-positions` touch as dropping a stale reference to the
now-closed hole. It edited only `gap`. `grep` finds `L1.hole.deletions` still cited three times:

- `logical.holding_change.note`: "L1.hole.deletions is carried because what a cdc_flag D row means for
  a holding change is not resolved."
- `inv.holding_quantity_updates_in_place.statement` (see F2).
- `sg.no-phantom-positions.coverage_claim`: "what a cdc_flag D report means for a holding change's
  quantities is L1.hole.deletions, not decided here" -- and, separately, "the provisional exclusion of
  cdc_flag D reports", an exclusion the clause has now made a rule rather than a provision.

All three name a hole that no longer exists and describe as undecided something `L1.deletion-withdraws`
decides. **Fix.** Restate all three from the clause.

### F5 (major) `sg.no-phantom-positions.gap` puts new substance in the wrong field, from a clause the group does not cite

The new gap text reads "What a D-only pair's quantities are is now decided by `L1.deletion-withdraws`,
not a hole: such a pair contributes no row at all..." That is a positive derivation, not a bound on
coverage, so it belongs in `coverage_claim`; it is asserted from `L1.deletion-withdraws`, which is
absent from the group's `parent_clauses`; and it sits directly beside a `coverage_claim` that still
says the same question is undecided (F4). A group cannot hold both.

This is not a prose change. Under a KEEP the group's substance was not supposed to move, and it moved.
(Also cosmetic: a capital "What" mid-sentence after a semicolon.)

**Fix.** Either take the group to a text-only recompile that restates coverage_claim from the clause
and adds `L1.deletion-withdraws` to `parent_clauses`, or revert the gap to a bound and leave the
derivation to `sg.holding-shape`.

### F6 (major) the `D`/non-`D` partition is undefined against a report held under `L1.unknown-codes`

A report carrying an unanchored `cdc_flag` is held whole under `L1.unknown-codes` and may not be read.
Both changed statements partition reports as `D` / non-`D`. A held report is literally non-`D`. So a
pair with one `D` report and one *later* held report:

- by the statements' letter, is a "`D` report followed by a later non-`D` report" -- routed to
  `hole.deletion_reversal`, which reads the held report as a report that resumes the record, the one
  thing `L1.unknown-codes` forbids;
- by `inv.eligible_holding_report_persisted`'s own `parallel_assumption` -- "that report is neither I,
  U, nor D for this invariant's purposes" -- is a `D`-only pair, and
  `inv.holding_change_absent_for_withdrawn_only_pair` requires its absence.

Two elements of the same model give opposite answers on the same pair. `trade-lifecycle` avoided this
by scoping every one of its new statements to "anchored, fully-coded" reports. Positions did not.

**Fix.** Scope both statements to anchored `cdc_flag` values (I, U, `D`, or null on a historical row)
and say explicitly what a held report does to the `D`-only test.

### F7 (minor) the absence invariant has no non-emptiness guard

"A pair every one of whose raw.holding_history reports carries cdc_flag D" is vacuously true of every
pair the brokerage never reported. `trade-lifecycle`'s twin,
`inv.trade_withdrawn_only_unclaimed`, carries the guard explicitly: "at least one such report, and no
cdc_flag I or U report among them." **Fix.** Mirror it.

### F8 (minor) dangling hole references outside this job, and a mis-stated `blocks`

`hole.deletion_reversal.blocks` lists `sg.no-phantom-positions`, but that group names the ordering only
in its `gap`; under F2 the group in fact *decides* it. Separately, and not this job's to fix:
`chain/anchors/sources-v1.json` still reads `"D": "the record is marked deleted; meaning is
L1.hole.deletions"`. Flagged for the coordinator.

### F9 (minor) the narrowing never asks whether the causing trade was withdrawal-only

`inv.eligible_holding_report_persisted` requires a row whenever the pair's `current_trade_number`
"resolves to a logical.trade row" with all four ownership values non-null, and inspects only the
`holding_history` reports' flags. Under the *currently selected* `trade-lifecycle` model a `D`-only
trade does get a persisted row with a frozen owner and a null outcome (measured in
`ce-withdrawn-account-v1`'s `observed`). `L1.deletion-withdraws` says of a withdrawal-only thing that
"no holding comes into being from it", and `L1.holdings-follow-trade` makes the holding derive from the
trade -- so a holding pair whose current trade is `D`-only must have no row, where the model today would
require one. The recompiled-but-not-yet-selected `trade-lifecycle` closes the gap by accident, through
`inv.trade_withdrawn_only_unclaimed`. **Fix.** State the dependency on that upstream absence claim, in
the invariant or in `sg.holding-shape`'s coverage_claim, rather than relying on an upstream recompile
landing first.

## Answers to the questions asked

**Q1.** No. `inv.eligible_holding_report_persisted` decides something L1 leaves open in one direction
(F2, via its sibling invariant) and refuses something L1 settles in another (F1).
`inv.holding_change_absent_for_withdrawn_only_pair` does restate its clause faithfully. The
`sg.no-phantom-positions` gap asserts a derivation from a clause the group does not cite (F5).

**Q2 (the crux).** The narrowing is correct in one half and wrong in the other, and is not complete.
`inv.eligible_holding_report_persisted` does now claim a row for a pair whose reports are I then a
later `D` -- correct, and the fix the adjudicator ordered. But the Developer added a second exclusion
the adjudicator did not order, which re-drops a pair with pre-withdrawal history followed by a `D` and
then any later report, so the no-reach-back sentence is still violated one ordering over (F1). The new
absence invariant does genuinely hold the absence rather than tolerate it -- it is an existence
negation over the source pair set, so a phantom row fires it -- but it is vacuous: no received record
carries any `D` in `HoldingHistory`, and `ce-withdrawn-account-v1` does not build a `D`-only pair,
because `(372101, 353232)` already has a received I report (F3). `inv.eligible_holding_report_persisted`
is not vacuous as a whole, but its newly added later-withdrawal conjunct -- the entire point of the
recompile -- has no witness in any fixture either.

**Q3.** Partly genuine, partly a decision dressed as one, and it is not the call `trade-lifecycle`
made. For a pair whose *first* report is `D` and is then followed by a non-`D` report, row existence
really does turn on the hole, and excluding it is honest. For a pair with real pre-withdrawal history
(I, `D`, U), the hole reserves only whether the post-withdrawal report may be *read*; that the row
exists carrying its pre-withdrawal quantities is settled by the clause, and excluding it is a decision
(F1). Worse, the exclusion does not even deliver abstention: `inv.holding_quantity_updates_in_place`
still requires the post-withdrawal U's quantities to be applied, so the model answers the hole in the
forbidden resumption direction while claiming to abstain (F2). `trade-lifecycle` handled row existence
the right way -- it kept the row claimed and made `withdrawn` monotonic precisely because the hole
forbids resumption -- but a concurrent review has now verified at L2 that its `latest_change` selector
carries no bound relative to the `D` either, so the post-withdrawal report wins its outcome too. That
half of the defect is shared, not positions' alone. And `ce-report-after-withdrawal-v1`'s fixture
carries only `trade_cdc` rows, no `holding_history` pair, so despite its `why_constructed` claiming to
run the case for both jobs, positions' excluded ordering has no test surface at all.

**Q4.** I agree with the KEEP on behavior: the clause confirms what the group produces, the quantities
and the sums are untouched, and the clause's new requirements land on row existence. I do not agree
that the Developer's touch was a stale-reference correction. It edited `gap` only, added new
substantive derivation there from an uncited clause, left the group's `coverage_claim` contradicting
its own new gap, and left two of the three stale `L1.hole.deletions` citations in place -- one of them
in a selected deterministic invariant of this very group whose text still calls the `D` exclusion
provisional (F2, F4, F5). The KEEP was right that no behavior needed recompiling; it could not
authorize a group whose member names a closed hole as the reason a behavior is undecided. The group
needed a text-only recompile, and got a substantive edit instead.

**Q5.** Under-closed, and in the one field that mattered. `questions_for_authority` is correctly `[]`
and `hole.deletions` is correctly removed, and `hole.deletion_reversal` is correctly opened with the
right L1 parent -- the bookkeeping is right. But the *substance* of the old question survives
unanswered in `inv.holding_quantity_updates_in_place`, which still says the quantities question is
`L1.hole.deletions`' and "not decided here", and in `sg.no-phantom-positions.coverage_claim`, which
still calls the `D` exclusion provisional. The business answered exactly that: the pre-withdrawal
holding stands as history and nothing is recomputed backwards, which fixes the quantities at the last
pre-withdrawal report's values. The Developer deleted the hole element that carried the question and
left the question itself standing in two selected elements. In the other direction it over-closed:
it widened the abstention past the `D`-only the answer and the adjudicator both specified (F1).

**Q6.** One invariant is vacuous and the fixture is worse than absent -- it is wrong. No received
`HoldingHistory` row in any batch of either fixture carries `D`, so
`inv.holding_change_absent_for_withdrawn_only_pair` has no received witness; that much is expected and
the accepted CE says so. What is not expected is that the constructed scenario does not supply one
either: `(372101, 353232)` carries `I|1488406|353232|372101|5225|0` in `Batch2`, so the scenario's
added `D` makes it I-then-`D`. So the scenario does not test what the new invariant claims, and its
stated expectation ("no holding_change exists for the pair") is now a violation of the model's other
new must-hold claim. No invariant was *weakened* for lack of a received record -- both new claims are
stated at full strength, which is to the Developer's credit -- but neither is exercised, and nothing in
the model or the group says so, unlike `ownership-history`, which records its withdrawal narrowing as
unexercised.

## Rejected element ids

- `inv.eligible_holding_report_persisted`
- `inv.holding_change_absent_for_withdrawn_only_pair`
- `inv.holding_quantity_updates_in_place`
- `sg.holding-shape`
- `sg.no-phantom-positions`

## What would have changed my mind

A pass on all of F1, F2, F3 together:

1. `inv.eligible_holding_report_persisted` claiming exactly one row for any pair with an anchored
   non-`D` report earlier than every `D` report, with the exclusion confined to a pair whose earliest
   anchored report is `D`.
2. `inv.holding_quantity_updates_in_place` narrowed so no report after a `D` report of the same pair
   is a "later report", with the no-reach-back sentence cited for what the row then carries -- the
   monotonic-`withdrawn` move `trade-lifecycle` made.
3. `sg.holding-shape` recording that no received record and no proposed counterexample exercises the
   `D`-only absence claim, with the `ce-withdrawn-account-v1` conflict raised rather than shipped past.

F4 through F9 alone would have been a pass with prescribed corrections.

VERDICT: fail
