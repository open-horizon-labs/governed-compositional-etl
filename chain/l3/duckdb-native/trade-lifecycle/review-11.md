# L3 projection review 11 — `duckdb-native` / `trade-lifecycle`

Reviewer: projection reviewer (capable model), 2026-09-17.
Authority: `chain/l2/trade-lifecycle/semantic-model.json` restricted to `selected_element_ids` in
`chain/l2/trade-lifecycle/review.json` (review sha `0405354…70c7f6`), `chain/anchors/**`,
`chain/profiles/duckdb-native.json`. Read also as reviewer: `sketches/l1-brokerage-intent-v1.md`,
`counterexamples/proposed/*.json`. Not read: `oracle/`, `.oh/`.

## What I checked

- Element-by-element coverage of the 57 selected ids against `manifest.json` and `trade.sql`'s
  `derived_from`; the audit set against the selected invariants.
- `trade.sql` in full: the two held-report gates, `first_report`, `latest_outcome`, both pins, the
  `first_seen_late` computation, and the MERGE write surface.
- Every audit under `audits/`, in particular `inv.trade_on_closed_account_reported`,
  `inv.trade_first_seen_late_matches_status_order`, `inv.trade_first_seen_late_defined_or_held`,
  `inv.trade_placement_reference_frozen`.
- The exact L2 delta since the stamp that `check` is complaining about
  (`git diff 627e91d..HEAD -- chain/l2/trade-lifecycle/semantic-model.json`) and the exact L3 delta
  (`git diff 627e91d..HEAD -- chain/l3/duckdb-native/trade-lifecycle/`).
- Harness, all read-only: `check`, `run`, `mutate`, `twophase`, and `simulate` against all six CE
  documents in `counterexamples/proposed/`. I also read the resulting simulation databases
  (`build/chain-duckdb-native-sim-*.duckdb`) read-only to see the actual column values, because
  `simulate`'s JSON reports only a row count for `governed.trade`.
- Grep for fixture hand-tuning: no trade number, account number, date literal or price appears
  anywhere in `trade.sql` or any audit. Every string literal in the projection is an anchored code
  (`I`/`U`/`D`; `PNDG`/`SBMT`/`CMPT`/`CNCL`; `TLB`/`TLS`/`TMB`/`TMS`; `INAC`).

## Question 1 — does every artifact and audit implement exactly the selected elements?

Yes. One artifact (`trade.sql`) for `logical.trade`; 13 audits for the 13 selected invariants whose
`deterministic` is true. The fourteenth selected invariant, `inv.trade_not_constructed`, is
`deterministic: false` — a judgment invariant, which the change contract does not require an audit
for; its claim (no constructed trade source exists to mix in) is checkable by inspection:
`sources-v1.json` anchors no `ce.trade_*` source and the SQL's `reads` are exactly
`raw.trade_cdc`, `raw.trade_history`, `governed.account`, `governed.customer`. Nothing outside the
selection is projected; `questions_for_authority` is empty and I found nothing the model is silent
about that the SQL had to decide. No invented mapping: every code list matches
`chain/anchors/sources-v1.json` (`trade_code_meanings.status_order` is `[PNDG, SBMT, CMPT]` and the
SQL's rank 3 for the terminal `CNCL` is the L2 statement's own wording, not a shape inference).
No policy from data shape, no hand-tuning.

## Question 2 — is the reporting invariant's audit written strictly, and does it leave attribution alone?

Yes, on all three counts.

Strictness. `audits/inv.trade_on_closed_account_reported.sql` is the literal restatement of the L2
`statement`: join `governed.trade` to `governed.account` on the *exact* pinned pair
(`account_number = owning_account_number AND effective_from = owning_account_effective_from`),
report where `status = 'INAC'`. There is no narrowing predicate anywhere — no `placed_at >
effective_from`, no exclusion of the fixture's two known trades, no `LIMIT`, no `WHERE 1=0` dodge.
It is not weakened to keep a run quiet; on the received fixture it returns rows and `run` stays
`ok: true`, listing them under `findings_for_the_business`, which is the contract's intended shape
for `reports: true`. `a.status = 'INAC'` leaves an absent status unreported rather than defaulting
to true, which is what the invariant's own `parallel_assumption` requires.

It reads and names the pinned statement without touching it. The audit selects
`trade_number, owning_account_number, owning_account_effective_from, a.status` — it names the trade,
the account, the exact statement, and the status, satisfying "naming the record". It re-derives
nothing: it does not recompute the pin from `placed_at`, does not re-resolve against the current
account statement, and does not join `raw.*` at all. Nothing is dropped, re-pinned or unwound.

Attribution is genuinely unchanged. `trade.sql` is byte-identical to the version accepted at
review 10 (the only L3 change this cycle is the new audit file plus its manifest entry and the
`review_sha256` bump), so no attribution path was touched. `twophase` confirms it behaviourally:
across the two phases only `status, executed_price, fees, commission, tax` changed on trade 372101;
all seven frozen columns, including `owning_account_effective_from = 2012-11-15 18:05:28`, are
unchanged even though account 428 gains a later statement at `2017-07-08` in the second phase. The
MERGE's `WHEN MATCHED THEN UPDATE SET` names only the six mutable outcome columns.

The audit also discriminates in both directions, which the received fixture alone cannot show
(both of its trades pin the closed statement, so a constant-true audit would look identical). Under
`ce-market-order-first-seen-submitted-v1`, trades 900002 and 900003 pin account 428's
`2007-12-29 ACTV` statement and are **not** reported, while 353232 and 372101 pin the
`2012-11-15 INAC` statement and are. Both halves of the invariant's `review_trigger` are therefore
exercised.

## Question 3 — does the SQL on disk answer the move of `sg.placement-moment`? (the crux)

**Yes.** I diffed the group between the stamped commit (`627e91d`) and HEAD. `sg.placement-moment`
moved in exactly four fields, and in exactly one substantive way:

- `parent_clauses` gained `L1.closed-account-activity`.
- `members` gained `inv.trade_on_closed_account_reported` (nothing removed).
- `coverage_claim` and `gap` were rewritten to explain that addition.

Nothing else in the group moved. `types`, `entities` and `handoffs` are byte-identical across the
whole model. The only other invariant that changed at all is
`inv.trade_placement_reference_frozen`, and only in `derived_from` (gained
`L1.closed-account-activity`) and `necessity` — its `statement` and `review_trigger` are unchanged,
so its audit is unaffected.

The new coverage claim asks this job for three things, and I checked each against the SQL on disk:

1. *A trade placed on an account after that account's closing statement is reported for review.*
   Met by the new `audits/inv.trade_on_closed_account_reported.sql` — the one file the Developer
   added. `run` reports exactly trades 353232 and 372101, both pinning 428's 2012-11-15 INAC
   statement, with every must-hold audit at zero and `ok: true`. That is
   `ce.l1.closed-account-activity`'s `deterministic_assertion`, verbatim and exactly.
2. *Closing unwinds nothing already attributed.* Met by the existing, unchanged
   `inv.trade_placement_reference_frozen` and by the existing write surface, not by new code — and
   this needs no new code, because the L2's own claim is that this invariant "now also carries this
   clause", with its statement unchanged. Behavioural evidence above from `twophase`.
3. *Activity never reopens an account.* Trivially satisfied and structurally checkable: `trade.sql`
   writes only `governed.trade` and reads `governed.account`/`governed.customer`; there is no write
   path by which a trade could produce an account statement. `check`'s containment and write-surface
   guard pass (`problems: []`).

So the move demanded exactly one new audit and no change to `trade.sql`, and that is exactly what is
on disk. I specifically satisfied myself that the move did **not** silently demand a
`first_seen_late` change: the market-order amendments (`ce.l1.first-seen-late-market-orders` and the
closed `L1.hole.market-order-seen-pending`) landed in the *previous* cycle and `trade.sql` already
implements them. I re-verified them rather than trusting the fingerprint. The rank comparison
`status_rank > first_lifecycle_rank` with limit orders (`TLB`/`TLS`) at rank 0 and market orders
(`TMB`/`TMS`) at rank 1 yields precisely the amended clause's truth table — limit: PNDG false, SBMT
true; market: PNDG false, SBMT false, CMPT true, CNCL true — and the simulation databases confirm
the live values: 900002 (TMB first reported SBMT) `false`, 900003 (TLB first reported SBMT) `true`,
900004 (TMB first reported PNDG) `false`, 900006 (TLB first reported PNDG) `false`. That is
`ce.l1.market-order-first-seen-submitted`'s and `ce.l1.held-for-review-trades`'s post-answer
expectations, exactly, including the disappearance of the old
`inv.trade_market_order_seen_pending_held`, which exists in neither the L2 nor the audit set.

My judgment: the fingerprints may be stamped.

## Question 4 — is the mutation and counterexample evidence adequate?

Yes.

`mutate` returns `unprotected: []` across 11 mutations: `null` and `swap` on the frozen columns and
`null` on mutable `status` and `quantity`, each caught by a named must-hold audit. Correctly, no
mutation is credited to `inv.trade_on_closed_account_reported` — the harness excludes reporting
invariants, and rightly, since it already fires on the received fixture and would "catch" anything.
That exclusion is why this cycle's protection evidence has to be the counterexample, and it is:
`ce.l1.closed-account-activity` gets its asserted two rows and nothing else; the reported/failed
split reads correctly (`silent: false`, `failures: {}`); and the ACTV-pinned CE trades give the
negative half that the received fixture cannot. All six CE documents behave as their `expected`
blocks state, including `ce.l1.trade-before-account-statement` and `ce.l1.held-for-review-trades`,
whose single must-hold failures are the open holes those documents were written for, not defects
here.

## Findings

None of blocking severity. Two observations, neither a finding against this cycle's change:

- **Observation (informational), `audits/inv.trade_placement_reference_frozen.sql`.** This audit
  proves the freeze by *recomputing* the pin against the current `governed.account` /
  `governed.customer` rather than by comparing against a previously stored value. That is sound for
  every case the fixture and the CEs contain (the new 2017-07-08 statement on 428 is later than both
  trades' `placed_at`, so recomputation and the frozen value agree), and it is strictly stronger
  than a "set once" check for the defect it is guarding. But if ownership-history ever delivers a
  *retroactive* account statement — one whose `effective_from` is at or before an existing trade's
  `placed_at` — the recomputation will disagree with the correctly-frozen stored value and this
  audit will report a violation that is not one. This is pre-existing, accepted at review 10, and
  bounded by `L1.hole.change-effective-time`, which `sg.placement-moment` already names as a gap. It
  does not belong to this cycle's move and I am not conditioning acceptance on it; it is worth a CE
  when that hole is answered.
- **Observation, `audits/inv.trade_on_closed_account_reported.sql`.** A pinned account statement
  carrying a NULL `status` is silently not reported. This is correct — the invariant's
  `parallel_assumption` says so in as many words, and calls it a separate question — and
  `inv.trade_ownership_pin_present` already catches an unresolved pin as a must-hold violation. No
  change wanted.

## What would have changed my mind

I would have failed this projection if any of these had held, and I checked each:

- the closed-account audit had narrowed its scope (a `placed_at`/`effective_from` predicate, an
  account or trade literal, re-deriving the pin from `placed_at` instead of reading the stored pair,
  or re-resolving against the current account statement) so that a run came out quiet;
- the reporting invariant had been written as a must-hold, or the projection had dropped, re-pinned
  or unwound trades 353232 and 372101 — the CE's three `tempting_wrong_repair`s;
- the audit had been constant-true, i.e. reported every row regardless of the pinned status (this is
  invisible on the received fixture, where both trades are on the closed statement, which is why I
  went to the CE databases for ACTV-pinned trades);
- `trade.sql` had changed any frozen column's derivation, or the MERGE's `UPDATE SET` had reached
  past the six mutable outcome columns, or `twophase` had shown any frozen column moving when
  account 428 gained its 2017-07-08 statement;
- the `sg.placement-moment` delta had touched a type, entity, handoff, or another invariant's
  `statement` — which would have demanded a `trade.sql` change the Developer did not make;
- `first_seen_late` had come out any other way for 900002/900003/900004/900006, or the retired
  `inv.trade_market_order_seen_pending_held` had still been present;
- any audit had been missing for a selected deterministic invariant, or any literal in the
  projection had been a code, date or identifier the anchors do not state.

VERDICT: pass
