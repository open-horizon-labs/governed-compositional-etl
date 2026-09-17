# Projection review 10 — duckdb-sqlmesh / trade-lifecycle

Reviewer: projection reviewer (capable model), cycle 10.
Authority: `chain/l2/trade-lifecycle/semantic-model.json` restricted to `selected_element_ids` in
`chain/l2/trade-lifecycle/review.json` (model_sha256 `0405354…0c7f6`), plus
`chain/profiles/duckdb-sqlmesh.json` and `chain/anchors/**`. L1 read as a reviewer for question 4 only.

## What I checked

Read in full: `models/trade.sql`, all 13 files under `audits/`, `manifest.json`, the engine profile,
`chain/anchors/DEVELOPER-CONTRACT-L2-L3.md`, the L2 entity/type/handoff/invariant/group records for
`logical.trade`, and `L1.placement-moment` / `L1.closed-account-activity` in
`sketches/l1-brokerage-intent-v1.md`. Diffed the L2 model and the projection against the state at the last
acceptance (`627e91d`) to establish exactly what moved and exactly what the Developer changed in answer.

Commands run (all read-only):

| command | result |
|---|---|
| `check duckdb-sqlmesh trade-lifecycle` | `status: question`, `problems: []`, one question (the `sg.placement-moment` move); `acceptance.accepted false` with reason "the projection changed after the review that accepted it" |
| `run duckdb-sqlmesh trade-lifecycle` | `ok: true`; `findings_for_the_business: {inv.trade_on_closed_account_reported: 2}` naming trades 353232 and 372101 on account 428, pinned statement `2012-11-15 18:05:28`; every other audit zero; SQLMesh plan applied with a `[WARNING]`, `sqlmesh.audit_ok false` (expected and not decisive per the contract) |
| `twophase duckdb-sqlmesh trade-lifecycle` | `first_phase_ok true`, `second_phase_ok true`; `changed_columns` = commission, executed_price, fees, status, tax — all six mutable-role columns or fewer, no frozen column moved |
| `compare duckdb-native trade-lifecycle --against duckdb-sqlmesh` | `both_ok true`, `governed.trade` `identical: true`, columns match, 2 rows each |
| `simulate … --ce ce-closed-account-activity-v1.json` | `status: accepted`, `ok true`, `silent false`, `fired: {inv.trade_on_closed_account_reported: {reported: 2, via: sqlmesh audit}}`, `failures: {}` |

## Question 1 — every model and audit implements exactly the selected L2 elements

Yes, as far as I can find fault with it.

- `manifest.json`'s single artifact cites 29 element ids; each is in `selected_element_ids`, and every selected
  entity, attribute and handoff element for `logical.trade` appears there. No element is cited that the
  selection does not carry.
- Thirteen audits, one per selected **deterministic** invariant. The fourteenth selected invariant,
  `inv.trade_not_constructed`, is `deterministic: false` and is a statement about what the model has no
  mechanism to do; the contract requires an audit file only per deterministic invariant, so its absence is
  correct, not an omission.
- Selectors are implemented as stated, not approximated. `first_encounter_only` is a
  `ROW_NUMBER() … ORDER BY batch_date ASC, cdc_dsn ASC` (or `th_dts ASC`) take-first; `as_of_event_time` is
  `effective_from <= placed_at` with `ORDER BY effective_from DESC` take-first against `governed.account` and
  `governed.customer` — never a current statement, never an `effective_to` the model does not declare; the
  `same_statement_as_owning_account_reference` handoff for `owning_customer_number` is taken from
  `account_asof`'s own `a.owning_customer_number`, i.e. structurally from the pinned statement, so it cannot
  name a customer inconsistent with it; `latest_change` is a take-latest over `cdc_flag IN ('I','U')` anchored
  rows, correctly excluding `D` per `inv.trade_outcome_updates_in_place`.
- No policy from data shape. Every code vocabulary in the SQL (`I,U,D`; `PNDG,SBMT,CMPT,CNCL`;
  `TLB,TLS,TMB,TMS`; `INAC`) is the anchored vocabulary, and each membership test is written null-sensitively
  (`IS NULL OR NOT IN`) so an absent code is held rather than silently passing an `IN` as unknown.
- No hand-tuning to the fixture. The fixture is tiny — 4 `raw.trade_cdc` rows, 4 `raw.trade_history` rows,
  2 persisted trades, both limit orders, both `first_seen_late false`. Nothing in it exercises a market order,
  a late first report, a held report, or a `D` flag. The SQL nonetheless implements all of those branches
  generally, contains no trade number, account number or date literal, and is byte-for-byte equivalent in
  result to the independently written `duckdb-native` projection (`compare … identical: true`). A projection
  tuned to this fixture would have collapsed those branches; this one did not.
- Read containment: the model references only `raw.trade_cdc`, `raw.trade_history`, `governed.account`,
  `governed.customer` — exactly the sources and upstream entities its handoffs name — and the gate's
  containment and write-surface guards return no problems.

## Question 2 — the reporting audit

`audits/inv.trade_on_closed_account_reported.sql` is correct on every count I can test.

- **Declared non-blocking, correctly.** Header is exactly
  `AUDIT (name "inv.trade_on_closed_account_reported", blocking false);` — dotted name double-quoted as the
  contract's SQLMesh note requires, and the run confirms the plan applied with a `[WARNING]` rather than
  refusing promotion, with the rows surfacing under `findings_for_the_business` and `run` staying `ok: true`.
- **Non-blocking is used nowhere else.** I grepped every audit header: `blocking false` appears on this one
  file and on no other. The other twelve are bare `AUDIT (name "inv.x");`. `inv.trade_on_closed_account_reported`
  is the only invariant in the L2 model carrying `reports: true` (with
  `reported_because_clause: L1.closed-account-activity`); I enumerated the `reports` flag on all fourteen
  invariants to confirm there is no second one and no must-hold audit quietly opted out. This is the check I
  most expected to fail, and it does not.
- **Not weakened to keep the run quiet.** The predicate is the invariant's own predicate and nothing narrower:
  join `@this_model` to `governed.account` on the frozen pair `(owning_account_number,
  owning_account_effective_from)` and select where `a.status = 'INAC'`. There is no date filter, no account
  exclusion, no `LIMIT`, no `DISTINCT` hiding a fan-out, and no `AND placed_at > …` re-deriving the "after the
  closing statement" test that the pinned statement already decides. It fires on the received fixture — two
  rows, the two trades the business asked about — which is the point.
- **It reads and names; it does not re-pin, drop or unwind.** The audit is a single `SELECT` over
  `@this_model`; it resolves no statement of its own (the join is an equality on the already-frozen
  `effective_from`, not an `as_of` re-resolution), and it emits `trade_number`,
  `owning_account_number`, `owning_account_effective_from` — it names the pinned statement rather than
  restating a judgement about it. The trade's attribution is provably unchanged: `twophase`'s
  `changed_columns` across a later report are commission, executed_price, fees, status, tax only, and the
  simulate run leaves 372101's `owning_account_number`, `owning_account_effective_from`,
  `owning_customer_number` and `owning_customer_effective_from` identical before and after, including after
  the counterexample adds a *later* (2017-07-08) account statement — the trade stays pinned to the
  2012-11-15 statement and is not additionally reported for the new one. That is
  `L1.closed-account-activity`'s "closing unwinds nothing already attributed", demonstrated.
- The invariant's "silence on an absent status" clause is honoured by construction: `a.status = 'INAC'` is
  NULL, hence false, for a pinned statement carrying no status, so an absent status does not report and does
  not default to true.
- Registered in `manifest.json` under `audits` and in the model's `audits (...)` list like any other, and the
  model's `depends_on (governed.account, governed.customer)` already covers the audit's join to another model.

## Question 3 — the CUSTOM header and the write surface

Correct per `chain/profiles/duckdb-sqlmesh.json`.

The profile's `strategy_for_incremental_by_identity` is "kind CUSTOM materialization governed_merge executing
a role-derived SQLGlot MERGE through the adapter". The header is
`kind CUSTOM (materialization 'governed_merge', materialization_properties ('unique_key' = 'trade_number',
'mutable_columns' = …, 'frozen_columns' = …))`. I checked the three property values against the L2 types'
`mutation_role` rather than against the header's own plausibility:

- `identity`: `trade_number` → `unique_key = trade_number`. ✅
- `mutable`: status, executed_price, fees, commission, tax, quantity (types `trade_status`,
  `trade_executed_price`, `trade_fees`, `trade_commission`, `trade_tax`, `trade_quantity`) → exactly the six
  in `mutable_columns`. ✅
- `frozen_from_first_encounter`: owning_account_number, placed_at, owning_account_effective_from,
  owning_customer_number, owning_customer_effective_from, first_seen_late, order_type → exactly the seven in
  `frozen_columns`. ✅
- No attribute of this entity carries `per_statement`, so no `per_statement` column can be in an update path.

The materialization derives `WHEN MATCHED UPDATE SET` from `mutable_columns`, so frozen columns are excluded
by construction; the gate's write-surface guard reports no problem, and `twophase` independently confirms it
empirically — a later report changed only mutable columns and left all seven frozen values byte-identical.
`kind FULL` would have been wrong here and is not used.

## Question 4 — does the SQL on disk answer the `sg.placement-moment` move? (the crux)

**Yes. The move is answered in full, and I can name precisely what moved and precisely what answers it.**

I did not take the Developer's word or the comment headers for this. I diffed the selected L2 model against
its state at the last acceptance (`627e91d`). The complete set of L2 changes is three items, all of them
within or about `sg.placement-moment`:

1. `inv.trade_on_closed_account_reported` **added** (new invariant, new member of the group).
2. `inv.trade_placement_reference_frozen` changed in `derived_from` (gains `L1.closed-account-activity`) and
   `necessity`. Its `statement` did **not** change.
3. `sg.placement-moment` changed in `parent_clauses` (gains `L1.closed-account-activity`), `members` (gains
   the new invariant), `coverage_claim` and `gap`.

Nothing else in the model moved. In particular **`inv.trade_first_seen_late_matches_status_order`,
`inv.trade_first_seen_late_defined_or_held`, `inv.trade_placed_at_matches_earliest_report`,
`inv.trade_order_type_frozen`, every type, every attribute and every handoff in the group are unchanged**
since the accepted state. The pending-market-order amendment to `L1.placement-moment` was the *previous*
cycle's move and was already compiled and accepted at `627e91d`; it is not what moved now.

So the move demands exactly three things of the SQL, and I checked each:

- **A new audit for the new member.** Present: `audits/inv.trade_on_closed_account_reported.sql`, registered
  in the manifest and the model's `audits (...)` list, correct as analysed under question 2. The projection
  diff since acceptance is precisely this file plus those two registrations plus the `review_sha256` bump —
  nothing else, and nothing gratuitous.
- **`inv.trade_placement_reference_frozen` now also carrying `L1.closed-account-activity`.** The clause it
  gains asks that `owning_account_effective_from` be frozen at first anchored encounter and never
  re-resolved against a later account statement. The existing audit already enforces exactly that
  proposition — it recomputes the account statement as of the *stored* `placed_at` and diffs against what
  `governed.trade` holds, so a re-resolution against any later statement (a closure among them) would show
  as a mismatch. Because the invariant's `statement` did not change, no new checkable proposition was added,
  and the correct answer to this part of the move is no SQL change. `twophase` confirms it behaviourally:
  a closing statement recorded *after* placement (the counterexample's 2017-07-08 row) does not move the
  trade's pin. I specifically looked for a change the Developer had skipped here and found none owed.
- **The group's third demand, "activity never reopens an account".** Trivially satisfied and verifiably so:
  this job's only write surface is `governed.trade`; `governed.account` appears only on the read side of the
  model and of the new audit, and the gate's read-containment and write-surface guards confirm it. There is
  no mechanism here by which a trade could create an account statement, so nothing is owed.

Because `sg.placement-moment` also happens to hold `first_seen_late`, I re-derived the amended
`L1.placement-moment` rule against the SQL anyway rather than assume the earlier acceptance was sound. L1
now says a limit order has a pending stage of its own; an order sent straight to market does not, and where
the brokerage records such an order as pending before routing it, that pending record is the order's own
first lifecycle event. Both `models/trade.sql` and
`audits/inv.trade_first_seen_late_matches_status_order.sql` implement this as
`rank(status_at_first_report) > threshold(order_type)` with `PNDG=0, SBMT=1, CMPT=2, CNCL=3` and
`TLB/TLS → 0`, `TMB/TMS → 1`. Enumerating: a limit order first reported PNDG is not late, SBMT/CMPT/CNCL are
late; a market order first reported **PNDG (0 > 1 false) or SBMT (1 > 1 false) is not late**, CMPT and CNCL
are. That is the amended clause and `inv.trade_first_seen_late_matches_status_order`'s "PNDG or SBMT,
whichever the first-encountered report states … only CMPT or CNCL … is late", claimed as `false` rather than
held — and `inv.trade_first_seen_late_defined_or_held` correspondingly nulls `first_seen_late` if and only if
the first-encountered status or order type is unanchored, with no pending-market-order carve-out left. The
fixture exercises none of these cases (both trades are limit orders, both `false`), so this is a reading of
the SQL, not of the run; the SQL is nevertheless general and matches the native projection exactly.

The remaining half of the `check` question — that `manifest.json`'s `group_fingerprints` still carries the
pre-move fingerprint for `sg.placement-moment` — is not a Developer defect. `chain_l3.py stamp` is what
rewrites those fingerprints, and the contract reserves stamping to the reviewer. The stale stamp is the
expected mid-cycle state and is why `check` raises a question rather than a problem.

## Findings

None. I looked hardest at the three places this cycle could plausibly have gone wrong — a second audit
quietly declared non-blocking, a reporting audit narrowed until it stopped firing, and a `first_seen_late`
derivation left behind by the clause amendment — and found none of them.

What would have changed my mind:

- `blocking false` on any audit other than `inv.trade_on_closed_account_reported`, or on an invariant without
  `reports: true` in the L2.
- The closed-account audit carrying any predicate the invariant does not state — an account or trade number,
  a date bound, a `LIMIT`, or an `a.status <> 'ACTV'`-style rewrite that would also fire on an absent status.
- The closed-account audit re-resolving the account statement with `effective_from <= placed_at` instead of
  the equality join on the frozen pair: that would report against a statement the trade is not pinned to.
- `twophase` showing any of the seven frozen columns in `changed_columns`, or `mutable_columns` /
  `frozen_columns` in the header disagreeing with the L2 types' `mutation_role` by even one column.
- A `first_seen_late` threshold of `0` for `TMB`/`TMS` (which would wrongly mark a market order first reported
  SBMT as late, contradicting the amendment), or a `>=` in place of `>`.
- Any SQL change in this cycle beyond the closed-account audit and its two registrations, which would have
  meant the Developer resolved something in SQL that the move did not ask for.

VERDICT: pass
