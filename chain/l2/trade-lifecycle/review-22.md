# L2 review 22 — trade-lifecycle semantic model (verification of the review-21 rework)

Reviewer: L2 semantic-model reviewer (capable model), 2026-09-17.
Scope: verification review. Eight findings from `review-21.md`, plus the Developer's second stale-reference pass. I re-traced the model from the sources rather than from the rework note, and I re-traced `ce-report-after-withdrawal-v1` through the model as it now stands.

## What I checked

- `sketches/l1-brokerage-intent-v1.md` in full: `L1.deletion-withdraws` (both accepted extensions, including the trade sentence), `L1.lifecycle-mutates-outcome`, `L1.placement-moment` (amended), `L1.attribution-at-placement`, `L1.constructed-scenarios` (withdrawal exception), `L1.hole.deletion-reversal`, `job:trade-lifecycle`'s clause list (note: `L1.omitted-facts-stand` is still not in it).
- `chain/ce/accepted/ce.l1.deletion-withdraws.md`, `ce.l1.withdrawal-reaches-standing.md`; `counterexamples/proposed/ce-report-after-withdrawal-v1.json` (now recording the central finding as VERIFIED AT L2) and `ce-withdrawn-account-v1.json` (its `blocked_on` on the D-only trade case).
- `chain/anchors/sources-v1.json`, `semantic-model-v2.schema.json`, `L2-FORMAT.md`, both developer contracts.
- Every element of `chain/l2/trade-lifecycle/semantic-model.json`: 15 types, `logical.trade` + 15 attributes, 15 handoffs, 16 invariants, 6 groups, 7 holes, 2 questions. Read `statement`/`derivation`/`necessity`/`parallel_assumption`/`review_trigger` per element, not group prose.
- `chain/l2/ownership-history/selected-model.json` (upstream pins) and, via `weave`, `positions`' declared gaps.
- `check trade-lifecycle` → `status: question`, `problems: []`, two questions (the pre-existing reopened-closed-account question; the new `ce.trade_changes` anchor question). `weave trade-lifecycle` → `contradiction: 0`, `named-gap: 13`, `overlap: 3`, `dependency: 7`. Neither new gate rule fires: the model's only `reports: true` invariant (`inv.trade_on_closed_account_reported`) is named by a counterexample, and every closed-hole mention carries its own closure sentence.

Verdict summary: the central finding is genuinely fixed for the case it was raised about, and seven of the eight findings are addressed. But the rework bounded the outcome selector against the trade's *earliest anchored D report* while leaving the placement-fixing selectors bounded only against D-flaggedness, and it widened `inv.every_received_trade_persisted`'s existential to any trade with at least one I/U report *in any position*. For a trade whose earliest anchored report is D, the model therefore reads the post-withdrawal report as the report that places the trade and pins its ownership, while simultaneously refusing to read that same report for the outcome — leaving a claimed row whose non-nullable `status` and `quantity` have no source at all. The asymmetry review-21 failed has not been removed; it has been inverted and moved one ordering over.

## Per-finding verification

### F1 — ADDRESSED. `inv.every_received_trade_persisted`

`necessity` and `parallel_assumption` now both state the decided quantifier ("at least one anchored, fully-coded cdc_flag I or U report, whether or not that trade_number also has one or more cdc_flag D reports"). The three surviving mentions of `L1.hole.deletions` in the file are all historical and self-closing ("the now-closed", "that hole is now closed and this invariant states the decided rule directly", "L1.deletion-withdraws (closing L1.hole.deletions)"), which is why the new dangling-hole gate rule does not fire on them, correctly. The stale wholesale-D-exclusion sentence is gone from `necessity`. Bookkeeping verified.

### F2 — ADDRESSED. `inv.trade_outcome_updates_in_place`

`derived_from` is now `["L1.lifecycle-mutates-outcome", "L1.deletion-withdraws"]`; `sg.outcome.parent_clauses` carries `L1.deletion-withdraws`; the `L1.hole.deletions` deferral sentence is replaced by the decided rule ("a D report supplies no outcome value of its own, so the six outcome facts stand exactly as they last stood at that moment"). The group no longer claims coverage from a clause it does not declare.

### F3 — ADDRESSED for the ordering it was raised about; re-traced.

Re-tracing trade 353232 (received `I` 2017-06-30; constructed `D` at cdc_dsn 1488600; constructed `U` status CNCL, null price/fees/comm/tax at 1488601) through the model as it stands:

- `withdrawn` = true (unchanged, and correctly so — `inv.trade_withdrawn_matches_deletion_report` is still a clean iff over the whole anchored report set).
- All six `sg.outcome` handoffs now carry, in `necessity`, `parallel_assumption` and `review_trigger`, the bound "an anchored I/U report received after the trade's earliest anchored cdc_flag D report is excluded" from `latest_change`. Candidate set for 353232 = {the June `I` row}. So `status` = CMPT and `executed_price`/`fees`/`commission`/`tax` keep their June values.
- The null-erasure is gone. `latest_change` is still per-field, but the offending report is no longer in any field's candidate set, so per-field nullability can no longer launder an overwrite. This is the right shape of fix: it removes the report from the candidate set rather than adding a null-guard that would have needed `L1.omitted-facts-stand`, which this job does not have.
- The hardest check you asked for: **a trade withdrawn and never reported again keeps its last pre-withdrawal outcome.** Verified. The bound is "at or before the trade's earliest anchored D report", not "before the D", and it excludes only reports *after* that position; every pre-withdrawal I/U report stays in the candidate set and the latest of them still wins. `inv.trade_outcome_updates_in_place`'s statement says the same in the positive direction. Nothing is nulled or absent for the I…D case, and nothing about the D report itself now clears the outcome.

The claimed grounds are also honest: the bound is stated as a deferral ("this is a deferral, not a decision that such a report is void or wrong"), the model explicitly declines to report the case for review and says why (`L1.deletion-withdraws` names reporting for customer withdrawals, not for this), and it does not pretend the hole is answered.

### F4 — PARTLY ADDRESSED.

`hole.deletion_reversal.blocks` is now `["sg.outcome", "sg.trade-identity"]`; `sg.outcome`'s `gap` names the hole and states the bound; the hole's `question` names both the assertion flag and the six outcome facts. For those two groups this is exactly the fix review-21 asked for.

It is not complete, and the incompleteness is the same defect in a new place — see **N1**. `sg.trade-shape` and `sg.placement-moment` read a post-withdrawal report as a fact, and neither their `gap` nor `hole.deletion_reversal.blocks` says so. The hole's own rewritten `question` now asserts "this job takes the no-resumption reading on both fronts, symmetrically", which is false of the placement front.

### F5 — NOT FULLY RESOLVED. The cross-job divergence survives for one ordering.

The Developer's position — defer, because nothing licenses reading a post-withdrawal report as resuming *or* as not-resuming — is a defensible reading of the hole and I accept it as a position, not as compliance. `inv.trade_outcome_updates_in_place`'s `parallel_assumption` states the agreement with `positions` explicitly.

But `positions`' current gap (from `weave`) excludes "a pair whose earliest anchored report is cdc_flag D and which has a later anchored non-D report" from both of its claims. `trade-lifecycle` affirmatively claims exactly one row for a trade in that same ordering (`inv.every_received_trade_persisted`), and pins its placement and ownership from the post-D report. So the two jobs still answer the same hole differently — narrower than in review-21 (it was every D-then-later-report ordering; now it is only the D-first ordering) but in the same direction: `positions` withholds, `trade-lifecycle` asserts. `weave` still reports `contradiction: 0`, because it compares declared gaps and not declared claims.

### F6 — ARGUMENT LARGELY ACCEPTED; the substance was in fact fixed. See "Judgment on F6" below.

### F7 — ADDRESSED. The unexercisability is now surfaced as a `questions_for_authority` entry (visible in `check` output), not only confessed in a `parallel_assumption`. That is the field a coordinator reads.

### F8 — ADDRESSED. `type.trade_withdrawn` carries a `note` stating that `mutable` is the schema's residual category and that monotonicity is entailed by the set-existential form ("there is no ordering for it to reset against"), not layered on as policy. That is the reasoning review-21's Q2 arrived at, stated on the element.

### Stale-reference pass — VERIFIED.

`L1.hole.market-order-seen-pending`: 0 occurrences; five sites now cite "L1.placement-moment (amended)" and the `trade_first_seen_late` / `trade_order_type` prose reasons from the clause's own market-order and pending-market-order sentences. `L1.hole.deletions`: 3 occurrences, all historical-with-closure, correctly not flagged. `L1.hole.closed-account-activity`: 0. The three invariant `statement` fields that excluded a trade "unclaimed under inv.trade_held_first_report_unclaimed or L1.hole.deletions" now read "or inv.trade_withdrawn_only_unclaimed" — that is the right substitution, because the exclusion now points at a stated invariant rather than at a question.

## New findings

### N1 — MAJOR — the placement-fixing selectors still read a report received after the withdrawal, so the D-then-I/U ordering is still decided — in the resuming direction

The outcome bound is "at or before the trade's earliest anchored D report in `report_order`". The placement bound is not an ordering bound at all: `handoff.raw.trade_cdc.t_ca_id->owning_account_number`, `handoff.raw.trade_cdc.t_dts->placed_at` and `handoff.raw.trade_cdc.t_tt_id->order_type` each say their `first_encounter_only` scan considers only cdc_flag I or U reports, "**even when it precedes every I/U report in report order**". `inv.trade_placed_at_matches_earliest_report` says the same in checkable form ("smallest (batch_date, cdc_dsn) among I/U rows only"). `inv.every_received_trade_persisted` makes it explicit: a D-having trade's "ownership and placement facts are still pinned from its first-encountered I/U report, never from the D report".

Take a trade whose anchored reports are `D` at cdc_dsn 100 and `U` at 101, with no earlier I/U report:

1. `inv.every_received_trade_persisted` — one anchored, fully-coded I/U report exists, so "exactly one logical.trade row exists for that trade_number". Claimed present, unconditionally as to ordering.
2. `withdrawn` = true.
3. `placed_at`, `owning_account_number`, `order_type`, and hence the whole frozen ownership pin, are taken from the cdc_dsn-101 report — the report received *after* the withdrawal.

Step 3 is reading a post-withdrawal report as a fact, and not a marginal one: it is reading it as the report that brings the trade into being and fixes whose it is. If reading that report's `t_st_id` "would treat it as resuming" — which is `sg.outcome`'s and the hole's own stated ground for excluding it — then reading its `t_ca_id` and `t_dts` as the trade's placement is the stronger version of the same act. The model cannot have it both ways on one row. So the answer to the question you asked me to check hardest is: **yes, an element still decides the D-then-I/U ordering, and it decides it in the resuming direction.** Three handoffs, two invariants, and both groups' prose say so deliberately — these are not leftovers, they are sentences written to cover the case ("whatever its position in report order").

Note that this is not simply my predecessor's F4 restated. Before the rework, the model read post-D reports uniformly: wrong, but coherent. Now it reads them for placement and refuses them for outcome. The asymmetry review-21 failed on is still present, with the two halves swapped.

The declaration defect recurs with it: `sg.trade-shape`'s gap names only `L1.hole.batch-identity`; `sg.placement-moment`'s names four holes, not this one; `hole.deletion_reversal.blocks` omits both groups.

### N2 — MAJOR — the rework leaves a claimed row whose non-nullable outcome attributes have no source

Same trade as N1. The `sg.outcome` candidate set is "anchored I/U reports at or before the trade's earliest anchored D report" — for a D-first trade that set is **empty**. `inv.trade_outcome_updates_in_place` says such a report "updates none of the six outcome facts" and that the facts "stand exactly as they last stood"; there is no last-stood value to stand at. Yet `logical.trade.status` is `nullable: false` and `logical.trade.quantity` is `nullable: false`, and `inv.every_received_trade_persisted` claims the row exists.

So the model, as written, requires a row that cannot be constructed: either `status`/`quantity` are null in violation of their own `nullable: false`, or the row is absent in violation of `inv.every_received_trade_persisted`, and no invariant in the model detects either outcome. This is new this cycle — before the rework such a trade took its status from the post-D report. It is the same failure class as the one just fixed (a nullability question standing in for a what-stands question), arriving from the other side: last cycle nullability excused an erasure, this cycle non-nullability is left unsatisfiable by an exclusion.

`inv.every_received_trade_persisted`'s own `parallel_assumption` shows where the reasoning stopped: it justifies counting the post-D report toward the existential with "it is, since the trade already exists from its earlier I/U report". For the D-first ordering there is no earlier I/U report, so the stated justification does not cover the case the stated quantifier claims.

### N3 — MODERATE — the divergence from `positions` is now exactly this ordering (see F5)

`positions` withholds its row-per-pair claim for an earliest-D-then-non-D pair; `trade-lifecycle` asserts a row for the earliest-D-then-U trade and pins it from the post-D report. Both jobs' prose says they are deferring the same hole in the same way. One of them is not.

### N4 — MINOR — `sg.constructed-scenarios` still carries `gap: "none"` beside a coverage_claim that spends a paragraph explaining that its clause's new exception is unusable here

Non-blocking, and I accept that the schema's `gap` is hole-oriented while this bound is a missing anchor rather than an open hole. But "none" is what `weave` publishes to the coordinator and the sibling jobs, and it reads as "nothing bounds this group". A one-clause pointer ("none; see questions_for_authority on the missing labeled ce.trade_* source") would cost nothing and would stop the group's real limit from being visible only to someone who reads the coverage prose.

## Judgment on the F6 argument

I accept the argument on its merits, with one correction to how the Developer characterised its own work and one residual (N4).

Accepted, and I would have reached the same conclusion independently:

- `inv.trade_not_constructed` states what is true and checkable today, and its `review_trigger` ("sources-v1.json gains a ce.trade_* entry") is the right trip-wire. Its claim is about where trade statements originate, and it is accurate about that.
- It genuinely cannot detect a scenario that writes into `raw.trade_cdc`. Detection needs a field that distinguishes a constructed row from a received one; `raw.trade_cdc` as anchored has none, and `L1.constructed-scenarios` cannot be self-enforcing at L2 against a source whose shape carries no provenance. Inventing a rule that says "no constructed row appears in raw.trade_cdc" would be an unverifiable assertion dressed as an invariant — worse than the honest gap, and exactly the kind of element this chain exists to refuse.
- The fix therefore is an anchor change, which is not this job's to make. A `questions_for_authority` entry naming `ce.trade_changes`, mirroring `ce.account_changes` with its own `provenance` field, is the correct instrument, and the one filed is specific enough to act on (it names the source, the mirror, the field, and the two invariants that cannot otherwise be exercised). `ce-withdrawn-account-v1`'s own `blocked_on` reaches the same conclusion for the account side.

Correction: the claim that `sg.constructed-scenarios` "needed no recompile" understates what was done. The group's `coverage_claim` *was* rewritten, and well: it now states plainly that the withdrawal exception "inverts that inference for this job specifically", that there is no legal way to use it, and that mixing into `raw.trade_cdc` is what a scenario would have to do and what `inv.trade_not_constructed` cannot detect. That is the substance of review-21's F6, and it is present. What the Developer declined to do was change an invariant — which I agree it should not have done.

Residual: `gap: "none"` (N4). Minor, not blocking.

## Elements I would still reject

- `inv.every_received_trade_persisted` — N1, N2. Its existential is unqualified as to where the earliest D sits, and its justification covers only the I-first ordering.
- `inv.trade_placed_at_matches_earliest_report` — N1. "Smallest (batch_date, cdc_dsn) among I/U rows only" takes a post-withdrawal report's time as the placement moment.
- `handoff.raw.trade_cdc.t_dts->logical.trade.placed_at` — N1 ("even when it precedes every I/U report in report order").
- `handoff.raw.trade_cdc.t_ca_id->logical.trade.owning_account_number` — N1. Pins the frozen ownership reference off a post-withdrawal report.
- `handoff.raw.trade_cdc.t_tt_id->logical.trade.order_type` — N1, same scan.
- `hole.deletion_reversal` — its `question` claims the no-resumption reading is taken "on both fronts, symmetrically", which is not true of placement; `blocks` omits `sg.trade-shape` and `sg.placement-moment`.
- `sg.trade-shape` and `sg.placement-moment` — group-level: their `gap` fields do not name the hole that bounds them (not element rejections).

Accepted and sound as written, and better than last cycle: all six `sg.outcome` handoffs, `inv.trade_outcome_updates_in_place`, `type.trade_withdrawn` (including the new note), `logical.trade.withdrawn`, `handoff.raw.trade_cdc.cdc_flag->logical.trade.withdrawn`, `inv.trade_withdrawn_matches_deletion_report`, `inv.trade_withdrawn_only_unclaimed`, `sg.outcome` as a group, `sg.constructed-scenarios`' members and coverage_claim, and both `questions_for_authority` entries.

## What would have changed my mind

A pass, with N4 as non-blocking bookkeeping, if the post-D exclusion had been applied to the *same* report set everywhere on the row instead of to one group. Concretely, any one of:

1. Bound the placement-fixing selectors the way `sg.outcome` is now bounded — `first_encounter_only` over anchored I/U reports **at or before** the trade's earliest anchored D report — and narrow `inv.every_received_trade_persisted`'s existential to match ("at least one anchored, fully-coded I/U report at or before the trade's earliest anchored D report"), with a D-first trade claimed *absent* or *withheld* by a stated invariant, the way `inv.trade_held_first_report_unclaimed` withholds under the other hole. That makes the deferral total, removes N2 outright, and lands on `positions`' side of N3.
2. Or withhold the row for a D-first trade explicitly and carry the ordering up in `questions_for_authority`, which is a deferral rather than a decision.
3. Or, if the Developer believes the D-first trade genuinely is placed at its first I/U report — an arguable reading of "a withdrawal creates nothing", and the reading `L1.constructed-scenarios`' withdrawal exception makes hard to exercise anyway — then say so as a *decision*, drop the `sg.outcome` bound for the same ordering so one report is read consistently, and supply the non-nullable outcome facts from that same report. I would have argued with that choice but I would not have failed it for incoherence.

In every case: `sg.trade-shape` and `sg.placement-moment` in `hole.deletion_reversal.blocks` and in their own `gap`s, and the hole's `question` corrected so it no longer claims a symmetry the model does not have.

What I cannot pass is a row whose placement is taken from a report the same row's outcome group refuses to read, whose non-nullable `status` and `quantity` have no candidate value at all, and which the sibling job declines to claim — with `check` at `problems: []` and `weave` at `contradiction: 0`. That is the review-21 defect with its halves exchanged, and no audit in the model can see it.

VERDICT: fail
