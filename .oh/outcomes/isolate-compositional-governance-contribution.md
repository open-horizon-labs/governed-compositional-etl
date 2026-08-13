---
id: isolate-compositional-governance-contribution
kind: objective
status: active
outcome: governed-compositional-etl-repair
s_and_t_step: E2
parent_step: root
sufficiency_group: SG-PROOF
owner: experiment-lead
review_trigger: "The three experiment arms cannot be held equivalent in model, data, reveal order, repair budget, or reviewer access."
files: []
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
