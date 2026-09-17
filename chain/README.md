# The compile chain

A CESS chain is a chain of compilations, not a data pipeline. Each level's reviewed projection is the next level's Sketch. A counterexample observed at any level is classified to the earliest level whose sketch lost the meaning, and only what derives from that change re-projects.

```text
L1  intent Sketch (business language, hashed clauses, holes)       sketches/l1-brokerage-intent-v1.md
 |   compiled per job by a Developer under a change contract
L2  semantic models: S&T steps with necessity, assumption,          chain/l2/<job>/semantic-model.json (working)
 |   feedback, disposition, sufficiency groups; reviewed, selected   chain/l2/<job>/review.json, selected-model.json (snapshot L3 compiles from)
 |   compiled per engine target by a Developer under a change contract
L3  projections: SQL + audits per entity, provenance to L2 ids      chain/l3/<target>/<job>/
```

The data DAG (customer and account statements, then trades, then holdings and positions) is content inside L2 and L3. The chain is the derivation.

## Artifact register (CESS roles)

| Role | Artifact |
|---|---|
| Sketch `S` | L1: `sketches/l1-brokerage-intent-v1.md`. L2 (for L3): a job's selected `semantic-model.json` |
| Anchors `K` | `chain/anchors/*` (source fields, L2 schema and format, L3 manifest schema, Developer contracts), `chain/profiles/*` (engine capabilities) |
| Projection `P` | L2 models and L3 SQL, written by Developers, disposable |
| CE archive `A` | `chain/ce/accepted/*` (chain-level), `counterexamples/archive/*` (phase-1 and data-level) |
| Regression set `R` | gate rules mechanized from reviews (`scripts/chain_l2.py`, `scripts/chain_l3.py`), `regressions/*` |
| Gate `G` | `chain_l2.py check`, `chain_l3.py check` and `run` |
| Simulator | `chain_l3.py run` over `oracle/fixtures/public/chain-fixture-v1.json` plus labeled constructed rows |
| Sketch reviewer | a capable model given S, K, and the projection only |
| Policy authority | business hat for L1; data-architect hat for K; recorded under `.oh/metis/` |

## Cache and cone

Every L1 clause is hashed on its own. Every L2 sufficiency group is fingerprinted over the clause fingerprints it derives from. `chain_l2.py plan` reports hits and stale groups against `chain/manifest.json`. A hash change is the floor; above it Jev (TypeSafe System One) is asked whether the clause change alters the behavior the group must produce, and answers with a probability. High confidence decides; low confidence routes to the reviewer. `chain/cache-adjudications.jsonl` records the outcomes. L3 artifacts record the L2 element ids they derive from, so a stale group names the SQL to re-project.

## Running a cycle

```bash
.venv/bin/python scripts/chain_l2.py l1                       # parse clauses, holes, jobs
.venv/bin/python scripts/chain_l2.py check <job>              # gate an L2 model
.venv/bin/python scripts/chain_l2.py select <job> --review r.json   # record a review; derive selected steps
.venv/bin/python scripts/chain_l2.py weave                    # cross-job relations
.venv/bin/python scripts/chain_l2.py plan                     # cache: hits, stale groups, Jev verdicts
.venv/bin/python scripts/chain_l2.py commit                   # re-baseline the manifest
.venv/bin/python scripts/chain_l3.py check <target> <job>     # gate an L3 projection
.venv/bin/python scripts/chain_l3.py run <target> <job>       # simulate on the fixture; audits must be empty
```

Developers receive S, K, and a change contract (`chain/anchors/DEVELOPER-CONTRACT-*.md`, plus a per-cycle contract under the job directory). They never receive the CE archive, the reference material under `oracle/`, or another level's Sketch. Reviewers receive S, K, and the projection. Each review that finds something the gate could have found becomes a gate rule.

## Status

See `.oh/tpcdi-governed-etl.md` for the cycle log.

- **L1:** 14 hashed clauses (the newest, `L1.unknown-codes`: a report carrying a code outside the vocabulary is held as a whole, keeps its place in the order of reports, changes nothing, creates nothing, and is reported), 9 holes (two opened this session: a market order seen pending; a trade whose placement-fixing facts would come from a held report). `L1.placement-moment` amended by accepting `ce.l1.first-seen-late-market-orders`.
- **L2 selected, all three jobs:** ownership-history (12 cycles), trade-lifecycle (17), positions (9). Weave: no uncovered clause, seven cross-job dependencies, thirteen named gaps.
- **L3 accepted and stamped on both engines:** ownership-history 17 audits, trade-lifecycle 13, positions 14. Mutation testing zero unprotected everywhere; cross-engine compare identical for every job; two filed questions for authority (a D-only holding pair; the constructed source's status vocabulary).
- **Counterexamples that run** (`counterexamples/proposed/`, `chain_l3.py simulate`): trade before its account's first statement; a tie between historical holding reports; an unanchored holding flag; a market order first seen submitted against a limit twin; six held-for-review trades (pending market order, unknown type, unknown later status, unknown flag, held first report, held first CDC report). Each fires the same audits on both engines or is silent on both.
- **Cache mechanics demonstrated:** a rewording of a clause moved its hash and Jev kept the one derived group (0.15, high); a rule change moved the same hash and Jev routed it to review (0.68, medium), adjudicated invalidate; a new clause nobody cited appeared as a weave gap until each L2 covered it; text-only L2 and L1 changes fall through to fingerprint fallbacks and stale projections nothing.
- **Awaiting authority:** the assumed L1 decisions (statement content, constructed scenarios, placement moment, omitted facts stand, the two unknown-codes clarifications); proposals in `chain/ce/proposed/`; the standing anchor question on NEW, UPDCUST, UPDACCT status.
