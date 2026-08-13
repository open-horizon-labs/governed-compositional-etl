---
id: governed-compositional-etl-repair
kind: outcome
status: paused
s_and_t_step: root
owner: experiment-lead
review_trigger: "The bounded experiment cannot distinguish semantic governance from ordinary lineage, tests, or stage-local CESS."
files:
  - .oh/tpcdi-governed-etl.md
  - docs/bounded-experiment-report.md
  - evidence/issue-8/bounded-decision-v1.json
---

# Repair semantic ETL failures at the responsible boundary

## Desired behavior change

Data-platform teams turn a reviewed semantic failure into one authorized change at the responsible stage, edge, or path invariant, then revalidate every affected downstream result instead of patching the final table or rerunning the full pipeline without knowing what changed.

## Mechanism

Represent each ETL stage as a CESS-governed semantic decision. Pass evidence-bearing contracts between stages, locate counterexamples at the earliest incorrect boundary, and combine executable lineage with changed semantic fields to select the downstream revalidation slice.

## Feedback

In a frozen TPC-DI-derived vertical slice, the compositional method should localize stage and handoff failures, avoid unauthorized policy edits, cover affected descendants, and preserve prior regressions better than native pipeline controls and independent stage-level CESS. Set numerical adoption thresholds only after the oracle-labeling pilot establishes a credible baseline.

## Bounded decision

The experiment is complete and the research-sponsor decision is `revise`. Materialized evidence shows protection beyond native and stage-local controls, but the frozen scorer credits one composition catch and active repair 0.5, below adoption thresholds. Expansion is paused until a new preregistration corrects the scorer contract and repeats the bounded comparison.
