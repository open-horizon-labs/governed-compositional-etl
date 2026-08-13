---
id: isolate-compositional-governance-contribution
kind: objective
status: achieved
outcome: governed-compositional-etl-repair
s_and_t_step: E2
parent_step: root
sufficiency_group: SG-PROOF
owner: experiment-lead
review_trigger: "The three experiment arms cannot be held equivalent in model, data, reveal order, repair budget, or reviewer access."
files:
  - scripts/compile_projection.py
  - projection/manifest-v1.json
  - docs/executable-projection.md
  - tests/test_projection.py
  - evidence/issue-5/sqlmesh-execution-v1.json
  - evidence/issue-5/sketch-review-v1.md
  - .oh/metis/issue-5-projection-regeneration.md
  - evidence/issue-7/experiment-result-v2.4.json
---

# Isolate what compositional governance adds

## Statement

Run the same frozen semantic failures through native DuckDB/SQLMesh controls, independent stage-local CESS, and CESS with governed handoffs and affected-slice revalidation.

## Why it matters

A working governed pipeline cannot show whether its additional artifacts caused an improvement.

## Enables

A falsifiable claim about value beyond lineage, audits, and stage-local learning.

## Acceptance signal

All arms use the same raw snapshot, projection starting point, failure order, model, repair attempts, and review budget, with arm-specific context recorded explicitly.

## Current evidence

Issue #5 establishes byte-identical starting projections. Valid issue #7 v2.4 holds raw snapshot, projection, reveal order, one-attempt budget, scripted policy, and zero-model budget fixed; evidence visibility is the treatment. The bounded comparison yields `revise`.
