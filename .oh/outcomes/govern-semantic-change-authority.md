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
files: []
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
