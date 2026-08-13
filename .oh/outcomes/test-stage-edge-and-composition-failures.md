---
id: test-stage-edge-and-composition-failures
kind: capability
status: achieved
outcome: governed-compositional-etl-repair
s_and_t_step: E2.1
parent_step: E2
sufficiency_group: SG-COMPARISON
owner: data-architect
review_trigger: "Seeded edge and composition cases consistently reduce to ordinary local transformation defects."
files:
  - experiments/preregistration-v2.2.json
  - evidence/issue-7/experiment-result-v2.4.json
  - evidence/issue-7/run-envelope-v2.4.json
  - docs/matched-experiment.md
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

## Current evidence

V2.4 materially observes and repairs distinct governed edge and path failures. Native and stage-local evidence retain both wrong values. The frozen scorer credits only the path because its descendant-array comparison is order-sensitive; the experiment is not rescored after observation.
