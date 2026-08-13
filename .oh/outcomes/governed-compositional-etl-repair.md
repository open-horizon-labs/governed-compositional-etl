---
id: governed-compositional-etl-repair
kind: outcome
status: active
s_and_t_step: root
owner: experiment-lead
review_trigger: "The bounded experiment cannot distinguish semantic governance from ordinary lineage, tests, or stage-local CESS."
files:
  - .oh/tpcdi-governed-etl.md
---

# Repair semantic ETL failures at the responsible boundary

## Desired behavior change

Data-platform teams turn a reviewed semantic failure into one authorized change at the responsible stage, edge, or path invariant, then revalidate every affected downstream result instead of patching the final table or rerunning the full pipeline without knowing what changed.

## Mechanism

Represent each ETL stage as a CESS-governed semantic decision. Pass evidence-bearing contracts between stages, locate counterexamples at the earliest incorrect boundary, and combine executable lineage with changed semantic fields to select the downstream revalidation slice.

## Feedback

In a frozen TPC-DI-derived vertical slice, the compositional method should localize stage and handoff failures, avoid unauthorized policy edits, cover affected descendants, and preserve prior regressions better than native pipeline controls and independent stage-level CESS. Set numerical adoption thresholds only after the oracle-labeling pilot establishes a credible baseline.
