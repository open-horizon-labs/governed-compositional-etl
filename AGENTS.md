# Agent guidance

Read `.oh/tpcdi-governed-etl.md` before planning or implementation.

## Open Horizons workflow

Use the repository’s `.oh/` records as the persistent source of strategic intent.

- Ground work in the recorded aim before choosing a solution.
- Work GitHub issues in dependency order. Each issue carries its S&T lineage, acceptance signal, owner hat, and review trigger.
- Use execution to make bounded progress, then review for drift at natural checkpoints.
- Record durable outcomes, evidence, guardrails, metis, and architectural decisions in repository-native artifacts.
- Use dissent before committing to any deviation from CESS or Compositional CESS.
- Use salvage when repeated reversals or accumulating patches show that the current approach is no longer producing learning.

Do not introduce workflows involving `wm`, `ba`, or `sg` command-line tools.

## Project context

### Purpose and aim

This repository is a spike/demo testing whether governed semantic handoffs and localized downstream revalidation improve repair of type-valid semantic ETL failures beyond native pipeline controls and independent stage-local CESS.

The desired behavior is for data-platform teams to locate the earliest incorrect semantic decision, make one authorized change at the responsible stage, edge, or path invariant, and revalidate every affected downstream result instead of patching a final table or rerunning blindly.

Progress and learning are the point. Prefer a working, evidence-producing vertical slice over premature breadth, production hardening, or framework generalization.

### Current focus

Begin with GitHub issue #2: validate official TPC-DI DIGen and load one trade-oriented vertical slice into persistent DuckDB. Continue through dependent issues in order.

The initial proof is bounded. It does not establish general correctness, production readiness, benchmark performance, or vendor superiority.

### Governing boundaries

- Raw data and a target schema do not authorize business policy.
- Unknown transformations remain explicit Sketch holes until an approved counterexample or named authority resolves them.
- Assumptions may unblock experiment mechanics, but may not silently fill policy holes.
- SQLMesh models, SQLGlot ASTs, generated SQL, and DuckDB tables are replaceable projections, not governing policy.
- Keep the complete accepted-counterexample archive separate from the curated regression set.
- Acceptance requires deterministic approved-output checks and separate review against the current Sketch.
- A stage-local pass does not establish edge or end-to-end correctness.
- Do not describe this work as a compliant TPC-DI benchmark or compare its performance with published TPC results.

### Roles and decisions

The named owners—experiment lead, domain reviewer, data-product owner, data architect, pipeline-platform team, and research sponsor—are conceptual hats rather than necessarily different people. State which hat is making a consequential decision.

The issue owner hat decides ordinary implementation choices. The research-sponsor hat makes the final adoption or rejection decision from the preregistered evidence.

When a review trigger fires:

1. Investigate and collect the relevant evidence.
2. Present the evidence and the available choices.
3. Select a reasonable assumed choice under the responsible hat.
4. Record the decision, assumptions, and justification.
5. Continue on that basis.

Do not use this process to cross a hard governing boundary. Any proposed deviation from CESS or Compositional CESS requires an explicit dissenting review before commitment.

### Evidence and reorientation

Tests, frozen oracle results, reviewer disagreement, affected-descendant coverage, experiment-arm equivalence, operational cost, and domain authority override the current plan.

Pause and reframe when evidence shows that:

- semantic failures cannot be assigned stable oracle labels;
- proposed edge failures reduce to ordinary local defects;
- an affected descendant escapes revalidation;
- experiment arms cannot remain equivalent;
- generated projections become the de facto policy source;
- compositional governance adds no measurable protection beyond stage-local CESS; or
- the cost of the governance layer consumes its demonstrated benefit.

A negative or bounded result is valid progress when it is supported by preserved evidence and a clear decision record.

### Working patterns

- Keep the first vertical slice small, reproducible, and end-to-end.
- Prefer explicit holes and recorded uncertainty over plausible invented policy.
- Separate implementation repair from policy change.
- Preserve enough evidence to reproduce both successful and failed approaches.
- Avoid universal abstractions until the selected slice demonstrates a concrete need.
- Treat production deployment, streaming, UI work, broad workload coverage, and performance benchmarking as out of scope.
