---
id: issue-6-replay-review-trigger
status: resolved
owner_hat: pipeline-platform-team
trigger: harness proof did not execute a comparable calculated cone and full replay
---

# Issue #6 replay review trigger

## Evidence

The initial report computed the correct frozen semantic cone and ran its checks, but both the cone and “full replay” audited a shared already-materialized database. It therefore did not establish which SQLMesh models were actually refreshed, whether dependencies were ordered, or whether scored answers came from replayed data.

## Choices

1. Stop the method because the semantic cone is invalid.
2. Keep the semantic method and replace the insufficient execution harness.
3. Report calculated node counts as replay evidence.

## Decision

Under the pipeline-platform-team hat, select choice 2. The semantic cone still exactly matched the independently frozen descendant oracle; the failed assumption concerned execution evidence, not the CESS or compositional method. Choice 3 would cross the evidence boundary and is rejected.

## Resolution

Each comparison now receives an isolated persistent DuckDB copy and regenerated SQLMesh project. The cone restates two affected models in dependency order and records four verified required ancestors. The control restates all six models. Active and curated submissions are derived from replayed tables. Wrong semantic values remain structurally valid but fail live scoring. The review trigger is resolved for this bounded run; any escaped descendant or inability to perform comparable replay will fire it again.
