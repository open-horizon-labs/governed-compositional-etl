---
id: diagnose-semantic-etl-failures
kind: objective
status: active
outcome: governed-compositional-etl-repair
s_and_t_step: E1
parent_step: root
sufficiency_group: SG-PROOF
owner: experiment-lead
review_trigger: "Native controls locate the seeded semantic failures with equal accuracy and less evidence overhead."
files: []
---

# Make semantic ETL failures objectively diagnosable

## Statement

Create structurally valid but semantically wrong cases whose responsible stage, handoff, authorized repair surface, and affected descendants can be scored before any repair begins.

## Why it matters

Syntax errors, nulls, and failed jobs mainly test capabilities that modern data platforms already provide. The method claims value at semantic boundaries.

## Enables

A controlled comparison of native checks, stage-local CESS, and governed compositional CESS.

## Acceptance signal

Two reviewers can assign stable oracle labels to the initial vertical-slice failures, including at least one genuine handoff failure that does not reduce to a local implementation defect.
