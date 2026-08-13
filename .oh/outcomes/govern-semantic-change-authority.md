---
id: govern-semantic-change-authority
kind: capability
status: active
outcome: governed-compositional-etl-repair
s_and_t_step: E3
parent_step: root
sufficiency_group: SG-PROOF
owner: data-product-owner
review_trigger: "Existing repository controls prevent unauthorized semantic repairs with equal clarity and lower operating cost."
files:
  - sketches/trade-dim-v1.md
  - contracts/schema/source-v1.schema.json
  - contracts/schema/logical-model-v1.schema.json
  - contracts/schema/semantic-types-v1.schema.json
  - contracts/schema/stage-contract-v1.schema.json
  - contracts/schema/edge-contract-v1.schema.json
  - contracts/schema/repair-authority-v1.schema.json
  - contracts/artifact-classification-v1.json
  - scripts/contracts.py
  - tests/test_contracts.py
  - evidence/issue-4/candidate-edge-adjudication-v1.json
---

# Govern semantic change authority

## Statement

Every repair identifies whether it may change classification, policy, projection, verification, an edge contract, or a path invariant, and names the authority allowed to approve that change.

## Why it matters

A technically successful repair can silently redefine business meaning.

## Enables

Auditable counterexample promotion and rejection of tempting unauthorized repairs.

## Acceptance signal

The experiment detects and reports every seeded edit outside the frozen allowed artifact set, including policy changes made to repair implementation defects.

## Current evidence

Issue #4 establishes the bounded contract and authority formats, validates explicit holes and projection classification, and adjudicates the historical lifecycle candidate through independent local and handoff checks. The capability remains active until the matched experiment measures unauthorized edits across all arms.
