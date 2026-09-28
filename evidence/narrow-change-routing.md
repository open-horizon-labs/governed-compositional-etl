# Three narrow L1 changes through the router, measured

2026-09-28. Each candidate from `narrow-change-candidates.md` applied in its own isolated worktree at HEAD, with a
control (no edit) run the same way. Jev given its key (`.env` is gitignored, so worktrees lack it; the first run
had every new-group verdict `not-run` for that reason and is discarded). Deltas are candidate minus control.

## Control

No edit. 11 groups stale across 3 jobs -- loop 2's re-projections awaiting L3 stamps. This residue is why absolute
counts say nothing here; only deltas do.

## Group level: 3 for 3

| | clause changed | groups whose state differs from control | Jev on the new clause | decision |
|---|---|---|---|---|
| A | `L1.current-version` | exactly `ownership-history/sg.current-version` | 0.63, medium | review |
| B | `L1.no-phantom-positions` | exactly `positions/sg.no-phantom-positions` | 0.81, high | invalidate |
| C | `L1.placement-moment` | exactly `trade-lifecycle/sg.placement-moment` | 0.62, medium | review |

Every change moved its predicted group and nothing else, in any job. The Jev decisions are the routing signal
working as designed: B changes must-hold to reported and goes straight to invalidate; A and C are wording that may
or may not change behaviour and escalate to a capable reviewer.

## Artifact and audit level, computed from derivation (what a CLEAN tree would show)

| | job | artifacts stale | audits stale | untouched jobs |
|---|---|---|---|---|
| A | ownership-history | 2 of 2 | 2 of 20 (`inv.customer_single_current`, `inv.account_single_current`) | 2 jobs, everything kept |
| B | positions | 3 of 3 | 9 of 14 | 2 jobs, everything kept |
| C | trade-lifecycle | 1 of 1 | 8 of 13 | 2 jobs, everything kept |

Identical on both engines.

## What this establishes

- Job routing: real. Two of three jobs untouched by every candidate; their projections stay accepted.
- Group routing: real, exact, Jev-decided.
- Audit routing: real. A re-runs 2 of 20 checks.
- Artifact routing: NOT shown. Every entity file derives from nearly every group, so any single-clause change
  rebuilds every table in its job. Selectivity below job level exists only for audits. Showing kept artifacts
  needs finer `derived_from` (per column or per CTE) in the L2 models -- a model change, not a harness change.

## Gotchas found running this

- A worktree has no `.env`; Jev silently returns `not-run`, which routes to invalidate. Copy the key in.
- Stale groups persist until stamped, so an unfinished cycle masks the next change's artifact/audit deltas.
  Measure against a control, or finish the cycle first.
