---
id: revalidate-affected-downstream-meaning
kind: capability
status: active
outcome: governed-compositional-etl-repair
s_and_t_step: E4
parent_step: root
sufficiency_group: SG-PROOF
owner: pipeline-platform-team
review_trigger: "An affected descendant escapes the calculated cone or the cone routinely approaches a complete rebuild without reducing operational risk."
files: []
---

# Revalidate affected downstream meaning

## Statement

The pipeline combines executable lineage, changed semantic contract fields, retained regressions, and path invariants to select all affected downstream behavior after an authorized repair.

## Why it matters

Rerunning too little permits regressions; rerunning everything does not demonstrate bounded consequences.

## Enables

Measured revalidation precision and recall rather than unqualified claims about smaller blast radius.

## Acceptance signal

The selected cone covers every frozen affected descendant and reports unnecessary recomputation separately from escaped regressions.
