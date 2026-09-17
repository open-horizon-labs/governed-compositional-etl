# L2 review 21 — trade-lifecycle semantic model

Reviewer: L2 semantic-model reviewer (capable model), 2026-09-17.
Model sha256 under review: as committed at review time (`review.json` records `040535...c7f6` from review 20; re-hash before selecting).
Scope: the `L1.deletion-withdraws` recompile — `sg.trade-shape`, `sg.trade-identity`, `sg.placement-moment` recompiled, `sg.outcome` kept with a prose-only `coverage_claim` change.

## What I checked

- `sketches/l1-brokerage-intent-v1.md` in full: `L1.deletion-withdraws` (both accepted extensions), `L1.current-version`, `L1.constructed-scenarios` (withdrawal exception), `L1.hole.deletion-reversal`, and `job:trade-lifecycle`'s clause list and feedback.
- `chain/ce/accepted/ce.l1.deletion-withdraws.md` and `ce.l1.withdrawal-reaches-standing.md`, including the latter's deterministic assertion.
- `chain/anchors/sources-v1.json` (`raw.trade_cdc` fields, `trade_code_meanings.cdc_flag`, `report_order`, the full list of anchored sources) and `chain/anchors/semantic-model-v2.schema.json` (`selector` is free text, so `any_anchored_d_flagged_report` is schema-legal).
- Every element of `chain/l2/trade-lifecycle/semantic-model.json`: 15 types, `logical.trade` and its 15 attributes, 15 handoffs, 16 invariants, 6 groups, 7 holes, 1 question. Read each changed element's `statement`/`derivation`, `derived_from`, `necessity`, `parallel_assumption` and `review_trigger` separately, not just the group prose.
- `chain/l2/ownership-history/selected-model.json` (upstream pins) and, via `weave`, the sibling `positions` model's declared gaps.
- `counterexamples/proposed/ce-report-after-withdrawal-v1.json` against the model's actual selectors.
- `.venv/bin/python scripts/chain_l2.py check trade-lifecycle` → `status: question` (the pre-existing reopened-closed-account question; no `problems`). `weave trade-lifecycle` → `contradiction: 0`, `named-gap: 13`.

Verdict summary: the withdrawal *marking* is derived correctly and honestly. What fails is the coherence between the marking and the outcome selector, and two changed elements whose own supporting fields still assert the pre-change rule and cite a closed hole.

## Findings

### F1 — MAJOR — `inv.every_received_trade_persisted`: `statement` was rewritten, `necessity` and `parallel_assumption` were not

The `statement` correctly claims both directions. But the element's own `parallel_assumption` still reads:

> "`L1.hole.deletions` bounds what a cdc_flag D report means for a trade's persistence ... so this invariant is quantified only over trade_numbers none of whose received raw.trade_cdc reports carries cdc_flag D at all, leaving a trade_number with any D report entirely to that hole, not merely excluding the D-flagged report itself from an otherwise-qualifying trade."

and `necessity` still contains:

> "every trade_number that has at least one received raw.trade_cdc report with fully anchored codes and no cdc_flag D, and whose earliest report is not itself held, must appear as exactly one logical.trade row; a trade_number with any cdc_flag D report is `L1.hole.deletions`' case and is not claimed here."

before contradicting itself four sentences later. `L1.hole.deletions` was closed on 2026-09-17. So the invariant's quantifier is stated two ways in two fields, and the stale reading is the *wholesale D-exclusion* that produced the very bug this cycle fixed. An L3 audit author who implements the `parallel_assumption`'s quantifier — which is the field that tells them what the check may assume — reinstates the defect while the `statement` reads as if it were fixed.

Fix: delete the stale sentence from `necessity`; rewrite `parallel_assumption` to state the decided quantifier (at least one anchored, fully-coded I/U report, D-having or not) and to name `L1.hole.deletion-reversal`, not `L1.hole.deletions`, as the only remaining bound.

### F2 — MAJOR — `inv.trade_outcome_updates_in_place` still defers to a closed hole, and its `derived_from` omits the deciding clause

Its `statement` says:

> "A report with cdc_flag D is not a later report under this invariant: what it means for the trade's outcome is `L1.hole.deletions`, not decided here."

Meanwhile `sg.outcome`'s new `coverage_claim` says the opposite — "`L1.deletion-withdraws` now decides what this means". The group claims a decision; the group's only invariant claims a deferral to a hole that no longer exists. `derived_from` is still `["L1.lifecycle-mutates-outcome"]` alone, so the clause the coverage now reasons from is not declared on any element of the group, and `sg.outcome.parent_clauses` does not list it either. `check` cannot catch this because it only prints declared parents; nothing cross-checks a `coverage_claim`'s cited clauses against them.

Fix: replace the `L1.hole.deletions` sentence with the decided rule (a D report supplies no outcome value and the outcome fields stand as they last stood); add `L1.deletion-withdraws` to the invariant's `derived_from` and to `sg.outcome.parent_clauses`.

### F3 — MAJOR — the prediction in `ce-report-after-withdrawal-v1` HOLDS, and is worse than predicted

Traced through the model as written, for trade 353232 (existing `I` at 2017-06-30; constructed `D` at `cdc_dsn` 1488600; constructed `U` status CNCL at `cdc_dsn` 1488601):

- `handoff.raw.trade_cdc.cdc_flag->logical.trade.withdrawn`, selector `any_anchored_d_flagged_report`, and `logical.trade.withdrawn`'s `derivation.rule` ("true when at least one anchored, fully-coded report ... carries cdc_flag D") → **withdrawn = true**.
- `inv.every_received_trade_persisted` claims **exactly one row**, unqualified as to where the D sits in report order.
- The six `sg.outcome` handoffs carry selector `latest_change` with candidate set "I- and U-flagged reports" ordered by `trade_code_meanings.report_order` `(batch_date, cdc_dsn)`. Nothing in the handoffs, in `inv.trade_outcome_updates_in_place`, or in `sg.outcome`'s coverage restricts that set relative to the trade's earliest D report. `cdc_dsn` 1488601 > 1488600 > the June I row → **status = CNCL**.
- No invariant in the model relates `withdrawn` to any `sg.outcome` attribute.

So 353232 comes out `withdrawn = true, status = CNCL`, with every audit at zero. The prediction holds, and `ce-report-after-withdrawal-v1` should be updated from UNVERIFIED PREDICTION to verified-against-L2, with the L3 re-projection run as confirmation rather than as discovery.

It is also sharper than the CE anticipated. `latest_change` is per-field, and `executed_price`, `fees`, `commission` and `tax` are `nullable: true` on `logical.trade`. The constructed `U` row carries `t_trade_price`, `t_chrg`, `t_comm`, `t_tax` all null. So the post-withdrawal report does not merely set a fresh status: it **overwrites the withdrawn trade's executed price, fees, commission and tax with nulls**, destroying the CMPT-era outcome the clause says "stands as history". Nullability is again silently excusing a derivation — the same failure mode as the `L1.omitted-facts-stand` finding two loops ago, and note that `L1.omitted-facts-stand` is not even in `job:trade-lifecycle`'s clause list, so this job has no clause licensing a per-field null overwrite. `L1.lifecycle-mutates-outcome` says a later report "updates the outcome"; replacing a stated value with nothing is a decision, not a restatement.

This is a finding about the model's coherence *and* about the clause. `L1.deletion-withdraws` says "everything that already followed from it stands as history" and "it is not among the trades the brokerage asserts". A row marked withdrawn while carrying a status and nulls taken from a report received *after* the withdrawal satisfies neither sentence in spirit, and the combination is not a reading anyone chose.

### F4 — MAJOR — `hole.deletion_reversal` bounds two derivations and is declared against only one

`hole.deletion_reversal.blocks` is `["sg.trade-identity"]`. `sg.trade-identity`'s `gap` names it. `sg.outcome`'s `gap` names only `L1.hole.batch-identity`. But the hole's standing instruction — "no job may treat a report received after a withdrawal as resuming the record" — constrains `latest_change`'s candidate set exactly as much as it constrains `withdrawn`'s monotonicity. Reading a post-withdrawal `U` report's status onto the row *is* treating it as resuming, in the only way this job can express resuming.

The hole's own `question` text compounds this: it frames the resolution solely as "does the trade resume being asserted (withdrawn reset to false)". That phrasing makes the flag the whole of the question and hides that the outcome fields already answer it the other way.

Fix: add `sg.outcome` to `hole.deletion_reversal.blocks`; name `L1.hole.deletion-reversal` in `sg.outcome`'s `gap`; rewrite the hole's `question` so it names both derivations; and bound both the same way — either restrict `latest_change`'s candidate set to anchored I/U reports at or before the trade's earliest anchored D report in `report_order`, or withhold the row for such a trade the way `inv.trade_held_first_report_unclaimed` withholds under the other hole, or report it for review using the mechanism `L1.closed-account-activity` introduced and `L1.deletion-withdraws` already reuses for customer withdrawals. Any of the three is defensible. Bounding one derivation and not the other is not.

### F5 — MAJOR — the two jobs now answer `L1.hole.deletion-reversal` differently

From `weave`, `positions`' `sg.holding-shape` gap:

> "`L1.hole.deletion-reversal` bounds this group's row-per-pair claim for a pair with a cdc_flag D report followed by a later non-D report: what such a report means is undecided, so that ordering is excluded from both `inv.eligible_holding_report_persisted` and `inv.holding_change_absent_for_withdrawn_only_pair`."

`positions` excludes the ordering from its claims. `trade-lifecycle` affirmatively claims a row for it (F1's `statement`) and applies the later report's outcome to it (F3). The chain therefore behaves as `ce.l1.deletion-withdraws` described before the answer: two jobs disagreeing about what a deletion means while every audit passes. `weave` reports `contradiction: 0` because it compares declared gaps, not declared claims, so this is invisible to the harness.

### F6 — MODERATE — `sg.constructed-scenarios` was not recompiled, and its `gap: "none"` is no longer true

`L1.constructed-scenarios` was amended this cycle with the withdrawal exception, and `job:trade-lifecycle` lists that clause. `sg.constructed-scenarios` was left untouched: `parent_clauses` unchanged, `gap: "none"`, and a `coverage_claim` reasoning that because "`sources-v1.json` anchors no labeled constructed source for trades (only `ce.account_changes` exists)", this job "therefore has no handoff that could mix an unlabeled constructed fact into the trade entity". I confirmed against `sources-v1.json`: `ce.account_changes` is the only `ce.*` source anchored.

After the amendment that inference runs backwards. The absence of a labeled constructed trade source no longer means safety; it means the new exception cannot be used legally for this job at all. And the practical consequence is already visible: `ce-report-after-withdrawal-v1`'s fixture injects its `D` and `U` rows under `raw_additions.trade_cdc` — directly into a *received* source. That is a constructed scenario mixed into the received records, which `L1.constructed-scenarios` exists to forbid, and `inv.trade_not_constructed` is *satisfied by* the mixing rather than able to detect it, since it only claims that every trade statement originates from `raw.trade_cdc`, `raw.trade_history`, or upstream statements.

Fix: set `sg.constructed-scenarios`' gap to name this, add `L1.constructed-scenarios`' withdrawal exception to the reasoning, and add a `questions_for_authority` entry (or anchor request) for a labeled `ce.trade_changes` constructed source with a `provenance` field, mirroring `ce.account_changes`. Without it, neither `inv.trade_withdrawn_only_unclaimed` nor the withdrawn branch of `inv.every_received_trade_persisted` can ever be exercised legally.

### F7 — MINOR — the new withdrawal invariants have no legal test surface, and only a `parallel_assumption` says so

`inv.trade_withdrawn_only_unclaimed` is vacuously satisfied today: no received record carries `D` anywhere, so no `D`-only `trade_number` exists. Its own `parallel_assumption` admits this. I checked specifically for the failure mode you asked about and **did not find it**: no invariant was weakened to fit the missing fixture. `inv.trade_withdrawn_only_unclaimed` is stated at full strength and in the right direction, and `inv.trade_withdrawn_matches_deletion_report` is a clean iff. The defect is only that the unexercisability is confessed in a `parallel_assumption` instead of being surfaced as a group gap or a question, which is where a coordinator would look for it. Fold into F6's fix.

### F8 — MINOR — `type.trade_withdrawn.mutation_role` is `mutable`, the same role as `type.trade_status`

Nothing in the type's role distinguishes a monotonic latch from an ordinary replaceable value; the monotonicity lives in `derivation.rule` and `parallel_assumption` prose. This turns out to be cosmetic rather than substantive — see Q2 below — but a reader scanning roles would take `withdrawn` for resettable. Worth a `note` on the type.

## Answers to the questions asked

**Q1 — does every changed element restate its cited clauses, or decide something L1 leaves open?**
The `sg.trade-shape` and `sg.placement-moment` changes are clean restatements. Excluding `D` reports from `first_encounter_only` on `t_ca_id`, `t_dts` and `t_tt_id` follows directly from "a withdrawal creates nothing" and is restated by `inv.trade_owning_account_frozen`, `inv.trade_placed_at_matches_earliest_report` and `inv.trade_order_type_frozen`, each with a matching `review_trigger` naming the D case. `handoff.raw.trade_cdc.cdc_flag->logical.trade.withdrawn`, `logical.trade.withdrawn`, `inv.trade_withdrawn_matches_deletion_report` and `inv.trade_withdrawn_only_unclaimed` all restate sentences of `L1.deletion-withdraws` verbatim in substance. Two elements decide something L1 leaves open: `inv.every_received_trade_persisted`, which claims a row for a D-then-I/U trade without qualification (F1, F4), and the `sg.outcome` handoffs, which read a post-withdrawal report's outcome onto that row (F3, F4).

**Q2 — is `withdrawn`'s monotonicity genuinely hole-forced, or a decision dressed as a deferral? Is the hole in the right group's `gap`?**
The monotonicity is genuinely forced, and it is better founded than the Developer's own justification suggests. `inv.trade_withdrawn_matches_deletion_report` states `withdrawn` as an existential over the trade's whole anchored report set — "true if and only if at least one anchored report carries cdc_flag D". Monotonicity is not an extra policy layered on top of that; it is *entailed* by the set-existential form, which has no notion of order to reset against. So the "never reset" prose in `derivation.rule` and `parallel_assumption` is descriptive, not decisional. And the existential's direction is exactly what the hole's standing instruction requires: "no job may treat a report received after a withdrawal as resuming the record" — staying withdrawn is precisely not-resuming, and the alternative (reset on a later report) is the `tempting_wrong_repair` the CE named. The flag is right.

What is *not* hole-forced is everything around it. The hole leaves three readings live, and the CE names the third explicitly: the later report is itself reportable for review. The model takes none of the available honest options — it neither withholds the row (as it does under `L1.hole.held-first-report-placement`) nor reports it for review (as `L1.deletion-withdraws` does for customer withdrawals) — it emits a claimed row that combines a hole-bounded flag with an unbounded outcome. So: the deferral in `withdrawn` is real; the decision is in `inv.every_received_trade_persisted` and `sg.outcome`, where it is not labelled as one at all.

On the `gap`: partially right. `L1.hole.deletion-reversal` appears in `sg.trade-identity`'s gap and in `hole.deletion_reversal.blocks`, which is correct — that is one group it bounds. It is missing from `sg.outcome`, which it bounds equally (F4). One of two.

**Q3 — does the prediction hold?**
**Yes, it holds, and it is worse than the CE predicted.** Traced element by element (F3): `withdrawn = true` from the existential over anchored reports; the row is claimed by `inv.every_received_trade_persisted` regardless of where the D sits; `latest_change`'s candidate set is all anchored I/U reports ordered by `(batch_date, cdc_dsn)` with no bound relative to the D, so `cdc_dsn` 1488601 wins and `status = CNCL`. Withdrawn and freshly updated, with no invariant relating the two, so every audit passes. Beyond the prediction: because `latest_change` is per-field and four outcome attributes are `nullable: true`, the post-withdrawal `U` row's null `t_trade_price`/`t_chrg`/`t_comm`/`t_tax` also **erase** the withdrawn trade's executed price, fees, commission and tax — an outright contradiction of "everything that already followed from it stands as history", not merely an incoherent combination. `ce-report-after-withdrawal-v1` should record the prediction as verified at L2 and add the null-erasure, and this belongs in front of the business as the reason `L1.hole.deletion-reversal` needs answering.

**Q4 — do you agree with the `sg.outcome` keep, and is the prose-only `coverage_claim` change honest?**
I agree with the keep on the derivations: for the case the clause actually decides — a trade withdrawn *after* an earlier I/U report — `sg.outcome` needed no change, since its D-exclusion already leaves the outcome fields standing as they last stood, which is exactly what "stands as history" requires. The adjudicator and the Developer were right that nothing in the six handoffs had to move for that case.

The prose-only change is **not honest**, for two concrete reasons rather than as a matter of taste. First, the new `coverage_claim` asserts "`L1.deletion-withdraws` now decides what this means" while the group's `parent_clauses` and every member element's `derived_from` still omit that clause, and the group's only invariant still says the opposite — that the meaning "is `L1.hole.deletions`, not decided here", a hole closed the same day (F2). A group cannot claim coverage from a clause it does not declare and whose member contradicts it. Second, and more seriously, `sg.outcome` is the one group whose selector actually answers `L1.hole.deletion-reversal`, and the rewritten prose discusses the D case at length without mentioning that hole or adding it to the group's `gap` (F4). The effect of a prose-only change here is to make the group *look* reconciled with the new clause while leaving the group as the sole place in the model where a report received after a withdrawal is read as a fact. The keep was right; the write-up made the keep do work it cannot do.

**Q5 — is `inv.every_received_trade_persisted`'s rewrite right in both directions? Can either claim be satisfied vacuously?**
The `statement` is right in both directions and is the correct restatement of the clause. The *element* is not: `necessity` and `parallel_assumption` still assert the pre-change wholesale D-exclusion and cite the closed `L1.hole.deletions` (F1), so the invariant says two incompatible things about its own quantifier and the stale one is in the field an implementer treats as normative. On vacuity: the positive direction is non-vacuous for ordinary trades (the received records exercise it heavily) but its *withdrawn* branch is vacuous, since no received record carries `D`. The absence direction, delegated to `inv.trade_withdrawn_only_unclaimed`, is entirely vacuous today. Neither is *stated* vacuously — both are honest universals — but neither has a legal test surface (F6, F7).

**Q6 — was any invariant weakened because no fixture exercises it?**
No, and I looked for it specifically. The D-only claim is stated at full strength, in the right direction, with a matching `review_trigger`, and `inv.trade_withdrawn_matches_deletion_report` is a clean iff. The real problem is the inverse of weakening: the invariants are strong and *unexercisable*, because `sources-v1.json` anchors no labeled constructed trade source, so `L1.constructed-scenarios`' new withdrawal exception cannot be used for this job without injecting constructed rows into `raw.trade_cdc` — which is the mixing that clause forbids, which `inv.trade_not_constructed` cannot detect, and which is precisely how the proposed CE's fixture is built (F6). `sg.constructed-scenarios` still carries `gap: "none"` while its reasoning has been invalidated by the amendment.

## Elements I would REJECT

- `inv.every_received_trade_persisted` — F1 (stale `necessity` and `parallel_assumption` asserting the pre-change quantifier and a closed hole), F4 (claims a row for the D-then-I/U ordering without bounding it).
- `inv.trade_outcome_updates_in_place` — F2 (defers to closed `L1.hole.deletions`; `derived_from` omits `L1.deletion-withdraws`), F4 (unbounded candidate set).
- `handoff.raw.trade_cdc.t_st_id->logical.trade.status` — F3, F4. The visible face of the incoherence.
- `handoff.raw.trade_cdc.t_trade_price->logical.trade.executed_price` — F3 (null erasure of a withdrawn trade's history), F4.
- `handoff.raw.trade_cdc.t_chrg->logical.trade.fees` — same.
- `handoff.raw.trade_cdc.t_comm->logical.trade.commission` — same.
- `handoff.raw.trade_cdc.t_tax->logical.trade.tax` — same.
- `handoff.raw.trade_cdc.t_qty->logical.trade.quantity` — F4 (same unbounded candidate set; no null risk on this field, rejected for consistency of the fix).

Not rejected, and sound as written: `type.trade_withdrawn`, `logical.trade.withdrawn`, `handoff.raw.trade_cdc.cdc_flag->logical.trade.withdrawn`, `inv.trade_withdrawn_matches_deletion_report`, `inv.trade_withdrawn_only_unclaimed`, and every `sg.trade-shape` / `sg.placement-moment` element changed this cycle. `sg.constructed-scenarios`' members are sound; its group `gap` is not (F6), which is a group-level defect, not an element rejection.

## What would have changed my mind

A pass, with F1/F2/F6 as non-blocking bookkeeping, if `sg.outcome`'s `latest_change` candidate set had been bounded by `L1.hole.deletion-reversal` the same way `withdrawn` is — restricted to anchored I/U reports at or before the trade's earliest anchored D report, or the row withheld, or the trade reported for review — with the hole named in `sg.outcome`'s `gap` and `sg.outcome` listed in `hole.deletion_reversal.blocks`. Equally, I would have passed if the model had declined to claim the D-then-I/U row at all and carried the case up in `questions_for_authority`, since that is a deferral rather than a decision. What I cannot pass is one derivation bounded by the hole and its neighbour on the same row unbounded, producing a combination the model's own proposed counterexample predicted and no invariant can detect.

VERDICT: fail
