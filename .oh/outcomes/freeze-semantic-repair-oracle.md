---
id: freeze-semantic-repair-oracle
kind: objective
status: active
outcome: governed-compositional-etl-repair
s_and_t_step: E1.1
parent_step: E1
sufficiency_group: SG-DIAGNOSE
owner: domain-reviewer
review_trigger: "Reviewers repeatedly disagree about the earliest responsible boundary or permitted repair after seeing the complete business rule."
files:
  - oracle/schema/failure-fixture-v1.schema.json
  - oracle/schema/repair-submission-v1.schema.json
  - oracle/corpus-v1.json
  - scripts/oracle.py
  - tests/test_oracle.py
  - docs/semantic-repair-oracle.md
  - evidence/issue-3/source-anchors-v1.json
---

# Freeze the semantic repair oracle before execution

## Statement

For every seeded failure, record the earliest responsible location, failure class, allowed and forbidden artifact changes, expected output, tempting wrong repair, affected descendants, and held-out neighboring cases before any experiment arm sees the failure.

## Why it matters

Post-hoc labels would allow any plausible repair to be described as correct.

## Enables

Objective scoring of localization, authority, revalidation coverage, and regression escape.

## Acceptance signal

The fixture schema is complete, reviewers agree on the pilot cases, and the experiment runner can score a repair without narrative reinterpretation.

## Current evidence

Issue #3 freezes two adjudicated pilot cases and one unresolved ambiguous case in `oracle/corpus-v1.json`. `scripts/oracle.py verify` validates the authority boundary and scores the example structural submissions without an explanation field. The objective remains active until human review confirms the provisional pilot labels; the adjudication protocol preserves ambiguity if reviewer agreement is unstable.
