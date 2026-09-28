# Narrow L1 change candidates (proposed, not made)

Worker: Opus engineering worker, experiment-lead hat. 2026-09-28. The sketch was not edited; the human picks.

Method. A group's fingerprint (`chain_l2.fingerprints`) hashes the fingerprints of its `parent_clauses` and of the
holes named in its `gap`. So editing one clause's text moves exactly the groups that list it in `parent_clauses`,
across all three selected models. Counting those (from `chain/l2/*/selected-model.json`), only three clauses are the
parent of exactly one group in one job:

| Clause | Groups that list it |
|---|---|
| `L1.current-version` | ownership-history / `sg.current-version` only |
| `L1.placement-moment` | trade-lifecycle / `sg.placement-moment` only |
| `L1.no-phantom-positions` | positions / `sg.no-phantom-positions` only |

Every other clause is a parent of 2 to 12 groups (`L1.deletion-withdraws` 12, `L1.identity` 10). That is why the
last two loops moved every group. The artifact and audit lists below come from `groups_of(model, derived_from)` on
each engine's current manifest, the same computation `chain_l3.py check` now reports.

## The candidates

| # | Clause | Moves | Artifacts stale (per engine) | Audits stale (per engine) | Kept |
|---|---|---|---|---|---|
| A | `L1.current-version` | ownership-history `sg.current-version` | `customer.sql`, `account.sql` (2 of 2) | 2 of 20: `inv.customer_single_current`, `inv.account_single_current` | 0 artifacts, 18 audits |
| B | `L1.no-phantom-positions` | positions `sg.no-phantom-positions` | `holding_change.sql`, `account_position.sql`, `customer_position.sql` (3 of 3) | 9 of 14 | 0 artifacts, 5 audits |
| C | `L1.placement-moment` | trade-lifecycle `sg.placement-moment` | `trade.sql` (1 of 1) | 8 of 13 | 0 artifacts, 5 audits |

### A. `L1.current-version`: a closed account is still current (recommended)

Current:
> The current statement about a customer or account is the one with no later statement. There is at most one current statement per customer and per account: exactly one while the record stands, and none once its latest statement is a withdrawal under `L1.deletion-withdraws`.

Proposed, appended:
> A statement that closes an account or inactivates a customer does not end its standing: the closed or inactive
> record stays current, as closed or inactive, until a later statement or a withdrawal.

Business meaning: it settles whether "which accounts are current?" includes closed ones. Today the answer only
follows from the fact that no clause says otherwise. A reporting team counting current accounts would split on this.
Prediction: `sg.current-version` moves and nothing else. Jev may score it behavior-neutral for the projection as it
stands (a keep, which also tests the cache's hit-by-jev path), or it may route it to review. Both are informative.
Risk: it touches the same topic as `L1.closed-account-activity` (the parent of `sg.statement-content` and TL
`sg.placement-moment`). Its text would not change, so those fingerprints do not move, but a reviewer should check
the two clauses still agree.

### B. `L1.no-phantom-positions`: report a negative position instead of refusing the load

Current:
> Summing holding changes for any one statement of an account or customer can never go below zero. A negative result means a holding was opened under one statement and closed under another, which the clauses above forbid.

Proposed, second sentence replaced:
> A negative result is reported to the business, naming the account or customer, its statement and the holding
> changes that produced it; it does not stop the load, and no position is adjusted to hide it.

Business meaning: must-hold becomes reported. That is the refuse-or-report choice the chain already makes for
`reports: true` invariants. Prediction: `sg.no-phantom-positions` moves. The L2 recompile would flip
`inv.account_position_not_negative` / `inv.customer_position_not_negative` to `reports: true`, and on sqlmesh their
audits must become `blocking false` (the gate checks that both ways). Every positions artifact derives from this
group, so all 3 are stale by provenance, even though the SQL change is probably confined to 2 audits per engine.
It also needs a counterexample that actually produces a negative sum, and none exists yet
(`ReportedInvariantNeedsACounterexampleTests` would demand one).

### C. `L1.placement-moment`: same-instant pending and submitted reports

Current (first two sentences; the rest unchanged):
> A trade is placed at the moment of the earliest report of it held by the brokerage, as that report states its own time. A trade whose earliest held report is not the trade's first lifecycle event is treated as placed at that report and marked as first seen late, so the ownership it fixes can be reviewed. ...

Proposed, inserted after the second sentence:
> Two reports that state the same moment are one event for this purpose: a limit order whose pending and submitted
> reports state the same time is not first seen late when only the submitted one is held.

Business meaning: it changes which trades are flagged for ownership review. Prediction: `sg.placement-moment` moves.
`trade.sql` is the job's only artifact, so it is stale on both engines; 8 of 13 audits are stale, including
`inv.trade_first_seen_late_matches_status_order`. The weakest candidate: DIGen may not produce a same-timestamp pair
anywhere in the fixture, so the change could be real policy with no witness.

## What this shows about "compile only what's needed"

At ARTIFACT granularity no single-clause change keeps anything. Each job projects one file per entity, and every
entity file derives from nearly every group. The narrowing only shows at audit granularity (A: 18 of 20 kept). If the
demo has to show kept artifacts, one clause is not enough. The model would need finer `derived_from` (per column or
per CTE), or a job with more, smaller artifacts. That is a finding, not something to fix here.

Candidate A is in ownership-history, which `trade-lifecycle` and `positions` read. The fingerprints predict that no
downstream group moves. Whether downstream tables must still be revalidated because an upstream table's content
changed is a separate question the fingerprints do not answer (`L1.current-version` would change `is_current`, and
trade-lifecycle resolves ownership as of an event time rather than by `is_current`). B and C are in leaf or
near-leaf jobs, where no such question arises.
