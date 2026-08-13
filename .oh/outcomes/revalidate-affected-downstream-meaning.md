---
id: revalidate-affected-downstream-meaning
kind: capability
status: achieved
outcome: governed-compositional-etl-repair
s_and_t_step: E4
parent_step: root
sufficiency_group: SG-PROOF
owner: pipeline-platform-team
review_trigger: "An affected descendant escapes the calculated cone or the cone routinely approaches a complete rebuild without reducing operational risk."
files:
  - contracts/revalidation-profile-v1.json
  - evidence/issue-6/revalidation-report-v1.json
  - evidence/issue-7/experiment-result-v2.4.json
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

## Current evidence

Localized replay covers all frozen semantic descendants at precision/recall 1.0/1.0 while restaging 2 models; the comparable full control restages all 6. Both execute the same five checks and six audits. Wall timings are descriptive only.
