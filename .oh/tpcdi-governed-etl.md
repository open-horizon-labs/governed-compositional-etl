# TPC-DI-derived governed compositional ETL

## Aim

**Aim:** Data-platform teams turn a reviewed semantic ETL failure into one authorized change at the responsible stage, edge, or path invariant, then revalidate every affected downstream result instead of patching a final table or rerunning blindly.

**Why it matters:** Type-valid semantic errors can pass execution, schema, and local quality checks while corrupting downstream warehouse meaning.

**Current state:** Teams use logs, tests, lineage, and local repair, but responsibility for meaning and downstream proof obligations often remain implicit.

**Desired state:** A failure has a scored location, change authority, executable protection, evidence trail, and bounded downstream revalidation set.

### Mechanism

**Change:** Compose CESS-governed stages using semantic contracts that carry grain, identity, units, time meaning, evidence, rule IDs, confidence, verification, and disposition.

**Hypothesis:** Governed handoffs and localized revalidation will catch stage-edge and composition failures that native ETL controls and independent stage-level CESS miss.

**Assumptions:** Reviewers can establish a stable oracle for a bounded vertical slice; SQLMesh lineage plus semantic contracts can identify affected descendants; evidence can be retained at batch or decision-class granularity without copying it into every warehouse row.

**Misunderstanding signal:** The implementation becomes another dbt/SQLMesh project whose SQL and tests carry policy implicitly, or reports smaller reruns without proving affected-descendant coverage.

### Feedback

**Signal:** Compare native controls, stage-local CESS, and compositional CESS on frozen type-valid semantic failures.

**Timeframe:** Establish the oracle and one end-to-end trade vertical slice before scaling the workload.

### Guardrails

- Raw data and schemas do not authorize missing policy.
- Keep Sketch, anchors, projection, complete CE archive, curated regression set, deterministic gate, and Sketch review distinct.
- Do not publish the work as a compliant TPC-DI benchmark or compare derived performance with official TPC results.
- Stop if the compositional arm does not add measurable protection beyond stage-local CESS.

## Problem Space

TPC-DI supplies heterogeneous raw source files, source and destination models, transformation rules, historical loading, incremental updates, verification requirements, and a scalable generator. The complete specification can act as a hidden oracle while an open-world arm begins with raw files, structural anchors, and an incomplete Sketch.

DuckDB provides an in-process columnar execution engine with persistent storage and larger-than-memory spill. SQLMesh supplies the executable model DAG, audits, change planning, and DuckDB integration. SQLGlot supplies parsed SQL expression trees and dialect-aware generation. None of these tools should own business policy.

The initial scope is one retail-brokerage vertical slice through raw parsing, semantic normalization or classification, identity/history, a logical fact or dimension, a physical DuckDB materialization, and an end-to-end invariant. Performance benchmarking, broad platform comparison, UI work, streaming, and production deployment are out of scope.

## Problem Statement

Data teams need to determine where a structurally valid warehouse value first acquired the wrong meaning and repair it under the correct authority, but executable lineage shows dependency rather than semantic responsibility, while stage-local tests and CESS do not establish that producer and consumer meanings are compatible.

## Problem Weave

### Shared Core

The experiment must distinguish execution failure from semantic failure, stage failure from handoff failure, implementation repair from policy change, and efficient revalidation from unsafe under-testing.

### Interwoven S&T Steps

| ID | Parent | Depth | Strategy | Tactic | Disposition | Necessity | Parallel assumption | Sufficiency group | Owner | Review trigger |
|---|---|---:|---|---|---|---|---|---|---|---|
| E1 | root | 1 | Make semantic failures objectively diagnosable | Seed structurally valid cases with frozen semantic responsibility | selected | Ordinary syntax and null failures only retest existing platform controls | A bounded TPC-DI slice can supply realistic type-valid failures | SG-PROOF | experiment-lead | Native controls locate them equally well |
| E1.1 | E1 | 2 | Establish a fair repair oracle | Freeze location, class, authority, expected output, wrong repair, descendants, and held-outs | selected | Post-hoc labels can rationalize any repair | Reviewers can agree on a small corpus before execution | SG-DIAGNOSE | domain-reviewer | Reviewer agreement is unstable |
| E2 | root | 1 | Isolate the compositional contribution | Compare native controls, stage-local CESS, and compositional CESS | selected | A single successful implementation cannot attribute its success | Matching model, data, order, and budgets separates the added layer | SG-PROOF | experiment-lead | Conditions cannot remain equivalent |
| E2.1 | E2 | 2 | Test the claimed boundary distinctions | Include stage, edge, and end-to-end composition failures | selected | The method adds little if every failure reduces to one stage | A type-valid unit or temporal mismatch can pass local checks | SG-COMPARISON | data-architect | Edge cases reduce to local bugs |
| E3 | root | 1 | Prevent unauthorized semantic repair | Declare allowed artifacts, forbidden changes, and approver roles | selected | Technical success can silently redefine business meaning | Frozen authority makes violations countable | SG-PROOF | data-product-owner | Existing controls prevent violations equally well |
| E4 | root | 1 | Revalidate all and only affected downstream meaning | Combine lineage, semantic deltas, regressions, and path invariants | selected | Under-testing escapes regressions; full replay hides boundedness | The small DAG permits an exhaustive affected-descendant oracle | SG-PROOF | pipeline-platform-team | The cone misses descendants or approaches full replay |
| E5 | root | 1 | Decide whether the method is worth its cost | Measure repair safety, coverage, operator time, model use, and compute | selected | More governance is not automatically better | A pilot can set a credible minimum effect and cost ceiling | SG-PROOF | research-sponsor | No benefit survives full cost accounting |

### Sufficiency Groups

| Group | Parent strategy | Child steps | Mode | Coverage claim | Gap |
|---|---|---|---|---|---|
| SG-PROOF | root | E1, E2, E3, E4, E5 | all required | Together they establish cases, comparison, authority, downstream safety, and rejection criteria | External validity beyond one workload remains open |
| SG-DIAGNOSE | E1 | E1.1 | all required | A frozen oracle is the minimum basis for scoring diagnosis | Adjudication protocol must be defined |
| SG-COMPARISON | E2 | E2.1 | all required | The comparison must exercise the boundary types the method claims to add | Temporal and streaming failures are deferred |

### Opposition and Uncertainty

- SQLMesh planning, lineage, audits, and conventional contracts may already solve enough of the problem.
- Evidence may belong per row, batch, partition, or exceptional decision; the cheapest sufficient granularity is unknown.
- Full replay may be safer and cheaper than localized revalidation at small scale.
- TPC-DI is now listed as obsolete; its workload remains useful, but fair-use and naming constraints require human review before publication.

## Solution Space

### Solution Space Analysis

**Problem:** Build a large, reproducible raw-to-warehouse experiment that tests governed semantic composition rather than database performance.

**Key Constraint:** Preserve policy outside generated SQL while keeping the executable substrate realistic enough that lineage, audits, and planning are strong baselines.

**Working Story:** Use a TPC-DI-derived workload as the semantic oracle, compile partial Sketches and structural anchors into SQLMesh models backed by DuckDB, and use SQLGlot for AST-level SQL generation and inspection.

**Success Signal:** A type-valid stage-edge failure passes native and local-stage checks, is rejected by a governed contract or path invariant, and is repaired without unauthorized policy change or missed affected descendants.

**Decision Criteria:** Semantic richness, scalable raw data, reproducibility, strength of baseline controls, artifact separation, bounded implementation cost, and publishable evidence.

**Critical Assumptions:** Current DIGen tools run in the development environment; one vertical slice can be ported without implementing the whole benchmark; SQLMesh and SQLGlot expose enough dependency information; TPC fair-use requirements permit the intended research artifact with correct labeling.

### Candidates Considered

| Option | Level | Approach | Main trade-off |
|---|---|---|---|
| A | Local optimum | TPC-DI with dbt and DuckDB | Familiar DAG and tests, but Jinja SQL and adapter behavior add policy and analysis ambiguity |
| B | Reframe | TPC-DI with SQLMesh, SQLGlot, and DuckDB | Strong planning and AST substrate with a smaller ecosystem |
| C | Redesign | Custom semantic compiler using SQLGlot and DuckDB | Maximum control but risks spending the experiment on infrastructure |
| D | Alternate frame | Synthea to OMOP on DuckDB | Rich semantics but healthcare expertise and safety dominate the method test |

### Recommendation

**Selected:** Option B — TPC-DI-derived vertical slice using SQLMesh, SQLGlot, and persistent DuckDB.

**Level:** Reframe.

Use the complete TPC-DI rules as a hidden closed-world oracle. Give the open-world arm only raw files, source and target structural anchors, and an incomplete Sketch. Compile accepted policy into replaceable SQLMesh and SQLGlot projections. Store evidence at batch or decision-class granularity unless a failure requires row-level provenance.

### S&T Selection

| Step ID | Disposition | Parent | Sufficiency group | Why | Owner | Review trigger |
|---|---|---|---|---|---|---|
| E1 | selected | root | SG-PROOF | Required to create meaningful semantic failures | experiment-lead | Native controls locate them equally well |
| E1.1 | selected | E1 | SG-DIAGNOSE | Required to prevent post-hoc scoring | domain-reviewer | Reviewer agreement is unstable |
| E2 | selected | root | SG-PROOF | Required to isolate the method's contribution | experiment-lead | Conditions cannot remain equivalent |
| E2.1 | selected | E2 | SG-COMPARISON | Required to test stage-edge and composition claims | data-architect | Edge cases reduce to local bugs |
| E3 | selected | root | SG-PROOF | Required to detect unauthorized policy changes | data-product-owner | Existing controls work equally well |
| E4 | selected | root | SG-PROOF | Required to test bounded downstream consequences | pipeline-platform-team | Cone misses descendants or becomes full replay |
| E5 | selected | root | SG-PROOF | Required for a falsifiable adoption decision | research-sponsor | Benefits disappear after costs are counted |

**Selected-step sufficiency:** All selected root siblings in SG-PROOF and both required child groups are present. The plan may proceed for the bounded vertical slice.

### Risk Retirement Plan

| Risk | Disposition | Tempting patch to reject | Required evidence | Stop or pivot if |
|---|---|---|---|---|
| TPC-DI tooling is unusable | Retired by evidence | Replace the raw generator with hand-authored fixtures while still claiming workload fidelity | Run current DIGen at a small scale and retain commands and checksums | Tools cannot run reproducibly |
| Policy leaks into SQL | Retired by evidence | Hand-edit generated SQL to fix an active case | Freshly regenerate the projection from Sketch plus anchors and pass both checks | Regeneration needs archive examples or manual SQL policy |
| Edge failures are really local defects | Pending issue #4 contract adjudication | Rename a local bug as a contract failure | Freeze a case where both local stage checks pass but meanings are incompatible | Reviewers assign every case locally |
| Smaller revalidation is unsafe | Retired by evidence | Report fewer models rerun as success | Measure precision and recall against an exhaustive descendant oracle | Any affected descendant escapes |
| Existing tooling is sufficient | Triggered | N/A | Compare with native SQLMesh/DuckDB and stage-local CESS arms | Added governance does not reduce meaningful failures |
| TPC fair-use constraints | Accepted with rationale pending human review | N/A | Avoid TPC performance claims; obtain human review before publishing derived results | Intended publication is not permitted |

### Execution Handoff

- Preserve the separation of Sketch, anchors, projection, archive, regression set, deterministic gate, and Sketch review.
- Verify one end-to-end vertical slice before expanding breadth or scale.
- Keep all experiment arms equivalent except for the governance layer under test.
- Reject repairs that infer policy from raw data or target structure without authority.
- Stop if no genuine edge or composition case survives oracle review.

## Plan

**Updated:** 2026-08-12 22:19 EDT

| S&T Step | Disposition | Issue/Epic | Parent Step | Depends On |
|---|---|---|---|---|
| root | tracking | [#1](https://github.com/open-horizon-labs/governed-compositional-etl/issues/1) | none | none |
| E1 | selected | [#2](https://github.com/open-horizon-labs/governed-compositional-etl/issues/2) | root | none |
| E1.1 | selected | [#3](https://github.com/open-horizon-labs/governed-compositional-etl/issues/3) | E1 | #2 |
| E3 | selected | [#4](https://github.com/open-horizon-labs/governed-compositional-etl/issues/4) | root | #2 |
| E2 | selected | [#5](https://github.com/open-horizon-labs/governed-compositional-etl/issues/5) | root | #3, #4 |
| E4 | selected | [#6](https://github.com/open-horizon-labs/governed-compositional-etl/issues/6) | root | #5 |
| E2.1 | selected | [#7](https://github.com/open-horizon-labs/governed-compositional-etl/issues/7) | E2 | #3, #5, #6 |
| E5 | selected | [#8](https://github.com/open-horizon-labs/governed-compositional-etl/issues/8) | root | #7 |

### Workflow handoff

Execute issues in dependency order. Begin with `/oh-task 2`; use #1 only as the tracking issue for the complete selected proof.
