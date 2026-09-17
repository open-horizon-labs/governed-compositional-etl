# The compile chain

A CESS chain is a chain of compilations, not a data pipeline. Each level's reviewed projection is the next level's Sketch. A counterexample observed at any level is classified to the earliest level whose sketch lost the meaning, and only what derives from that change re-projects.

```text
L1  intent Sketch (business language, hashed clauses, holes)       sketches/l1-brokerage-intent-v1.md
 |   compiled per job by a Developer under a change contract
L2  semantic models: S&T steps with necessity, assumption,          chain/l2/<job>/semantic-model.json
 |   feedback, disposition, sufficiency groups; reviewed, selected   chain/l2/<job>/review.json
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

See `.oh/tpcdi-governed-etl.md` for the cycle log. Selected: `ownership-history` L2 (nine cycles) and its `duckdb-native` L3 projection (reviewed, 11 audits clean). In flight: `trade-lifecycle` L2, `ownership-history` on `duckdb-sqlmesh`. Not started: `positions`. Assumed decisions awaiting business confirmation, each one hashed clause: what a statement carries (`L1.statement-content`); constructed scenarios never introduce new things (`L1.constructed-scenarios`); the placement moment (`L1.placement-moment`); omitted facts stand as last stated (`L1.omitted-facts-stand`). Proposed and undecided: how a late first encounter differs from a market order that begins at submitted (`chain/ce/proposed/`).
