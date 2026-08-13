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
files: []
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
