---
id: test-stage-edge-and-composition-failures
kind: capability
status: active
outcome: governed-compositional-etl-repair
s_and_t_step: E2.1
parent_step: E2
sufficiency_group: SG-COMPARISON
owner: data-architect
review_trigger: "Seeded edge and composition cases consistently reduce to ordinary local transformation defects."
files: []
---

# Test stage, edge, and composition failures separately

## Statement

The experiment can inject and score perception, policy, projection, verification, producer-consumer contract, and end-to-end composition failures.

## Why it matters

The proposed method adds little if every failure can already be assigned to one independent CESS stage.

## Enables

Direct evaluation of governed handoffs and path invariants.

## Acceptance signal

At least one type-valid edge failure passes both local stage checks but fails the governed handoff or path invariant.
