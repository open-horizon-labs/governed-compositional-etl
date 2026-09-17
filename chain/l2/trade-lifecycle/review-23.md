# L2 review 23 — trade-lifecycle semantic model (verification of the third rework)

Reviewer: L2 semantic-model reviewer (capable model), 2026-09-17.
Scope: verification review of the third rework of the `L1.deletion-withdraws` / `L1.hole.deletion-reversal` defect. Prior failing reviews: `review-21.md` (F1–F8) and `review-22.md` (N1–N4). I re-traced the model from the sketch, the anchors and the two counterexamples rather than from the Developer's rework note, and I re-enumerated the report orderings myself instead of checking the Developer's enumeration.

## What I checked

- `sketches/l1-brokerage-intent-v1.md` in full: `L1.deletion-withdraws` (both accepted extensions, including the trade sentence), `L1.placement-moment` (amended), `L1.attribution-at-placement`, `L1.lifecycle-mutates-outcome`, `L1.unknown-codes`, `L1.constructed-scenarios` (withdrawal exception), `L1.hole.deletion-reversal`, `L1.hole.held-first-report-placement`, and `job:trade-lifecycle`'s clause list (`L1.omitted-facts-stand` is still not in it).
- `chain/ce/accepted/ce.l1.deletion-withdraws.md` and `ce.l1.withdrawal-reaches-standing.md`.
- `counterexamples/proposed/ce-report-after-withdrawal-v1.json` (fixture re-traced row by row) and `ce-withdrawn-account-v1.json` (`blocked_on`, `later_withdrawal_pair`, `deletion_only_holding`).
- `chain/anchors/sources-v1.json` (`raw.trade_cdc` fields, `trade_code_meanings.cdc_flag`, `status_order`, `trade_type_codes`, `report_order` and its note), `semantic-model-v2.schema.json`, `L2-FORMAT.md`, both developer contracts.
- Every element of `chain/l2/trade-lifecycle/semantic-model.json`: 15 types, `logical.trade` + its attributes, 15 handoffs, **17** invariants (one new), 6 groups, 7 holes, 2 questions. Read `statement`/`derivation`/`necessity`/`parallel_assumption`/`review_trigger` per element.
- `chain/l2/positions/selected-model.json` — now selected — specifically `inv.eligible_holding_report_persisted`, `inv.holding_change_absent_for_withdrawn_only_pair`, `inv.holding_quantity_updates_in_place`, and `sg.holding-shape`'s gap.
- `.venv/bin/python scripts/chain_l2.py check trade-lifecycle` → `status: question`, `problems: []`, the same two questions (reopened-closed-account; the `ce.trade_changes` anchor request). `weave trade-lifecycle` → `contradiction: 0`, `named-gap: 13`, `overlap: 3`, `dependency: 7`.

Verdict summary: **the defect is fixed, and this time it is fixed on both fronts of the same row rather than moved to the other one.** The bound is now one bound, stated identically in every selector, invariant, group gap and the hole itself; the D-first ordering is claimed absent by a stated invariant instead of being claimed present with no candidate values; the clause's stand-as-history requirement is intact for the ordering the clause actually decides; and the reading now matches the selected `positions` model. What remains are four bookkeeping defects, none of which decides the hole in either direction and one of which (M1) I want fixed before the L3 projections read this model as authority.

## The four hard checks

### 1. Are the three unclaimed invariants a disjoint partition? — **Exhaustive and coherent, but not disjoint.**

The three claims, as stated:

- **A** `inv.trade_withdrawn_only_unclaimed` — anchored, fully-coded reports exist, **all** cdc_flag D, no I/U among them → no row. Decided by `L1.deletion-withdraws` ("a thing whose only reports are withdrawals was never held at all").
- **B** `inv.trade_earliest_report_withdrawn_unclaimed` (new) — earliest anchored report carries cdc_flag D **and** no anchored, fully-coded I/U report at or before that `report_order` position → no row, regardless of any later I/U. Deferred to `L1.hole.deletion-reversal`.
- **C** `inv.trade_held_first_report_unclaimed` — earliest report of either anchored source held under `L1.unknown-codes`, or any placement-fixing fact would come from a held report → no row. Deferred to `L1.hole.held-first-report-placement`.

And **E** `inv.every_received_trade_persisted` — at least one anchored, fully-coded I/U report at or before the earliest anchored D (or any such report, when no D exists), and no placement-fixing fact from a held report → exactly one row.

Enumerated:

| ordering | claimed by | outcome |
|---|---|---|
| all-D (≥1 D, no I/U) | **A and B** | absent — claimed twice |
| D-first, then I/U | B only | absent |
| I/U-first, then D (no later I/U) | E | present, withdrawn, full outcome |
| I/U-first, then D, then I/U | E | present, withdrawn, outcome frozen at the last pre-D I/U |
| I/U-first, then I/U between, then D | E | present; the intervening I/U is `at or before` the D and still wins |
| no D at all | E | present |
| held-first (any flags) | C | absent |
| held-first where that held row also carries D | **C and B** | absent — claimed twice (see M1) |
| I/U-first, held D later, clean I/U after | E | present, `withdrawn` **false**, outcome frozen anyway (see M1) |
| `th_t_id` in `raw.trade_history` with no `raw.trade_cdc` row | nobody claims present or absent | out of scope by E's own stated reasoning (no identity handoff); a `review_trigger`, pre-existing |

**No ordering falls through all three.** Two orderings are claimed twice. Both double-claims resolve to the *same* verdict (no row), so neither is a contradiction, and A's ground is independent of the hole, so A survives if the hole is answered and B retires. The overlap is therefore harmless in outcome — but `inv.trade_earliest_report_withdrawn_unclaimed`'s `parallel_assumption` asserts that it "differs from `inv.trade_withdrawn_only_unclaimed`'s decided absence (which holds for a trade with no I/U report at all, regardless of order)", and that distinctness claim is **false as written**: a D-only trade satisfies B's own stated antecedent too. The fix is one clause, and the selected sibling model already writes it: `positions`' `inv.eligible_holding_report_persisted` excludes a pair "whose earliest anchored report is cdc_flag D **and which has at least one later anchored non-D report**". Add that second conjunct to B and the partition is genuinely disjoint. Recorded as **M2**, non-blocking.

### 2. Does anything the clause requires to STAND now fail to? — **No. Verified, for all three facts.**

The case the clause decides: a trade withdrawn after earlier I/U reports. Traced on `ce-report-after-withdrawal-v1`'s trade 353232 (received `I` 2017-06-30; constructed `D` at cdc_dsn 1488600 with full outcome fields; constructed `U` status CNCL with null price/fees/commission/tax at 1488601):

- **Claimed.** E's narrowed existential asks for a qualifying I/U report *at or before* the earliest D. The June `I` is before cdc_dsn 1488600, so it qualifies. The row is claimed, exactly once. The narrowing did **not** cost this ordering its row — I checked this specifically, because narrowing an existential is the obvious way to break case 2 while fixing case 1.
- **Placement and attribution stand.** `handoff.raw.trade_cdc.t_dts->placed_at`, `t_ca_id->owning_account_number` and `t_tt_id->order_type` scan qualifying I/U reports at or before the earliest D; the June `I` is in that set and is first-encountered, so all three are pinned from it. `owning_account_effective_from`, `owning_customer_number` and `owning_customer_effective_from` resolve `as_of` `placed_at`, unchanged. `inv.trade_ownership_pin_present`'s four non-nulls are satisfiable.
- **Outcome stands.** The `latest_change` candidate set is qualifying I/U reports at or before the earliest D = {the June `I`}. `status` = CMPT and the four nullable money fields keep their June values. The **null erasure is gone and cannot return by this path**: the offending report is out of the candidate set, so per-field nullability has nothing to launder. `inv.trade_outcome_updates_in_place` states the same rule in checkable form.
- **The bound is `at or before`, not `before`.** I checked this against the obvious off-by-one: an I/U report arriving *between* an earlier I and the D (dsn 10 I, dsn 15 U, dsn 20 D) is inside the set and still wins, so a withdrawn trade keeps its *last* pre-withdrawal outcome, not its first. Correct.
- **Nothing is unclaimed.** `withdrawn` = true via a clean iff over the trade's whole anchored report set; `first_seen_late` non-null (its held set is the unknown-code case only); the three `_frozen` invariants each scope themselves to claimed rows and exclude both the D report and post-D reports from their comparisons, so none of them fires on this row.
- The CE's own `deterministic_assertion` — one row, marked withdrawn, engines agreeing on every field including status, holdings byte-identical — is now satisfied by the model rather than contradicted by it.

`review-22.md`'s **N2** is therefore resolved at its root rather than patched: for every row E claims, the outcome candidate set is non-empty by construction (the qualifying I/U report E's existential demands *is* a member of that set), so `status` and `quantity`, both `nullable: false`, always have a source. That equivalence is the load-bearing property of this rework, and it holds because both quantifiers were written against the same report set.

### 3. Does anything still decide the D-then-I/U ordering, in either direction? — **No, on every front that can reach a claimed row.** Three residues, all provably non-divergent; two of them are stale text I would still fix.

Every site that could read a post-withdrawal report:

- All six `sg.outcome` handoffs: bounded, hole named, in `necessity`, `parallel_assumption` and `review_trigger`. Verified per handoff, not by group prose.
- The three placement-fixing handoffs: bounded identically. The `"even when it precedes every I/U report in report order"` language that produced N1 has **0 occurrences** in the file.
- `inv.trade_owning_account_frozen`, `inv.trade_placement_reference_frozen`, `inv.trade_order_type_frozen`, `inv.trade_placed_at_matches_earliest_report`, `inv.trade_first_seen_late_matches_status_order`, `inv.trade_first_seen_late_defined_or_held`, `inv.trade_outcome_updates_in_place`, `inv.every_received_trade_persisted`: all carry the same bound, and each additionally excludes the three unclaimed sets from its own quantifier.
- `logical.trade.withdrawn` and `inv.trade_withdrawn_matches_deletion_report`: a set-existential with no ordering to reset against. Not a decision — the reasoning `review-21.md`'s Q2 arrived at, now on the element.
- `hole.deletion_reversal.blocks` = `["sg.outcome", "sg.placement-moment", "sg.trade-identity", "sg.trade-shape"]`; all four gaps name the hole; the `question` no longer claims a symmetry that was not there, and now states the uniform no-resumption reading front by front. The false "on both fronts, symmetrically" sentence is gone.
- A post-D I/U report is now **completely inert**: it supplies nothing, changes nothing, resets nothing, and `inv.trade_outcome_updates_in_place` says plainly that it is not reported for review either, with the reason (no clause names that treatment for this case). That is a deferral, not a decision, and it is labelled as one.

The residues:

- **`logical.trade.first_seen_late`'s `derivation.rule` was not updated with the bound** (M3). It still reads "otherwise **the `raw.trade_cdc` row with the smallest `(batch_date, cdc_dsn)` for that `t_id`**" — no D exclusion, no post-D exclusion — while `inv.trade_first_seen_late_matches_status_order`, which claims to restate it directly, says "its earliest non-D-flagged (cdc_flag I or U) `raw.trade_cdc` row at or before the trade's earliest anchored cdc_flag D report". The derivation is the field an L3 author implements, so this is the same shape as `review-21.md`'s F1. It **cannot diverge for a claimed row**: divergence needs the smallest-`(batch_date, cdc_dsn)` row to be a D, i.e. the earliest report to be D, and every such trade is claimed absent by B. I verified that implication rather than assuming it. Still stale text asserting the pre-rework shape, and it becomes wrong the moment the hole is answered.
- **`handoff.raw.trade_history.th_dts->placed_at` carries no D bound at all** (M3). It is the sibling that supplies `placed_at` for a historical-load trade, and it is unbounded. It cannot diverge either, because the anchored `report_order.note` makes every trade with `raw.trade_history` rows also carry a Batch1 `t_id` snapshot at cdc_dsn 0 with cdc_flag I — so such a trade's earliest report is always an I and B never fires on it. But that reasoning appears nowhere on the handoff or on B, and B's `statement` asserts flatly that for a trade it claims absent "no source report exists from which this job may read them", which this handoff would contradict if the anchor note ever changed.
- The "anchored" vs "anchored, fully-coded" imprecision on the D side of every bound (**M1**, below). Not a decision about the ordering; a different defect.

### 4. What this rework introduced.

**M1 — MODERATE — the D side of the new bound says "anchored", not "anchored, fully-coded", so a *held* D report can set the bound.**

The I/U side of every bound is carefully qualified: "anchored, fully-coded" (9 occurrences), and the three `_frozen` invariants spell it out as "anchored (not held under `L1.unknown-codes`)". The D side is qualified only as "the trade's earliest **anchored** cdc_flag D report" — 23 occurrences, including the new invariant, E's existential, all nine selector bounds and all four group gaps. `inv.trade_outcome_updates_in_place` proves the two phrases are distinct in this file's own usage: "an **anchored** `raw.trade_cdc` report ... **with every one of its coded fields anchored**". And `logical.trade.withdrawn`'s `derivation.rule` requires "at least one **anchored, fully-coded**" D report, while `inv.trade_withdrawn_matches_deletion_report`, which restates it, requires only "at least one **anchored**" one.

Take a trade with a clean `I` at dsn 10, a row at dsn 20 carrying `cdc_flag D` **and** an unanchored `t_st_id`, and a clean `U` at dsn 30. Under the literal text: `withdrawn` = **false** (no fully-coded D); `inv.trade_withdrawn_matches_deletion_report` demands **true** and fires on a correctly projected row; and the dsn-30 `U` is excluded from every candidate set because it is after "the earliest anchored cdc_flag D report" — so a trade the model says was never withdrawn has its outcome and placement frozen at dsn 10 anyway, on the strength of a `cdc_flag` read off a report `L1.unknown-codes` holds as a whole and says nothing else about may be read.

The selected `positions` model states exactly the missing sentence, twice: "A report held under `L1.unknown-codes` is not an anchored report at all: it counts as neither an anchored non-D report nor a D report for this invariant's purposes." `trade-lifecycle` leaves it to inference. So this is also a terminology divergence from the model that is now authority for the sibling job.

Why this is not a third failure. It is doubly unreachable today — the received records carry no D row at all, and `L1.constructed-scenarios` plus the missing `ce.trade_*` anchor make a constructed one illegal, which the filed `questions_for_authority` entry already says. It decides nothing about `L1.hole.deletion-reversal` in either direction. The under-qualified phrasing is not new this cycle: it has stood on `inv.trade_withdrawn_matches_deletion_report` since round 1 and on the `sg.outcome` bound since round 2, and both prior reviews examined those elements and blessed them (`review-21.md` called the iff "clean"; `review-22.md` accepted the bound as correct in shape). Failing the rework on a twice-blessed wording that this round only *propagated*, while the substantive defect it was asked to fix is fixed, would be moving the goalposts. The fix is mechanical: write "anchored, fully-coded" on the D side everywhere, and copy `positions`' held-report sentence onto the three absence invariants and E.

**M2 — MINOR — the new invariant's claimed distinctness from `inv.trade_withdrawn_only_unclaimed` is false.** See check 1. Add "and which has at least one anchored I/U report at a later `report_order` position", mirroring `positions`.

**M3 — MINOR — two elements still assert the pre-rework shape: `first_seen_late`'s `derivation.rule` and the `raw.trade_history.th_dts` handoff.** See check 3. Both are provably non-divergent for any claimed row; both are the derivation-moved-and-a-neighbour-did-not pattern that produced review-21's F1 and review-22's N1, so I want them corrected on principle rather than on consequence. `inv.trade_placed_at_matches_earliest_report`'s `review_trigger` has the same shape: it fires on "a trade with anchored `raw.trade_history` rows [whose] `placed_at` [is] anything other than the smallest `th_dts`" without the exclusion its own `statement` carries.

**M4 — MINOR — `sg.constructed-scenarios` still carries `gap: "none"`.** I accept the gate constraint (`"none"` or a hole id, and the bound here is a missing anchor, not an open hole), and the substance is in the `coverage_claim` and the filed question, which is where a coordinator looks. `review-22.md`'s N4 stands unchanged and unblocking.

## Cross-job agreement (review-21 F5 / review-22 N3) — resolved, and I checked it against the selected model rather than against the claim.

`positions/selected-model.json`, read directly:

- `inv.eligible_holding_report_persisted` claims a row for a pair "with at least one anchored report **earlier than every anchored cdc_flag D report** of that pair", and excludes "a pair whose earliest anchored report is cdc_flag D and which has at least one later anchored non-D report" as the hole's case.
- `inv.holding_quantity_updates_in_place` freezes the quantities at the pair's last anchored report before its earliest D.
- `inv.holding_change_absent_for_withdrawn_only_pair` claims the D-only pair absent.

`trade-lifecycle` now takes the same three positions on the same three orderings, with the same bound expressed over `report_order`. The two jobs agree — and the agreement is an agreement about claims, which is the thing `weave` structurally cannot see, since it compares mutation roles and declared gaps and not declared claims. `weave`'s `contradiction: 0` was already 0 while the jobs disagreed, and it is still 0 now that they agree; I record that the agreement was verified by reading both models, not by reading the gate.

I also accept the Developer's ground for the choice. It declined to treat the D-first trade as genuinely placed at its first I/U report, on the grounds that nothing licenses reading a post-withdrawal report as the origin of the trade's existence. That is the right call and for the right reason: `review-22.md` listed it as option 3 and said it would have argued with it, and the argument is now settled the other way by `L1.hole.deletion-reversal`'s own standing instruction ("no job may treat a report received after a withdrawal as resuming the record") — reading a report as the one that *brings the trade into being* is the strongest form of resuming, not a marginal one, and asserting it would be deciding the hole. The Developer's `necessity` on the new invariant says exactly this. Withholding is a deferral; placing from the later report would have been a decision.

## Elements I would still reject

None blocking. Four bookkeeping fixes I want landed before the L3 projections treat this model as authority:

- **`inv.trade_withdrawn_matches_deletion_report`** and every site carrying the phrase "earliest anchored cdc_flag D report" — M1. Qualify the D side as "anchored, fully-coded", and state that a held report is not an anchored report for these purposes, as `positions` does.
- **`inv.trade_earliest_report_withdrawn_unclaimed`** — M2. Its `parallel_assumption`'s distinctness claim; one conjunct fixes it.
- **`logical.trade.first_seen_late`** (`derivation.rule`), **`handoff.raw.trade_history.th_dts->logical.trade.placed_at`**, and **`inv.trade_placed_at_matches_earliest_report`**'s `review_trigger` — M3.
- **`sg.constructed-scenarios`** — M4, group-level, unchanged from review-22.

Accepted and sound as written: all six `sg.outcome` handoffs; the three placement-fixing handoffs; `inv.trade_outcome_updates_in_place`; `inv.every_received_trade_persisted` (both its narrowed existential and its `necessity`/`parallel_assumption`, which now state the same quantifier as its `statement` — review-21's F1 stays fixed); `inv.trade_earliest_report_withdrawn_unclaimed`'s `statement`, `necessity` and `review_trigger`; the three `_frozen` invariants; `inv.trade_first_seen_late_defined_or_held`; `type.trade_withdrawn` with its note; `logical.trade.withdrawn`; `hole.deletion_reversal` including its corrected `question` and its four-group `blocks`; all four group gaps; both `questions_for_authority` entries.

## It is right this time. What would have changed my mind

Plainly: the rework does what reviews 21 and 22 asked, and it does it by making one bound out of two instead of by moving the asymmetry a third time. The test I set myself was whether the two quantifiers — E's existential and the selectors' candidate sets — are written against the *same* report set, because that identity is what makes N2 impossible rather than merely absent. They are, and I verified the consequence in both directions: every row E claims has a non-empty candidate set for its non-nullable fields, and every trade with an empty candidate set is claimed absent by a stated, checkable invariant.

I would have failed it for any of:

1. **A single unbounded selector reaching a claimed row.** I checked all fifteen handoffs individually, plus `first_seen_late`'s derivation and every `report_order` occurrence in the file. The two unbounded residues (M3) cannot reach a claimed row, and I proved the implication rather than assuming it; had either been reachable, the deferral would have been nominal and this would be a fail.
2. **Any fact the clause requires to stand coming out null, absent or unclaimed.** If the bound had been "before" rather than "at or before", or if E's narrowing had dropped the I-then-D trade's row, check 2 would have failed.
3. **The D-first trade claimed present, or claimed absent by nobody.** It is claimed absent by a named invariant with the hole cited, which is a deferral; had it been merely uncovered, the absence would have been unauditable, which is the defect `inv.trade_held_first_report_unclaimed` exists to prevent elsewhere in this same model.
4. **An ordering claimed twice with opposite verdicts.** Two orderings are claimed twice (check 1); both times both claims say "no row". Had A and B disagreed, or had B's hole-deferred absence shadowed A's decided absence in a way that would retire both when the hole is answered, that would be a fail.
5. **M1 reaching a projectable row.** If the received records carried any D row, or if a labeled `ce.trade_*` source existed so a constructed D row were legal, M1 would be reachable and blocking today. It is neither, and the model itself is the thing that says so, in the question it filed.

VERDICT: pass
