# Review 11 (L2 semantic-model reviewer): job positions

Verification of the rework demanded by `review-10`. Element-level diff read against `0b8a6b4..HEAD`
(the model's only change in that range is `968a7a2`). Nine findings checked one at a time, plus
everything the rework introduced.

## What I checked, and what I measured rather than read

- `sketches/l1-brokerage-intent-v1.md`: `L1.deletion-withdraws` sentence by sentence,
  `L1.unknown-codes` sentence by sentence, `L1.hole.deletion-reversal`, `L1.hole.batch-identity`.
- `chain/ce/accepted/ce.l1.deletion-withdraws.md`, `ce.l1.withdrawal-reaches-standing.md`,
  `counterexamples/proposed/ce-withdrawn-account-v1.json`.
- `chain/anchors/sources-v1.json`: `raw.holding_history`'s declared field order,
  `trade_code_meanings.cdc_flag` (the `D` line now reads `L1.deletion-withdraws`, so `review-10`'s
  F8 anchor complaint is discharged), `report_order.applies_to`.
- `chain/anchors/L2-FORMAT.md` and `DEVELOPER-CONTRACT-L1-L2.md`, including the new
  "a review finding is a claim, not an authority" section.
- Upstreams: `chain/l2/ownership-history/selected-model.json`,
  `chain/l2/trade-lifecycle/selected-model.json` (which carries no `withdrawn` attribute at all --
  F9's premise still holds).
- `.venv/bin/python scripts/chain_l2.py check positions` -> `status: ok`, zero problems, zero
  questions, six holes carried, no dangling hole reference (`L1.hole.deletions` now appears zero
  times in the model). `weave positions` -> 0 contradictions, 0 unnamed gaps, 13 named gaps.
- The fixture, loaded. `scripts/chain_load.load_digen('raw/generated/tpcdi-sf3-review', 2)` plus
  `ce-withdrawn-account-v1`'s two `holding_history` additions, inserted through the same column
  order `chain_load.DDL` declares.

### The predecessor's F3 was wrong, and I did not inherit it

`raw.holding_history` is declared `(cdc_flag, cdc_dsn, hh_h_t_id, hh_t_id, hh_before_qty,
hh_after_qty, batch_date)` in both `sources-v1.json` and `chain_load.DDL`, and Batch1 historical rows
load as `(NULL, NULL, hh_h_t_id, hh_t_id, ...)`. So `I|1488406|353232|372101|5225|0` is
`hh_h_t_id=353232, hh_t_id=372101`. `review-10` read those two fields in the reverse order and
concluded the received `I` sat on `(372101, 353232)`. It does not. Measured, grouping by
`(hh_h_t_id, hh_t_id)` on the loaded scenario:

```
  (353232, 353232)  1 report   [null]            historical, Batch1
  (353232, 372101)  2 reports  [I, D]            I cdc_dsn 1488406 (received), D 1488502 (scenario)
  (372101, 353232)  1 report   [D]               D cdc_dsn 1488501 (scenario), D-only
```

`cdc_flag = 'D'` count over the whole table with the scenario loaded: 2, both of them the scenario's.
So: no received `D` anywhere, and the absence invariant has a genuine `D`-only witness. Both
invariants are exercised on this fixture. `review-10`'s F3 is withdrawn in its first half; its second
half (no fixture witnessed pre-withdrawal history followed by a withdrawal) was right and the
coordinator fixed it by adding `cdc_dsn 1488502`.

## Per-finding verdict

**F1 -- addressed.** `inv.eligible_holding_report_persisted` now claims exactly one row for any pair
with at least one anchored non-`D` report earlier than every anchored `D` report of that pair,
"equivalently, whose earliest anchored report is not D". The second exclusion is gone. An I,D,U pair
is claimed and carries its pre-withdrawal history, which is what the no-reach-back sentence entails.
The three-way split is now total and disjoint over pairs with at least one anchored report: earliest
anchored report non-`D` -> exactly one row; all anchored reports `D` -> no row
(`inv.holding_change_absent_for_withdrawn_only_pair`); earliest anchored report `D` with a later
anchored non-`D` report -> `L1.hole.deletion-reversal`, claimed by neither. That is the exact shape
the adjudicator ordered and `review-10` said would change its mind.

**F2 -- addressed in substance, with one element left behind (see N1).**
`inv.holding_quantity_updates_in_place` now lets an I/U report update only when the pair has no
anchored `D` earlier than it, freezes the row at the values of the last anchored report before the
pair's earliest `D`, cites the no-reach-back sentence for the freeze rather than a hole, leaves the
post-`D` reading to `L1.hole.deletion-reversal`, and carries `L1.deletion-withdraws` in
`derived_from`. `sg.no-phantom-positions.parent_clauses` carries the clause too, so the citation is
legal under the gate's subset rule. The invariant's `review_trigger` now names the wrong projection
directly -- "a row is found whose before_qty or after_qty reflects any anchored report later than the
pair's earliest anchored D report" -- which is what makes the shared `latest_change` defect
detectable rather than silent. The model no longer decides the hole in the forbidden direction.

**F4 -- addressed.** Zero occurrences of `L1.hole.deletions` in the model.
`logical.holding_change.note` now cites `hole.deletion-reversal` for the one undecided thing and says
the rest is decided by `L1.deletion-withdraws`; the invariant statement is restated; the
`sg.no-phantom-positions` coverage_claim no longer calls the `D` exclusion provisional. The one
surviving "provisional" in the file is in that invariant's `necessity`, reading "a rule the model
holds, not a provisional filter" -- a correct use, not a stale one.

**F5 -- addressed, and better than the minimum.** `sg.no-phantom-positions.gap` is now a pure list of
hole bounds with no positive derivation and no stray capital. The derivation moved into
`coverage_claim`, and `L1.deletion-withdraws` was added to `parent_clauses`, so the group asserts
from a clause it cites. The coverage_claim and the gap no longer contradict each other.

**F6 -- addressed, and correctly (my reasoning below).** Both changed statements and the absence
invariant are scoped to anchored reports, and all three now say the same thing about a held report:
it counts toward neither side of the `D`/non-`D` partition. The two elements that gave opposite
answers on the same pair now agree. No question was filed, and none was needed.

**F7 -- addressed.** `inv.holding_change_absent_for_withdrawn_only_pair` now requires "at least one
anchored raw.holding_history report", and its `necessity` explains why a pair with zero reports is
not evidence for or against the rule. This mirrors `trade-lifecycle`'s
`inv.trade_withdrawn_only_unclaimed`.

**F8 -- addressed.** `hole.deletion_reversal.blocks` still lists `sg.no-phantom-positions`, and that
is now correct rather than mis-stated: the group genuinely names the bound in its gap and the freeze
rule lives in its member invariant. The anchor line F8 flagged for the coordinator has been fixed.

**F9 -- addressed as an open assumption, which is the right shape.**
`inv.eligible_holding_report_persisted`'s `parallel_assumption` states in as many words that the model
does not condition row existence on whether the causing trade is withdrawal-only, names the two
clauses that would entail it, and declines to read `trade-lifecycle`'s unselected working model. The
`review_trigger` fires when "trade-lifecycle selects an absence rule for a D-only trade and this
invariant has not yet been revisited for it", and `sg.holding-shape.coverage_claim` repeats the
assumption. I checked the selected upstream: it carries no `withdrawn` attribute and no absence rule,
so the dependency is real and stating it beats either guessing or reading an unselected model.

**The coverage claim -- addressed, and it now matches the fixture.** It records that no received row
carries `D`, then names `(353232, 372101)` as the received-I-then-scenario-D witness for
`inv.eligible_holding_report_persisted` and `(372101, 353232)` as the `D`-only witness for
`inv.holding_change_absent_for_withdrawn_only_pair`, and says explicitly that these are two distinct
pairs rather than two readings of one. Every part of that matches what I measured. The Developer
ended up right about its own model over a review that was wrong about the fixture, which is exactly
what the new contract section asks for -- though it arrived there only after being shown the
measurement, and the earlier deference is why that section exists.

## The two things I was asked to check hardest

### Is the ordering well defined from the anchored sources?

Yes, for the predicate the rules actually use. The test is not "which report is latest" but "is the
pair's earliest anchored report a `D`", and that is decidable from the anchors:

- Historical rows carry no `cdc_flag` at all, so a historical row is never `D`; and
  `report_order.applies_to` states that historical `raw.holding_history` rows "have no cdc columns
  and precede all incremental rows". So any pair with a historical row has a non-`D` earliest
  anchored report, with no tie-break required. Measured: 0 pairs carry more than one historical row,
  and 0 pairs mix historical and incremental rows.
- Incremental rows carry `(batch_date, cdc_dsn)`, which `report_order.order_by` anchors. Measured: 0
  duplicate `(pair, batch_date, cdc_dsn)` triples, and `cdc_dsn` is globally unique across all
  362,562 loaded rows. On the scenario's own witness pair the two reports share a `batch_date` and
  are separated by `cdc_dsn` (1488406 < 1488502), so the witness is ordered by the anchored key and
  not by luck.
- The residual ambiguity -- several reports of one pair tying under `report_order` -- can only affect
  *which* candidate supplies the quantities, never whether the earliest anchored report is a `D`,
  because a tie among historical rows is a tie among non-`D` reports.
  `inv.holding_quantity_updates_in_place`'s `parallel_assumption` already routes that tie to
  `L1.hole.batch-identity`.

So this is not a rule resting on an order the sources do not establish. It rests on `applies_to`,
which the anchors now state for holding-change reports directly. One bookkeeping consequence went
unrecorded, which is N2.

### Is a held report genuinely inert to the `D`/non-`D` partition?

Yes, and it is forced rather than convenient. The partition is a function of `cdc_flag`, and
`L1.unknown-codes` says a held report may not be read at all beyond its place in the order: "nothing
else about it may be read". So the job cannot know whether a held report is a `D` or a non-`D`, and it
may not default either way -- which is exactly "counts toward neither side". The second half comes
from the clause's own last sentence: a held report "changes nothing and creates nothing", so it cannot
bring a row into being, and it cannot supply the anchored non-`D` report the row claim requires.

Does "a held report keeps its place in the order of reports" bear on "earlier than every anchored
`D`"? No. That predicate quantifies over anchored reports only, so where a held report sits between
them changes nothing about whether some anchored non-`D` precedes every anchored `D`. Order-place
matters only when a report is being *selected to supply a fact*, and a held report supplies none. The
one place the order sentence does bite is a pair known only through held reports, which is N3.

I checked the awkward case the other way too. A pair with one `D` and one later held report is now
claimed `D`-only and its absence asserted, even though the held report might turn out to have been an
`I`. That is right, not a gamble: under `L1.unknown-codes` the held report creates nothing, so no
holding comes into being, and `inv.unknown_codes_held` reports the row so the business sees it. The
model says both halves.

## New findings (prescribed corrections, none blocking)

### N1 (major) the two quantity handoffs did not receive F2's bound

`inv.holding_quantity_updates_in_place` now forbids reading any report after a pair's earliest
anchored `D`. The two handoffs that perform the reading do not say so. Both
`raw.holding_history.hh_before_qty -> before_qty` and `hh_after_qty -> after_qty` keep
`selector: latest_change` with a `parallel_assumption` that still reads "as of the latest report of
the same holding change", cite only `L1.holdings-follow-trade` and `L1.no-phantom-positions`, and name
the `L1.unknown-codes` bound on the candidate set while saying nothing about the `D` bound.
`review-10`'s F2 named the selector as well as the invariant, and `selector` has no fixed vocabulary
in `L2-FORMAT.md` -- its meaning is whatever this model's prose gives it.

This is not a re-commission of the error: `sg.no-phantom-positions.coverage_claim` states the freeze,
the invariant states it as a rule, and the `review_trigger` catches a projection that ignores it. It
is an element whose own text is looser than the group it belongs to. **Fix.** Add
`L1.deletion-withdraws` to both handoffs' `derived_from` (legal now that the group cites it) and say
in each `parallel_assumption` that the latest candidate is the pair's last anchored report before its
earliest anchored `D`, with the post-`D` reading bounded by `L1.hole.deletion-reversal`.

### N2 (major) `sg.holding-shape` now rests on `report_order` and does not name the bound

Row existence in `sg.holding-shape` newly depends on report ordering; before this rework the group's
claims were flag-set claims with no ordering in them. Every other group in this model that rests on
`report_order` names `L1.hole.batch-identity` in its gap (`sg.holding-attribution`,
`sg.no-phantom-positions`), and `hole.batch_identity.question` enumerates the dependent selectors by
name. Neither was updated: `sg.holding-shape.gap` names only `L1.hole.deletion-reversal`, and
`hole.batch_identity.blocks` still lists only `sg.holding-attribution` and `sg.no-phantom-positions`.
A reader of `sg.holding-shape` alone cannot see that its row claim rests on file production order.
**Fix.** Add `L1.hole.batch-identity` to `sg.holding-shape.gap`, add `sg.holding-shape` to
`hole.batch_identity.blocks`, and extend that hole's question to name the earliest-anchored-report
test alongside the selectors it already lists.

### N3 (minor) a pair known only through held reports is claimed by neither invariant

With F7's guard added and F6's inertness rule stated, a pair all of whose reports are held has zero
anchored reports, so `inv.eligible_holding_report_persisted` does not claim it (no anchored non-`D`
report) and `inv.holding_change_absent_for_withdrawn_only_pair` does not claim it (no anchored report
at all). Row existence for it is unstated. `L1.unknown-codes` settles it: such a pair "is not yet
known to the job" and a held report "creates nothing", so it has no row. **Fix.** Either claim that
absence from `L1.unknown-codes` in `sg.unknown-codes`, or say in `sg.holding-shape.coverage_claim`
why the case is left to `inv.unknown_codes_held`'s report alone.

### N4 (minor, partly the coordinator's) a claimed withdrawn pair carries no marker

`L1.deletion-withdraws`' as-of paragraph opens on "a trade **or a holding**" and then states the
reading only for a trade: it "keeps its record and is marked withdrawn, it is not among the trades the
brokerage asserts". `trade-lifecycle` took that literally and pins `withdrawn` true, monotonic.
Positions now claims the I-then-`D` pair's row -- correctly -- and says nothing about whether that
holding is among the ones the brokerage asserts; it keeps contributing to both position sums with no
marker distinguishing it. `ce-withdrawn-account-v1`'s `later_withdrawal_pair` puts the marking
question under `L1.hole.deletion-reversal`, which is arguably the fixture's reading rather than the
clause's: the hole is about a report received *after* a withdrawal, not about the withdrawal itself.
The clause's "stands as history" sentence does settle that the quantities keep contributing, so
nothing the model produces is wrong. What is missing is the sentence saying which reading it takes.
**Fix.** State it in `sg.holding-shape.coverage_claim` -- either that the marked-withdrawn consequent
names trades only, or that the holding-side marker is the coordinator's to route -- rather than
leaving the clause's own antecedent unanswered.

### N5 (cosmetic) two wordings in `inv.holding_quantity_updates_in_place`

"Once a pair has an anchored cdc_flag D report, no anchored report of that pair after **that** D
report" is ambiguous when a pair has two `D` reports; the next clause disambiguates it as the earliest
`D`, so make the first say so too. And the statement's "a report held under L1.unknown-codes is not a
'later report' under this invariant at all" is looser than the same element's `parallel_assumption`,
which gets it exactly right ("neither a freezing D nor a resuming I/U"); the same slackness appears in
`inv.eligible_holding_report_persisted`'s "neither the pair's earliest nor its latest report", which
sits awkwardly beside the clause's own "keeps its place in the order of reports". Use the
parallel_assumption's formulation in both statements: a held report keeps its place in the order and
supplies no flag and no fact, so it lands on neither side of the partition.

## Rejected element ids

None. Every element `review-10` rejected is now derivable from the clause text it cites:

- `inv.eligible_holding_report_persisted` -- accept, with N2's gap correction owed by its group.
- `inv.holding_change_absent_for_withdrawn_only_pair` -- accept; witnessed, guarded, and a rule
  rather than an accident of nullability.
- `inv.holding_quantity_updates_in_place` -- accept, with N5's wording owed.
- `sg.holding-shape` -- accept, with N2 and N4 owed.
- `sg.no-phantom-positions` -- accept, with N1 owed on its two quantity handoffs.

## What would have changed my mind

Any one of these would have been a fail:

1. The earliest-anchored-`D` test resting on an order the anchors do not establish. If
   `report_order.applies_to` had not been extended to holding-change reports, or if the fixture had
   shown a pair whose `D` and non-`D` reports tie under `(batch_date, cdc_dsn)`, the rework would have
   replaced an honest abstention with a rule that cannot be evaluated -- worse than what it replaced.
   I measured for the tie and found none.
2. The held-report resolution going the other way -- treating a held report as non-`D` because it is
   "not D", which is reading the flag the clause forbids reading, or letting the two invariants
   disagree about it again as they did before.
3. The coverage claim still naming `(372101, 353232)` as the pair with the received `I`. That claim
   is checkable with one query, it was put into the model once already after the Developer had been
   shown the measurement, and shipping it twice would have been a fail on its own regardless of the
   nine findings.
4. `inv.holding_quantity_updates_in_place` still calling the quantities question a hole's, or the
   `latest_change` selector still affirmatively requiring a post-withdrawal report to be applied. N1
   is the residue of that defect in the handoffs' own prose; had the invariant not been fixed, or had
   its `review_trigger` not named the wrong projection, the residue would have been the whole defect
   and this would be a fail.

VERDICT: pass
