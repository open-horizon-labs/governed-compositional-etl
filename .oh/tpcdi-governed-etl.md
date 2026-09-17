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
| Edge failures are really local defects | Retired for the bounded historical case by issue #4 evidence | Rename a local bug as a contract failure | Freeze a case where independent producer and consumer checks pass but meanings are incompatible | Reviewers assign every case locally |
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

**Execution status (2026-08-13):** Issues #2–#7 produced the bounded slice and valid v2.4 comparison. Issue #8 records `revise`: materially promising compositional protection, but the frozen scorer credits one of two composition catches and active repair 0.5, so adoption and scope expansion are paused pending a newly preregistered correction.

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

## Aim (phase 2, 2026-09-16): chained lifecycle example

**Aim:** A warehouse engineer reading this repo can follow one realistic multi-stage TPC-DI change, incremental trade completion after an account SCD2 rollover, and see each stage governed by its own Sketch and counterexamples, with the lifecycle mutation policy caught and repaired as a semantic-role violation rather than as an incident-specific test they would have had to think of.

**Why it matters:** The phase-1 slice proved the mechanism on a four-file historical trade path with a status-constant style failure. Practitioners like Dave will not recognize their own defects in it. If the example does not look like a real dimensional-modeling mistake, the method reads as ceremony and nobody adopts the governance layer.

**Current State:** One Sketch (`trade-dim-v1`), one edge contract, a single logical dim, zero model calls, and six explicit holes including `source.incremental-cdc`, `edge.incremental-update-lifecycle`, and `dim-trade.security-account-keys`. Readers see a bounded proof, not a chain.

**Desired State:** A chain Customer CDC -> DimCustomer SCD2 -> Account CDC -> DimAccount SCD2 -> Trade CDC (SBMT -> CMPT) -> DimTrade incremental MERGE -> HoldingHistory -> FactHoldings -> position metrics, where each stage has a Sketch plus CE archive, the three holes above are closed by named TPC-DI rules or accepted CEs, and one controlled CE (account 428 rollover before the trade 372101 CMPT) drives a `frozen_from_first_encounter` violation that the compiler physically prevents in the regenerated MERGE. The conventional restricted-MERGE repair is shown alongside, not strawmanned.

### Mechanism

**Change:** Extend the Sketch set and contracts to a chained pipeline; add insert-versus-update column roles (`mutable`, `frozen_from_first_encounter`) to the lifecycle contract; make the projection compiler emit MERGE update lists from those roles; add the account-rollover CE and its curated regression; propagate semantic descendants into holdings revalidation. Separately, evaluate Jev (Typesafe.ai) as the selector for composite CESS choice, as a new model-in-the-loop arm.

**Hypothesis:** Column mutation roles are the cheapest policy artifact that distinguishes "valid FK to current version" from "correct historical attribution", so a role violation localizes the failure at the DimTrade edge and names holdings as affected without a bespoke regression. Chaining Sketches shows CE archives evolving per stage rather than one monolithic policy.

**Assumptions:**
- TPC-DI 1.1.0 clauses on DimTrade key binding and FactHoldings key resolution are specific enough to serve as named authority for closing the three holes. Must be verified against the spec text before the holes are marked resolved.
- DIGen SF3 Batch2 contains account 428, trade 372101, and the 353232 -> 372101 holding change as described, and Customer/Account CDC files exist in Batch2/Batch3 with enough rows to build SCD2 versions without synthesis beyond the one labeled CE.
- The existing compiler (SQLGlot-built expressions) can be extended to MERGE generation in DuckDB without abandoning the replaceable-projection principle.
- Jev exposes an API suitable for ranking or selecting among candidate CESS compositions; its output can be logged as evidence and scored under the existing frozen-scorer discipline. Unverified: what Jev actually does. Verify before designing the arm.
- Adding a model-driven arm does not contaminate the deterministic arms; it must be run and reported separately with model calls and tokens counted, since phase 1 reports zero.

**Misunderstanding Signal:** Someone ports the example to plain SQLMesh with a restricted MERGE and a regression query and says "same thing, less machinery". If the repo cannot show what the role contract caught that their regression would not have caught until the incident, the aim was missed even though the feature shipped. A second signal: Jev gets wired in as a demo integration rather than as a measured arm.

### Feedback

**Signal:** A reader-facing walkthrough where the account-rollover CE produces the stage-by-stage PASS/FAIL/AFFECTED diagnosis, the regenerated MERGE update list excludes frozen columns, and the holdings revalidation cone names FactHoldings and position metrics. Secondary: at least one external practitioner reviews the example and identifies it as a defect they have seen, without prompting. For Jev: a preregistered comparison of composite selection with and without it, reported with model calls and tokens.

**Timeframe:** Chain and CE runnable in DuckDB before any Jev integration. Jev evaluation is gated on confirming what the product does.

### Guardrails

- The account-428 rollover is labeled a controlled CE. Never present it as DIGen output.
- Closing a hole requires a named TPC-DI clause or an accepted CE; the raw Batch2 coincidence does not authorize policy.
- The conventional repair is shown as legitimate and complete for its scope; the comparison is about where policy lives and what is caught generically.
- Frozen scorer and phase-1 valid run are never rescored; phase 2 is a new preregistration.
- Secrets: `.env` at repo root, added to `.gitignore` (currently absent), variable `TYPESAFE_API_KEY`, with a committed `.env.example` holding the name only. Scripts read it via environment, never hardcoded.
- Stop if the role contract cannot be expressed without encoding column names as policy, or if MERGE generation forces policy into SQL.
- The two companion cases (cash balance across account SK rollover, security SCD across the 52-week window) are recorded as candidates, not built, until the main chain runs.

## Problem Space (phase 2, 2026-09-16)

**Scope:** Extending the bounded historical trade slice into a chained incremental pipeline (Customer/Account SCD2 -> DimTrade incremental -> HoldingHistory -> FactHoldings -> position metrics), governed per stage by Sketch plus CE archive, with one controlled account-rollover CE, and adding Jev (TypeSafe System One) as a measured fourth arm for composite CESS selection.

### Objective
A practitioner reads the repo and recognizes a defect they have shipped: an incremental MERGE that rebinds an existing trade's dimension surrogate keys to the current SCD version. They see it localized as a `frozen_from_first_encounter` role violation at the DimTrade edge, repaired by regenerating the projection from a changed contract, and see holdings named as affected. Success is recognition and a runnable diagnosis, not another table.

### Constraints
| Constraint | Type | Reason | Question? |
|---|---|---|---|
| Raw data, schemas, and projections never authorize policy (guardrail `no-policy-from-structure`) | hard | Core thesis; violating it collapses the method into ordinary SQLMesh | No |
| Closing a Sketch hole requires a named TPC-DI clause or an accepted CE | hard | Same guardrail; the three holes this example closes are already declared | No |
| Phase-1 valid v2.4 run is never rescored; phase 2 is a new preregistration | hard | Metis from v1, v2 attempt A, v2.1, v2.3 invalidations: post-hoc changes destroy the evidence | No |
| Account 428 rollover is a controlled CE, labeled as such | hard | No Batch2/Batch3 Account CDC row exists for 428 (verified) | No |
| Deterministic arms stay zero-model; Jev is a separate arm with calls and tokens counted | hard | Phase 1 reports zero model usage; mixing would break the matched comparison | No |
| Everything runs locally in DuckDB via SQLMesh/SQLGlot | soft | Reproducibility and the existing compiler | Could switch engine, but nothing in the aim requires it |
| Column roles must be expressed without hardcoding column names as policy | soft | Otherwise roles are just another allowlist in SQL | Semantic types already exist in contracts; roles can attach to types |
| TPC-DI 1.1.0 is the only named external authority | soft | Fair use and the frozen oracle discipline | Kimball SCD literature could be cited for general rules, but not as authority here |
| Compiler extension to MERGE stays within the replaceable-projection principle | assumed | The compiler currently renders stage queries and audits, not MERGE | Verify SQLMesh 0.236.1 INCREMENTAL_BY_UNIQUE_KEY on DuckDB 1.5.5 emits usable MERGE or delete-insert; if not, the role check must live in the audit layer instead |
| Jev is nondeterministic or undocumented on determinism | assumed | Docs say nothing about reproducibility | Scored quantities must derive from logged answers, never from reruns |
| Publication stays bounded, non-benchmark, human-gated | hard | TPC fair use; TPC-DI is listed obsolete | No |

### Terrain
- **Systems:** DIGen SF3 output (Batch1 historical, Batch2/3 CDC), the existing contracts and compiler (`scripts/compile_projection.py`, 881 lines, JSON-pointer parameterized), SQLMesh 0.236.1, DuckDB 1.5.5, the frozen oracle and scorer, sealed custody, Jev via `typesafe-sdk` (`jev-latest`, currently 1.13.0).
- **Data facts (verified):** trade 372101 is Batch1 PNDG (TLS, account 428, security AAAAAAAAAAAABFV) then Batch2 `U` SBMT 00:57:49 and `U` CMPT 00:59:31. Trade 353232 is a Batch1 CMPT TLB buy of 5225 on the same account and security. Batch2 HoldingHistory row `I|1488406|353232|372101|5225|0` closes that position. Account 428 appears twice in Batch1 CustomerMgmt.xml and never in Batch2/3 Account CDC. Batch2 Account CDC has 30 rows, Customer CDC 15, Trade 570, HoldingHistory 218. The security exists in FINWIRE1985Q1.
- **Stakeholders:** data-product-owner, domain-reviewer, data-architect, research-sponsor hats; the external practitioner audience; TypeSafe as a vendor whose product becomes part of the comparison.
- **Blast radius:** if roles are miscast, the example teaches a wrong rule with authority language attached. If the Jev arm leaks scorer truth into state, the whole phase-2 comparison is invalid, repeating the v1 failure mode. If the hole closures cite clauses loosely, the repo loses its named-authority discipline.
- **Precedents/metis:** `raw-and-target-model-underdetermine-etl` (SCD policy is exactly the kind of meaning raw data cannot supply). `issue-5-projection-regeneration` (one canonical compiled project copied byte-identically into every arm). `issue-6-replay-review-trigger` (replay evidence must come from actually refreshed models). Five harness invalidations, all evidence defects, never method defects. The v2.4 scorer list-order false negative is the open revise item and must be fixed in the new preregistration, not patched.

### Situation Model
- **Explains:** The phase-1 Sketch already left `source.incremental-cdc`, `edge.incremental-update-lifecycle`, and `dim-trade.security-account-keys` open. The chained example is the authorized closure of those holes, which is why it demonstrates CE evolution honestly. The controlled rollover CE is needed because DIGen did not produce the coincidence, and the rule it exercises is named in TPC-DI. Jev fits as a judge over code-constructed state answering Choice/Noul/Score questions; it cannot read the database or the CE archive, so what it sees is a design decision that must be frozen.
- **May hide:** Whether the incremental DimTrade clause is specific enough about which dimension version binds at first encounter, versus leaving it to the historical-load clause. Whether FactHoldings key resolution through the current trade is stated as a rule or only implied by the schema. Whether a Choice over candidate compositions is even the right Jev question, versus Noul checks per role with code doing the selection (composite scoring pattern). Whether the practitioner recognition signal can be observed at all inside this repo.
- **Evidence quality:** data facts observed. Compiler and contract shapes observed. Jev API behavior observed for one call. TPC-DI clause specificity for incremental DimTrade and FactHoldings assumed pending spec read. SQLMesh MERGE behavior on DuckDB assumed. Jev determinism unknown.

### Assumptions and Open Questions
- TPC-DI 1.1.0 names the first-encounter key binding for incremental DimTrade updates and current-trade key resolution for FactHoldings specifically enough to be cited as authority. Risk if false: the holes stay open and the CE becomes the sole authority, which the guardrail permits but weakens the example. Answer before writing contracts; read the spec sections on incremental DimTrade and FactHoldings.
- Customer and Account CDC in Batch2/3 plus Batch1 CustomerMgmt.xml can build DimCustomer and DimAccount SCD2 without synthesis beyond the one labeled CE. Risk: scope explodes into full CustomerMgmt XML parsing. Answer during solution space by measuring the minimal XML slice needed for account 428 and its customer.
- SQLMesh 0.236.1 can materialize an incremental-by-unique-key model on DuckDB 1.5.5 in a way the compiler can constrain by column role. Risk: role enforcement moves to audits and the "physically cannot write frozen columns" claim weakens to "is rejected before execution". Answer with a spike before preregistration.
- Jev's state construction can exclude scorer truth, held-out submissions, and CE archive contents while still giving it enough to judge. Risk: a v1-style leak. Answer by adding Jev state to the compiler input allowlist discipline and the custody verifier.
- Jev answers are logged per call and scored from logs; reruns are never used to improve a score. Risk: nondeterminism becomes tuning. Answer in preregistration.
- The v2.4 scorer list-order defect is corrected and frozen before any phase-2 run. Risk: same false negative recurs. Answer first, it is the outstanding issue #8 revise item.
- What Jev is asked matters more than that it is asked. Candidate question shapes: Noul "does this matched-update write a frozen-role column", Choice over candidate composition repairs, Score on revalidation-cone completeness. Answer in solution space with a small offline pilot on phase-1 cases, reported as pilot not evidence.

### Frame-Stress Signals
- A reviewer shows the restricted-MERGE plus regression conventional repair catches everything the role contract catches, on this and held-out cases. The compositional claim then does not survive and phase 2 should stop per the phase-1 guardrail.
- The spec does not state first-encounter binding for incremental updates. The example then rests on a CE alone and the "named authority" framing must be dropped from the walkthrough.
- Building DimCustomer and DimAccount SCD2 honestly requires most of the CustomerMgmt XML transformation. The chain is then too wide for a bounded slice and should be cut to Account only or to a stubbed customer dimension with its own declared holes.
- Jev confidence is uniformly high on every question, including deliberately ambiguous cases. That signals the questions are leaking the answer through state construction.
- The role vocabulary needs a new role for every new case. That means roles are not a general abstraction and the mechanism is wrong.

### Ready for Solution Space?
Yes, with two items to resolve inside solution space before any preregistration: read the TPC-DI incremental DimTrade and FactHoldings clauses for authority specificity, and spike SQLMesh incremental-by-unique-key on DuckDB to settle where role enforcement physically lives. The scorer correction is a prerequisite carried from issue #8 and is not a phase-2 design question.

## Problem Weave (phase 2, 2026-09-16)

**Current frame:** Extend the phase-1 slice into a chained incremental pipeline governed per stage, with a controlled account-428 rollover CE that exposes surrogate-key rebinding on trade 372101, caught as a `frozen_from_first_encounter` role violation, propagated into FactHoldings, and compared against a conventional repair; plus Jev as a measured fourth arm.
**Layers used:** practitioner outcome (recognition is the aim), governance and authority (holes close only under named authority), system and technical (compiler and engine feasibility), evidence and measurement (preregistration, scorer fix, Jev comparability).
**Independence:** four parallel sub-agents, same contract, no cross-reading. Coordinator synthesis only.
**Status:** candidate frames; one premise correction and three material oppositions surfaced.
**Inputs:** phase-2 Aim and Problem Space above; verified Batch1/2 facts; compiler and contract shapes; one Jev call.

### Shared Core
All four lenses agree on these, independently:
- The failure is real and reproducible on the data: 372101's keys bound in Batch1, Batch2 completes it, 353232's holding closes through it. Only the account rollover is constructed and must be labeled everywhere.
- The rule must be stated as a semantic role attached to semantic types, never as column names or incident ids. Roles must be reused on at least two columns or two consumers or they are per-case and the mechanism is wrong.
- The conventional repair must be shown complete and honest, and a preregistered null arm must exist that ties or loses.
- Jev is evidence only, under the experiment-lead hat, off the reader's critical path, counted separately, with state provably free of scorer truth and CE archive.
- Phase 2 is a new preregistration; v2.4 is never rescored.

**Premise correction (technical lens, observed in venv):** SQLMesh 0.236.1 on DuckDB has no MERGE. `INCREMENTAL_BY_UNIQUE_KEY` materializes as delete-by-key plus insert of whole rows, and `when_matched` raises. There is no update-column list to constrain. Frozen-key preservation can only live in the generated SELECT (carry the prior row's frozen columns forward, or read a separate first-encounter carrier) plus a fail-closed audit. The aim's "MERGE whose matched-update list physically cannot contain frozen columns" is not buildable here; the buildable claim is "the compiler derives the carry-forward from roles and the audit fails closed on any escape".

### Distinct Problem Statements
1. **Practitioner:** A warehouse engineer needs to recognize the rebind as a defect they have shipped and see what a role catches that their regression would not, because otherwise the method reads as ceremony, but the repo shows a status-timestamp failure on a historical slice with an empty CE archive.
2. **Governance:** The domain-reviewer and data-product-owner hats need each of the three holes closed under traceable authority before any projection encodes the policy, but the spec is unread, the only other fill is a constructed CE, semantic types have no mutation role, and the Sketch is one document for one slice.
3. **Technical:** The compiler maintainer needs the projection to preserve frozen keys as a property of generated code, but the engine has no MERGE, `model()` hardcodes FULL, preflight pins the hole set, and SCD2 for accounts requires an XML extraction whose scope is undecided.
4. **Evidence:** The research-sponsor needs a phase-2 score that separates "roles caught it" from "any restricted update plus regression would have", but no preregistration exists, the v2 harness hard-codes the visible finding per case (so a Jev arm fed that table is trivially confident), and Jev determinism is unobserved.

### Interwoven S&T Steps
| ID | Parent | Depth | Layer | Strategy (what/why) | Tactic (how) | Disposition | N | PA | Owner | Review trigger | Evidence | Links |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| root | none | 0 | all | Reader recognizes the rebind defect and sees roles catch what a regression cannot, under traceable authority, with a preregistered comparison | — | — | — | — | data-product-owner | practitioner read | — | — |
| U1 | root | 1 | practitioner | Recognition: naive load passes every existing check on Dave's own defect | Show the naive incremental first in ordinary SQLMesh form, passing schema, null, count and phase-1 audits; then introduce contracts. Label the 428 injection wherever it appears. | candidate | Without recognition nothing else matters | Chain materializes on DuckDB with the CE | repo author | walkthrough draft | data observed; materialization assumed | dep T2, T3; overlap G3 |
| U2 | root | 1 | practitioner | Differentiation: defeat "same thing, less machinery" | Show the conventional repair completely (drop SK columns from the rewrite, regression on 372101). Then a second unrelated change where the regression is silent and the role fails closed. Order is load-bearing. | candidate | Aim's misunderstanding signal is exactly this | A second change exists without inventing policy | repo author + skeptical reviewer | before preregistration | frame-stress, undemonstrated | dep G2, T4; opp T2a; overlap E3 |
| U3 | root | 1 | practitioner | Consequence: "what else is wrong" | Cone names FactHoldings for 353232 and position metrics | deferred until U2 survives | Post-incident question Dave asks | Cone derivable from typed edges | repo author | after U2 | phase-1 recall 1.0 on other edge | dep T5 |
| G1 | root | 1 | governance | Every hole has one hat | Keep Sketch ownership: incremental-cdc and incremental-update-lifecycle to domain-reviewer; key holes to data-product-owner. Reviewer adjudicates meaning; owner authorizes Sketch edit via new repair-authority record. | candidate | Issue-4 split worked | Hats assignable before spec read | data-architect | hole reassigned mid-phase | Sketch hole table observed | dep G6 |
| G2 | root | 1 | governance | Authority exists before and after the spec read | Pre-spec: basis kind `approved_decision` to a new adjudication metis, with presumed clauses marked `unverified-locator`, never invented. Post-spec: swap to verified locators. | candidate | No clause locator exists today | Verifier accepts approved_decision already | domain-reviewer | spec obtained or declared unreadable | assumed | dep U2, T4; gap: FactHoldings has no hole and no owner |
| G3 | root | 1 | governance | A constructed CE cannot become incident-specific policy | CE enters archive with `provenance: constructed`, constructor hat, and a general rule stated via semantic role. Reviewer accepts the rule only if it names no ids. CE joins regressions; rule joins Sketch. | candidate | Constructed CE is policy-from-convenience wearing a badge | Archive and regression set are already separate | domain-reviewer | any rule mentioning 428 or 372101 | observed separation | overlap U1; opp T3 (where the injected row lives) |
| G4 | root | 1 | governance | Roles attach to types, not columns | Add `mutation_role ∈ {mutable, frozen_from_first_encounter}` to semantic-types v1; contracts inherit via target_semantic_type; check becomes a contract_check like existing type compatibility. | candidate | Only way to reuse across DimTrade and FactHoldings | history_role precedent exists | data-architect | a third role is needed | observed schema | overlap T1; invalidation: FactHoldings needs a third role |
| G5 | root | 1 | governance | Sketch structure supports per-stage authority | One Sketch per stage, own holes and CE path, plus a chain index naming which Sketch owns each edge hole. One chained Sketch rejected because repair-authority allowed and forbidden lists are per-sketch ids. | candidate | Forbidden-adjacent lists need distinct targets | none | data-product-owner | edge hole with no owning Sketch | observed record shape | dep G6 |
| G6 | root | 1 | governance | DimTrade incremental edge has a repair record | New `repair.dim-trade-incremental-edge.v1`: basis G2 decision plus G3 CE; allowed only the new incremental edge sketch; forbidden DimAccount SCD2 sketch, historical edge, all projections, position metrics. | candidate | Template exists | none | data-product-owner | repair touches DimAccount | observed template | dep G1, G2, G3 |
| T1 | root | 1 | technical | Contracts carry a role slot | Add role field to semantic types; contracts.py validates roles alongside nominal type equality | candidate | Nothing else can derive the carry-forward | history_role exists | compiler | schema change review | observed | overlap G4 |
| T2 | T1 | 2 | technical | Generated code preserves frozen keys without MERGE | Emit INCREMENTAL_BY_UNIQUE_KEY whose SELECT takes frozen columns from the prior target row (or a first-encounter carrier) and mutable columns from CDC | candidate | Engine rewrites whole rows | SQLMesh allows self-reference for this kind | compiler | first `sqlmesh plan` | logical_merge observed; self-reference assumed | dep U1; opp U2 wording |
| T2a | T2 | 3 | technical | Escapes fail closed | Audit joining target to first-encounter carrier on frozen columns | candidate | No engine-level enforcement exists | compiler already emits audits | compiler | audit passes on injected CE | observed audit path | overlap E3 |
| T2b | T2 | 3 | technical | Native MERGE emission | Only if a MERGE engine enters scope | deferred | Not phase 2 | engine swap | compiler | engine change | when_matched engine-gated | — |
| T3 | root | 1 | technical | Minimal SCD2 for DimAccount and DimCustomer | Field-minimal XML extraction: ActionTS, ActionType, C_ID, CA_ID, CA_B_ID, CA_TAX_ST, status. SCD_TYPE_2_BY_TIME on DuckDB. Injected 428 row lives under counterexamples/, never in raw. | candidate | Chain needs real SCD2 versions | Batch1 XML has 14,573 actions in six types; 428 is NEW 2007-12-29 under C_ID 238, CLOSEACCT 2012-11-15 | compiler | XML scope review | observed counts; SCD kind assumed | opp G3 resolved by location |
| T4 | T2 | 3 | technical | FactHoldings resolves keys through the current trade | Join fact.current_trade_id to dim_trade.trade_id at load; a rebound sk_account_id propagates silently | candidate | Cross-table story depends on it | Spec clause assumed | compiler | clause verification | HH row observed | dep G2; invalidation: clause resolves via held trade 353232 |
| T5 | T4 | 4 | technical | Cone selects semantic descendants across tables | Typed edges dim_trade.sk_account_id[frozen] to fact_holdings to position metrics in revalidation profile | candidate | Lineage alone names dependency, not attribution | none | compiler | profile schema | flat node map observed | dep U3 |
| T6 | T2a | 4 | technical | Jev as pure judge | Code builds state from compiler output and contract (target columns with roles, candidate update list, prior row, CDC row), never from DuckDB. Noul on frozen write. Leak control: role-absent variant state. | candidate | Optional arm | SDK not yet in venv | experiment-lead | determinism check | one call observed | overlap E2.1, E2.4 |
| E1 | root | 1 | evidence | Phase 2 preregistered as v3 | Antecedent commit hashing scorer, corpus, custodian, Jev adapter, nonce | candidate | Every prior invalidation was an evidence defect | none | research-sponsor | before any scored run | metis chain observed | — |
| E1.1 | E1 | 2 | evidence | Scorer list-order fixed without rescoring v2.4 | Freeze `v2-score/v2` comparing descendant sets; v2.4 keeps v1; report counterfactual only as a labeled non-decision note | candidate | It is the open issue #8 item | none | experiment-lead | scorer diff review | false negative documented | prerequisite for all |
| E1.2 | E1 | 2 | evidence | Corpus v3 | Five v2 classes plus `incremental_key_rebinding` and one FactHoldings path case; new held-outs under rotated nonce | candidate | New classes need cases | E1.1 | experiment-lead | corpus freeze | classes observed, cases assumed | dep G2, G3 |
| E2 | root | 1 | evidence | Jev is a comparable fourth arm | Matched start DB, projection, reveal order, one attempt, same authority. Treatment: Jev replaces the deterministic "first visible finding" with a Choice over candidate locations and a Noul on frozen write, given raw observations not the hard-coded finding. | candidate | v2 visible_evidence is hard-coded per case | none | experiment-lead | dry run with decoy state | one call observed | dep T6; changes meaning of treatment |
| E2.2 | E2 | 2 | evidence | Calls are evidence | Per call: request and response sha256, tokens, probability vector, confidence, wall ns. Verifier asserts deterministic arms equal zero. | candidate | Envelope currently has literal zero | none | experiment-lead | verifier extension | observed | — |
| E2.3 | E2 | 2 | evidence | Nondeterminism handled | k preregistered replicates, majority decision, all retained, agreement rate reported not thresholded | candidate | Determinism unknown | none | experiment-lead | pre-run | none | — |
| E2.4 | E2 | 2 | evidence | State provably clean | Custodian emits jev_state_sha256 and a no-overlap assertion against corpus and CE archive; a decoy uninformative case must yield low confidence | candidate | v1 leak precedent | none | custodian | custody test | custodian observed | overlap T6 |
| E3 | root | 1 | evidence | Null arm exists and is a reject rule | Fifth arm: hand-written carry-forward excluding SK columns plus one regression on 372101. Tie on catches, held-out regressions, localization means compositional adds nothing for this case. | candidate | Frame-stress must be testable | none | experiment-lead | threshold review | untested | overlap U2; dep T2 (no MERGE to restrict) |
| E4 | root | 1 | evidence | Recognition is observable | Blinded raters given repair diff only classify incident patch vs role violation and name the role; agreement reported, no threshold | deferred | Aim's secondary signal | E1 | research-sponsor | after E3 | none | dep U2 |

### Sufficiency Groups
| Group | Parent strategy | Child steps | Mode | Collective coverage claim | Gap/deferred branch |
|---|---|---|---|---|---|
| SG-READER | root | U1, U2, U3 | U1 and U2 required, U3 conditional on U2 | Recognition plus differentiation is the minimum for the aim; consequence strengthens it | Recognition unmeasurable inside the repo (E4 deferred); no portable artifact for Dave's own shop |
| SG-AUTHORITY | root | G1, G2, G3, G4, G5, G6 | all required | Every hole has a hat, a basis before and after the spec read, a CE acceptance rule, a role vocabulary, a Sketch structure, and a repair record | FactHoldings has no hole and no owner; verifier acceptance of unverified locators untested |
| SG-BUILD | root | T1, T2, T2a, T3, T4, T5 | all required; T2b deferred | Roles derive the carry-forward, audit fails closed, SCD2 exists minimally, cross-table propagation and cone exist | SQLMesh self-reference and SCD_TYPE_2_BY_TIME on DuckDB unverified; FactHoldings clause assumed |
| SG-PROOF | root | E1, E1.1, E1.2, E2, E2.2, E2.3, E2.4, E3 | all required; E4 deferred | Preregistered, order-insensitive, uncontaminated score with a null arm and a separately counted model arm | Work-unit definition for a Jev call unfixed; SDK token field names unobserved |
| SG-JEV | E2 and T6 | T6, E2, E2.2, E2.3, E2.4 | all required | Judge over clean code-built state, logged, replicated, custody-checked | Whether Choice over locations or Noul per role is the right question is untested |

### Overlap and Complement
- G4 and T1 are the same move (role slot on semantic types) seen from authority and from code. Merge with provenance; G4 owns the vocabulary, T1 owns validation.
- U2.1 and E3 are the same conventional repair, once as walkthrough and once as null arm. Keep separate: one is prose, one is a scored arm.
- T6, E2.1 and E2.4 jointly define the Jev call site: technical says what state contains, evidence says what it must not contain and how it is verified.
- G3 and T3 complement: the constructed CE lives under counterexamples/ (T3), which is what lets G3 keep it out of raw data and out of policy-from-structure.
- U1 depends on T2 and T3 materializing; U2 depends on G2 authority for the second change and on T4 for FactHoldings as that change.

### Opposition and Uncertainty
- **Tension:** U2 wants a compile-time refusal ("the compiler will not generate it") versus T2/T2a where enforcement is a role-derived carry-forward query plus a fail-closed audit, because DuckDB has no MERGE.
  - **Type:** evidence dispute resolved by observation, leaving a scope trade-off on wording.
  - **Decision needed:** restate the aim's mechanism as "roles derive the projection and audits fail closed", and decide whether a pre-plan contract_check (rejecting a candidate update surface that touches a frozen type) is added so the reader still sees a refusal before execution.
  - **Owner:** data-architect for the mechanism, repo author for the walkthrough wording.
- **Tension:** E3's null arm is "restricted MERGE plus regression" versus T2's finding that there is no MERGE to restrict, so the honest conventional repair is a hand-written carry-forward.
  - **Type:** scope difference. The comparison becomes "role-derived versus hand-written carry-forward", which is a fairer and still recognizable contrast.
  - **Decision needed:** rewrite E3 and U2.1 in carry-forward terms before preregistration.
  - **Owner:** experiment-lead.
- **Tension:** E2 needs Jev to see raw observations rather than the hard-coded finding, which changes what "treatment" means for all arms, versus the phase-1 design where treatment was evidence visibility only.
  - **Type:** true trade-off between comparability with phase 1 and a meaningful Jev arm.
  - **Decision needed:** whether v3 redefines treatment for all arms (deterministic arms also consume raw observations) or Jev is reported as a pilot outside the matched comparison.
  - **Owner:** research-sponsor.
- **Tension:** G2 proceeds on presumed clauses with `unverified-locator` versus U2's second unrelated change, whose recognizability depends on the FactHoldings rule being named authority rather than a CE.
  - **Type:** sequencing. Read the spec before writing the walkthrough's second change.
  - **Decision needed:** obtain the spec text; if it does not name current-trade key resolution, the second change must be a different frozen column (sk_security_id) rather than a new consumer.
  - **Owner:** domain-reviewer.
- **Uncertainty:** G3.1 says a constructed CE can exemplify a rule; the Sketch text says holes fill by "named rule or approved counterexample" and does not say whether constructed counts. Needs a one-line Sketch clarification under data-product-owner.

### Recommended Working Frame
A warehouse engineer must be able to recognize surrogate-key rebinding on an incremental trade update as a defect they have shipped, and see it caught as a `frozen_from_first_encounter` role on a semantic type that the compiler turns into a carry-forward projection and a fail-closed audit, under authority traceable to a hat and a recorded decision, with a preregistered null arm that could show the roles added nothing. Jev is a separately counted judge over clean state, not part of the reader's path.

This frame keeps the shared core, absorbs the no-MERGE correction, and makes the two live trade-offs visible: refusal versus fail-closed wording, and whether v3 redefines treatment for every arm.

### Alternate Frames Worth Keeping
- **Authority-first:** treat phase 2 primarily as closing three declared holes under named authority, with the chain as the vehicle. Narrows scope, drops FactHoldings if the spec is silent, and makes the spec read the gating step.
- **Jev-as-pilot:** keep the deterministic three-arm comparison on the new corpus and report Jev outside it. Avoids redefining treatment, at the cost of no matched claim about model-in-the-loop selection this phase.
- **Engine-swap:** move to an engine with MERGE so the original "update list cannot contain frozen columns" claim is literal. Rejected for phase 2: it breaks the DuckDB reproducibility constraint and the phase-1 byte-matched projection discipline.

### Evidence and Invalidation
- **Need to learn:** whether TPC-DI 1.1.0 names first-encounter key binding for incremental DimTrade and current-trade key resolution for FactHoldings. Whether SQLMesh allows self-reference in INCREMENTAL_BY_UNIQUE_KEY on DuckDB. Whether SCD_TYPE_2_BY_TIME runs on DuckDB. Whether Jev returns low confidence on a decoy state. SDK token field names.
- **Signal this synthesis is wrong:** the null carry-forward arm ties compositional on a held-out case; Jev is equally confident with and without role labels in state; a third mutation role is needed for FactHoldings; the audit passes on the injected CE.

### Ready for Next Phase?
Yes for `/solution-space`, with three gates inside it: the spec read (G2), the SQLMesh self-reference and SCD2 spike (T2, T3), and the sponsor decision on treatment redefinition versus Jev-as-pilot (E2). The scorer fix (E1.1) is a prerequisite carried from issue #8 and can start now.

### Next Route
Research-sponsor decides E2: redefine treatment for all arms in v3, or report Jev as a pilot. Everything else in solution space follows from that choice and the two spikes.

### Wiring Follow-up
**Offer:** record durable artifacts after solution space selects; the premise correction and the constructed-CE rule are worth recording as metis now.
**Plan gate:** not ready; run `/oh-plan` only after `/solution-space` marks S&T ids selected.

| ID | Type | Statement | S&T step | Parent | Disposition | Owner | Record route | Planning route |
|---|---|---|---|---|---|---|---|---|
| W1 | metis | SQLMesh on DuckDB has no MERGE; frozen-key preservation lives in the generated SELECT plus a fail-closed audit | T2 | root | candidate | compiler | metis now | defer |
| W2 | guardrail | A constructed CE may exemplify a rule only if the rule is stated via semantic role and names no incident ids | G3 | root | candidate | domain-reviewer | guardrail after selection | defer |
| W3 | capability | Semantic types carry a mutation role that contracts inherit and the compiler enforces | G4/T1 | root | candidate | data-architect | capability under governed-compositional-etl-repair | issue candidate |
| W4 | capability | Per-stage Sketches with a chain index and per-edge repair-authority records | G5/G6 | root | candidate | data-product-owner | capability | issue candidate |
| W5 | signal | Null carry-forward arm ties or loses to compositional on catches, held-out regressions, localization | E3 | root | candidate | experiment-lead | signal | issue candidate |
| W6 | signal | Jev confidence drops on decoy state and per-call logs reconcile to envelope | E2.4/E2.2 | E2 | candidate | custodian | signal | issue candidate |
| W7 | objective | Scorer v2 compares descendant sets; v2.4 untouched | E1.1 | E1 | candidate | experiment-lead | objective | issue now (carried from #8) |
| W8 | signal | Blinded practitioner raters name the role from the repair diff | E4 | root | deferred | research-sponsor | signal | defer |

## Solution Space (phase 2 mechanism, 2026-09-16)

### Solution Space Analysis

**Problem:** The compiler must turn `frozen_from_first_encounter` roles on semantic types into an incremental DimTrade projection that cannot rebind first-encounter surrogate keys, and must detect mechanically when any candidate projection would.
**Key Constraint:** Projections stay replaceable and byte-matched across arms inside one SQLMesh DAG on DuckDB; policy lives in roles, not SQL.
**Working Story:** The weave's premise correction was half right. The engine is not the gap: DuckDB 1.5.5 executes native `MERGE INTO`, and SQLGlot 30.8 parses and emits `exp.Merge` with the matched-update column list exposed as AST. The gap is SQLMesh 0.236.x, whose DuckDB adapter still uses `logical_merge` and raises on `when_matched`; latest release 0.236.2 and main are unchanged. So the literal aim claim, a MERGE whose matched-update list cannot contain frozen columns, is buildable if the compiler owns MERGE emission and the guard inspects the AST.
**Success Signal:** Given roles, the compiler emits a Merge AST whose `WHEN MATCHED THEN UPDATE SET` names only mutable-role columns; a guard rejects any Merge AST (compiler-built or hand-written by the native arm) that assigns a frozen-role column in a matched update; the injected 428 case leaves 372101's `sk_account_id` at its Batch1 value; a runtime audit still fails closed if anything escapes.
**Decision Criteria:** (1) literal enforcement on the update surface, (2) stays inside the SQLMesh DAG for lineage, audits, and matched arm bytes, (3) guard applies to every arm's SQL, not only compiler output, (4) minimal new machinery, (5) does not depend on upstream.
**Critical Assumptions:** SQLMesh `kind CUSTOM` materializations load and run on the DuckDB gateway in 0.236.1; the materialization can execute an arbitrary SQLGlot expression through the adapter's connection; `is_first_insert` lets it create and seed the table; semantic-type roles can be added without collapsing the existing nominal type checks.

### Candidates Considered
| Option | Level | Approach | Main Trade-off |
|---|---|---|---|
| A | Local optimum | Carry-forward SELECT inside SQLMesh `INCREMENTAL_BY_UNIQUE_KEY`; frozen columns COALESCE from the prior target row; fail-closed audit | Fits stock SQLMesh, but the claim weakens to "derived SELECT plus audit"; no update surface exists to guard, so the native arm's conventional repair cannot be a restricted MERGE and the practitioner comparison gets less recognizable |
| B | Reframe | Compiler builds `exp.Merge` from roles; `kind CUSTOM` materialization executes it natively on DuckDB; AST guard rejects frozen-role assignments in any matched update; audit retained as second gate | One small Python materialization in the projection; SQLMesh column lineage for CUSTOM kind must be declared; bypasses adapter merge path only for this model |
| C | Band-aid | Compiler emits MERGE and the experiment runner executes it on DuckDB outside SQLMesh | Simplest, but breaks the one-DAG, one-canonical-projection discipline that issue #5 established; lineage and audits for DimTrade leave SQLMesh |
| D | Redesign | Engine adapter subclass with native merge, registered as a custom gateway type | Cleanest semantics (stock `when_matched` works) but relies on an unofficial extension seam; effectively a fork for one adapter method |
| E | Status quo plus upstream | Keep FULL kind now; contribute `SUPPORTS_MERGE` for DuckDB ≥1.4 to SQLMesh | Correct long-term, not on this phase's timeline; nothing to demonstrate meanwhile |

Pruned early: C fails criterion 2; D fails criterion 4 and adds fork risk for no demonstrable gain over B; E does not deliver in phase 2 but is kept as a follow-up.

### Interpretive Variety Check
- Different frames. A assumes the engine cannot merge and pushes policy into query shape. B and D assume the adapter is the gap and restore the update surface. C assumes SQLMesh is optional for this model. E assumes the fix belongs upstream.
- Current-frame test: B most directly tests the aim's original claim that roles constrain the update surface. A tests the weave's corrected claim.
- Failure would teach: if B fails because CUSTOM materializations cannot run arbitrary SQL on DuckDB, the fallback is A and the aim wording stays as the weave corrected it. If the guard passes a rebind through some Merge shape the compiler did not anticipate (an INSERT-on-match trick, a subquery assigning through an alias), roles-on-AST are insufficient and enforcement must also be structural, which is what the retained audit covers.

### Risk Retirement Plan
| Risk / Assumption / Alternate Frame | Planned Disposition | Tempting Patch This Must Fail | Required Evidence or Rationale | Stop/Pivot If |
|---|---|---|---|---|
| `kind CUSTOM` runs on DuckDB gateway and can execute a SQLGlot Merge | Retired by evidence | Running the MERGE via a raw duckdb connection inside the materialization instead of the adapter | Spike: minimal CUSTOM model in a scratch SQLMesh project; `sqlmesh plan` applies, MERGE executed through `self.adapter`, second run updates without duplicating rows | Materialization cannot reach the adapter's connection or plan refuses CUSTOM on this gateway; pivot to A |
| Guard covers all Merge shapes that can write a frozen column | Retired by evidence | A guard that only checks column names in `SET` for the compiler's own output | Adversarial tests: hand-written MERGE from the native arm with frozen column in SET; frozen column assigned via alias or expression; `WHEN MATCHED THEN DELETE` followed by `NOT MATCHED INSERT` (delete-reinsert rebind); frozen column absent from SET but present in an UPDATE outside MERGE. Guard must reject the first three and the audit must catch the fourth | A shape passes both guard and audit while rebinding; then enforcement needs a structural first-encounter carrier table |
| Roles attach to semantic types without breaking nominal type checks | Retired by evidence | Putting `frozen` on logical-model column names | Contracts test: role inherited via `target_semantic_type`; a column renamed keeps its role; a contract declaring a role directly on a column is rejected | Two columns of one semantic type need different roles; then roles are per-binding not per-type and G4 is wrong |
| Native arm can still write a conventional restricted MERGE | Accepted with rationale | N/A | B restores the update surface, so the null arm (E3) and walkthrough (U2.1) return to "restricted MERGE plus regression"; this is the recognizable contrast the practitioner lens wanted | — |
| SQLMesh lineage for the CUSTOM model | Retired by evidence | Skipping `columns` and letting lineage go dark for DimTrade | Manifest test: `lineage_manifest` still maps roles and rules to `governed.dim_trade` columns; SQLMesh `columns (...)` declared from the logical model | Lineage cannot be declared; accept with a manifest-level lineage note |
| Upstream fixes this and makes B redundant | Accepted with rationale | N/A | B is a replaceable projection by design; if SQLMesh adds native DuckDB merge, the materialization is deleted and the same guard runs on the adapter's Merge. Record E as follow-up | — |
| The injected 428 rollover must live outside raw data | Triggered | Editing Batch2 Account.txt | Carried from weave G3/T3: CE row under `counterexamples/`, loaded by a labeled CE stage | Any raw file diff |

### Recommendation
**Selected:** Option B, role-derived MERGE through a custom SQLMesh materialization with an AST guard, plus Option A's fail-closed audit as the second gate.
**Level:** Reframe

**Rationale:** It restores the literal claim in the aim with the smallest new part, keeps every model in one DAG with matched bytes across arms, and gives the guard a real update surface to inspect on every arm's SQL. The audit stays because the guard proves the compiler's intent, not the engine's behavior. This is a projection choice, replaceable by design, so it is not a one-way door and `/dissent` is optional.

**Accepted trade-offs:**
- One Python file enters the projection; it is classified as `sqlmesh_model` projection, not policy.
- The DuckDB adapter's merge path is bypassed for one model; if upstream changes, the file is removed.
- Column lineage for the CUSTOM model must be declared explicitly.

### S&T Selection
| Step ID | Disposition | Parent | Sufficiency group | Why this disposition | Owner | Review trigger |
|---|---|---|---|---|---|---|
| T1 | selected | root | SG-BUILD | Role slot on semantic types is the input to MERGE emission and the guard | compiler | schema change review |
| G4 | selected | root | SG-AUTHORITY | Same move as T1 seen from authority; vocabulary `mutable`, `frozen_from_first_encounter` | data-architect | a third role is needed |
| T2 | selected (revised) | T1 | SG-BUILD | Revised tactic: compiler builds `exp.Merge` from roles; CUSTOM materialization executes natively; guard on AST | compiler | CUSTOM spike result |
| T2a | selected | T2 | SG-BUILD | Audit remains the fail-closed second gate | compiler | audit passes on injected CE |
| T2b | selected (revised) | T2 | SG-BUILD | Native MERGE emission is achieved via SQLGlot plus custom materialization, no engine swap | compiler | upstream adds native DuckDB merge |
| E3 | selected (reworded) | root | SG-PROOF | Null arm is again restricted MERGE plus regression | experiment-lead | threshold review |
| U2 | selected (reworded) | root | SG-READER | Compile-time refusal is real again: the guard rejects before plan | repo author | walkthrough draft |
| E1.1 | selected | E1 | SG-PROOF | Prerequisite carried from issue #8 | experiment-lead | scorer diff review |
| G1, G2, G3, G5, G6 | candidate | root | SG-AUTHORITY | Authority work, not decided by this mechanism choice; spec read still gates G2 | as recorded | as recorded |
| T3, T4, T5 | candidate | root / T2 | SG-BUILD | Chain build beyond DimTrade; unchanged by this decision | compiler | as recorded |
| U1, U3 | candidate | root | SG-READER | Depend on T3 and T5 | repo author | as recorded |
| T6, E2, E2.2, E2.3, E2.4 | deferred | E2 / T2a | SG-JEV | Await research-sponsor decision on treatment redefinition versus Jev-as-pilot | experiment-lead | sponsor decision |
| E4 | deferred | root | SG-PROOF | After E3 | research-sponsor | after E3 |
| Option E (upstream) | deferred | T2b | SG-BUILD | Follow-up contribution, not phase 2 | compiler | SQLMesh release notes |

**Selected-step sufficiency:** T1, G4, T2, T2a, T2b together make roles the single source for the update surface, prove it at compile time, and catch escapes at run time. E3 and U2 make the mechanism testable and recognizable. Gap: the selected set proves the mechanism on DimTrade alone; the chain into FactHoldings (T4, T5) and the authority closures (G2, G3, G6) remain candidate and are needed before the full walkthrough. Planning may proceed on the selected set as a first slice.

### Execution Handoff
- Preserve: roles on semantic types are the only place mutation policy lives; the compiler derives the matched-update list from them; no column name appears in policy.
- Verify via: guard rejects frozen-role assignments in any Merge AST regardless of author; compiler output passes the guard; injected CE leaves 372101's frozen keys unchanged; audit fails when the guard is bypassed by hand.
- Decision criteria: literal update-surface enforcement, one DAG, guard on all arms, minimal machinery, no upstream dependency.
- Critical assumptions: CUSTOM materialization executes through the adapter on DuckDB; `is_first_insert` supports create-and-seed; roles are per-type.
- Accepted trade-offs: one Python projection file; adapter merge bypassed for one model; explicit column lineage.
- Risk retirement checks: CUSTOM spike (must not fall back to a raw connection); adversarial Merge shapes including delete-reinsert (must fail a SET-only guard); role inheritance test (must reject roles on column names); lineage manifest test.
- Invalidated if: a Merge shape rebinds while passing both guard and audit; or roles must differ per binding for one semantic type.
- Stop/pivot triggers: CUSTOM kind cannot run on DuckDB in 0.236.1, pivot to Option A and keep the weave's corrected wording; any raw data edit for the CE.
- Needs human verification: data-architect confirms the role vocabulary; research-sponsor decides the Jev treatment question separately.

## Execute (phase 2 mechanism, 2026-09-16)

### Execution Complete

**Task:** Implement Option B the CESS way: mutation roles on semantic types govern the incremental DimTrade update surface; the compiler derives a SQLGlot MERGE from roles, guards it on the AST, and runs it through a SQLMesh `kind CUSTOM` materialization that the incremental Sketch names as a workaround for SQLMesh's missing native DuckDB merge; a deterministic gate fails closed on any escape.
**Aim achieved:** The literal aim claim holds again. The matched-update list cannot contain a frozen-role column, the guard names the attempted write and its role for any candidate SQL, the constructed account-428 counterexample runs end to end in DuckDB with keys preserved and lifecycle fields updated, and holdings are named as affected in the diagnosis.

### Declared Success Criteria
- Roles on semantic types are the only place mutation policy lives; no column list in contracts or SQL is policy.
- Compiler-built MERGE passes the guard and contains only mutable-role columns in `WHEN MATCHED THEN UPDATE SET`.
- Guard rejects frozen-role writes in any Merge shape and in UPDATE, DELETE-reinsert, and INSERT ON CONFLICT, whoever wrote the SQL.
- The counterexample leaves 372101's `sk_account_id` at 428001 while status becomes CMPT and prices update; audit passes.
- Phase-1 artifacts, index, regression set, and v2.4 evidence are byte-identical.

### Delivered Characteristics
- Role-derived MERGE via `governed_merge` CUSTOM materialization, executed natively on DuckDB 1.5.5 through the SQLMesh adapter: met.
- AST guard with diagnosis output (PASS/FAIL/AFFECTED) and CLI (`compile_incremental.py guard <sql>`): met.
- Fail-closed gate `frozen_keys_bound_once` against an insert-only key-binding model: met.
- Sketch `trade-dim-incremental-v1` naming the workaround with a retirement trigger; rules `assumed` under an approved decision; authority-locator hole open: met.
- Constructed CE labeled, accepted on a role-stated general rule, in a phase-2 archive index and regression set: met.
- Conventional restricted-MERGE repair shown passing the guard (E3, U2): met.
- Scorer set-comparison fix (E1.1): deferred, separate change.
- SCD2 build, FactHoldings, Jev arm: out of scope, unchanged.

### Changes
- `sketches/trade-dim-incremental-v1.md`: new governing Sketch, extends v1, rules 4 to 6 on roles, MERGE surface, verify twice; workaround section; six holes.
- `contracts/incremental/`: schema v2 for semantic types (`mutation_role`) and edge contracts (authority may be an adjudication, rule status may be `assumed`, history_policy defers to roles); types, logical model, stage, edge, repair authority. Placed under `contracts/incremental/` so phase-1 directory scans stay exact.
- `.oh/metis/issue-8-incremental-key-binding-adjudication.md`: domain-reviewer decision; presumed rule; no clause number recorded.
- `counterexamples/archive/ce-account-428-rollover-v1.json`, `index-incremental-v1.json`, `regressions/curated-incremental-v1.json`: constructed CE, phase-2 index and regression set.
- `scripts/merge_guard.py`: roles, surface derivation, Merge builder, guard, diagnosis.
- `scripts/compile_incremental.py`: preflight, SQLMesh project renderer with materialization template, CE runner, CLI.
- `tests/test_incremental_guard.py`: 16 tests.
- `docs/incremental-merge-guard.md`: reader-facing walkthrough.
- `projection/manifest-incremental-v1.json`: retained manifest with roles, guard verdict, workaround record.

### Verification
- 16 incremental tests pass, including three SQLMesh executions on DuckDB.
- Phase-1 suites pass unchanged (contracts, projection, revalidation, oracle, experiment). One pre-existing failure in `test_final_report` is caused by Aug 14 working-tree edits to `evidence/issue-7/*v2.4*` wall-clock fields, not by this work; the test passes against the committed evidence.
- Guard CLI: naive MERGE exits 3 with both frozen columns named; restricted MERGE exits 0.

### Risk Retirement
| Risk / Assumption / Stop Trigger | Status | Tempting Patch This Check Fails | Evidence / Route |
|---|---|---|---|
| CUSTOM materialization executes through the adapter on DuckDB | retired | raw duckdb connection inside the materialization | Spike and tests execute `self.adapter.execute(merge)`; plan and restate succeed |
| Guard covers all Merge shapes | retired | SET-only name check on compiler output | Tests reject SET, alias, expression, matched DELETE plus INSERT, plain UPDATE, DELETE-reinsert, ON CONFLICT DO UPDATE; restricted MERGE passes |
| Roles per type, not per column | retired | role key on a logical attribute | `column_roles` rejects a role on a column; preflight requires the frozen role on two or more columns |
| Escape past guard and SQLMesh still caught | retired | trusting the guard alone | Test writes the frozen key directly into the physical table; `frozen_keys_bound_once` fails |
| Hand-edited properties refused before writing | retired | restatement plan that ignores local edits | Plain plan detects the change; materialization raises before executing; row unchanged |
| Constructed CE must not enter raw data | retired | editing Batch2 Account.txt | Fixture lives in `counterexamples/archive/`; compiler excludes that path; CE runner alone reads it |
| Spec clause specificity | accepted | recording a presumed clause number | Rules `assumed` under the adjudication; hole open; compiler refuses if it closes without a spec read |
| Upstream SQLMesh adds native DuckDB merge | accepted | keeping the materialization forever | Retirement trigger in Sketch and manifest; latest 0.236.2 and main unchanged |
| Two columns of one semantic type needing different roles | triggered-if | splitting a type per column | None observed; would invalidate G4 |

### Needs Human Verification
- Data-architect: the role vocabulary (`none`, `identity`, `mutable`, `frozen_from_first_encounter`) and its placement on types.
- Domain-reviewer: the TPC-DI 1.1.0 incremental DimTrade clause, to convert `assumed` rules and close `incremental.authority-locator`.
- Owner of the Aug 14 evidence edits: whether `evidence/issue-7/*v2.4*` should be restored to HEAD.

### Notes
- SQLMesh restatement plans reuse prod snapshots and ignore local model edits. A changed model is itself the plan; do not combine the two in a test.
- SQLMesh caches parsed models by file mtime; an edit within one second of compilation needs `.cache` cleared.
- The key-binding model is insert-only through the same materialization with an empty mutable list; it doubles as the audit's reference and as the first-encounter carrier the weave asked for.

## Dissent (phase 2 chain claim, 2026-09-16)

**Decision under review:** that the five links (DimCustomer, DimAccount, DimTrade incremental, FactHoldings, position metrics) form a compositional CESS chain rather than five CESS instances sharing a database.
**Stakes:** the whole phase-2 aim is compositional governance. If this is five models with `depends_on` in their frontmatter, the repo demonstrates nothing phase 1 did not.
**Confidence before dissent:** MEDIUM.

### Steel-Man Position
Each link has its own Sketch, contracts, gate, and repair authority. They share one role vocabulary, so a frozen key means the same thing in every consumer. Edge contracts map producer outputs to consumer inputs by semantic type. A revalidation profile compiles typed edges from those mappings, so the affected set after a violation is computed across links. Repair authorities forbid adjacent links' Sketches and all metrics, so a repair cannot leak sideways. One constructed CE enters at link 2 as labeled data and is expected to be caught at links 3 and 4 by the guard and at link 5 by the invariant. That is a chain: one failure, one entry point, governed propagation, bounded repair.

### Contrary Evidence
1. Nothing checks a handoff. Phase 1 had `validate_edge_bindings`: the producer contract's output type had to equal the consumer input type, and evidence could not declare its own type. Phase 2's edge contracts list `reference.dim_account_as_of.sk_account_id` but no code verifies that `logical.dim_account` has an attribute of that name and semantic type. The mappings are prose in JSON.
2. Nothing constrains what a link's projection may read. A Developer for FactHoldings can join `governed.dim_account` directly and re-resolve keys. That is the tempting wrong repair for link 4, it passes the MERGE guard because the write surface is fine, and only the runtime gate would notice. The chain boundary is not mechanical.
3. The revalidation profile is computed but unused. No runner takes a violated node, selects the downstream gates, and runs only those. The AFFECTED list prints; nothing acts on it.
4. The CE's lineage across links is not recorded. The phase-2 archive index says the CE resolves two rules on the trade edge. The FactHoldings repair authority cites the CE, the position invariant depends on it, and neither is in the index. `A` is incomplete about which links one CE governs.
5. Sketch review has no judge at any link, and no composite acceptance exists. `accepted(chain)` is undefined. Five green gates is not a chain accepting a case.
6. Link 3 says it extends `trade-dim-v1` and closes none of its six holes formally. The phase-1 holes that motivated phase 2 are still open in phase 1's Sketch while phase 2 acts as if they were closed.

### Pre-Mortem Scenarios
1. **Functional:** a Sonnet Developer for link 4 joins DimAccount directly, all gates pass on the fixture because the fixture's current version happens to match, and the "second consumer catches it" demonstration is false. Warning sign ignored: no table-reference check.
2. **Adoption:** a practitioner reads five Sketches, sees five SQLMesh models with audits, and says "this is dbt with contracts." Warning sign ignored: the composite behaviors (cone selection, chain acceptance, cross-link CE lineage) are described but not runnable.
3. **Opportunity cost:** the time goes into five SCD2 and fact bodies while the one artifact that makes composition mechanical, the handoff check, never gets built. Phase 1 already had it for one edge.

### Hidden Assumptions
| Assumption | Evidence | Risk if Wrong | Test |
|---|---|---|---|
| Shared semantic types make handoffs governed | Types exist; edges name them | Producer and consumer drift silently; a rename breaks meaning without a failure | Harness check: every edge mapping `from` resolves to a producer attribute of identical semantic type |
| A link's projection reads only its declared producers | Edge contracts list producers | Re-resolution shortcut passes the guard | Harness check: model body table references must be a subset of the edge's producer entities |
| The CE propagates through the chain | Design intent | It is caught only where a fixture happens to make it visible | Run the cone from the violated node and require downstream gates to fail on the naive body |
| Five per-link acceptances imply chain acceptance | None | Path failures with locally valid links pass | Composite acceptance = all links pass G and review on active case plus R, plus path invariants |

### Reconstructed Story
- **Still true:** the role vocabulary, the guard, the per-link Sketches and authorities, and the CE entering as labeled data are the right parts. The revalidation profile is the right composite gate skeleton.
- **Weakest assumption:** that naming producers in an edge contract governs what the projection reads.
- **Changed situation model:** composition has to be mechanical in the harness, not asserted in JSON. Four checks are missing and each is small: handoff type binding, table-reference containment, cone-driven gate selection, and composite acceptance with a judge per link.
- **Changed beliefs:** confidence that the current artifacts are a chain drops to LOW. Confidence that they become one with those four checks is HIGH, because phase 1 already did the first for one edge.
- **Next action:** add the handoff and table-reference checks to the harness before any Developer is spawned, so the Developer boundary is enforced, not described.

### Decision
**Recommendation:** ADJUST.
**Reasoning:** the user is right about the present state. Five Sketches with `depends_on` and a shared type file are five instances. What makes it a chain is enforcement at the seams, and none of the seam checks exist yet.
**Modifications:**
1. Harness `anchors()` validates every edge mapping against the producer logical model or stage contract: same attribute, same semantic type, no type declared by the consumer. Fail otherwise.
2. Harness `check` extracts every table reference from a governed body and rejects any not in the edge's declared producers. FactHoldings may read `holding_history_stage` and `dim_trade_incremental` only.
3. Harness `cone` takes a violated node, computes affected models from the profile, and runs only their gates. The CE report uses it instead of running everything.
4. Harness `accept` produces the two-check matrix for the active case and `R` across all links, with a sketch-review judge per link given only that link's Sketch and its observed rows.
5. Archive index records, per CE, the links whose rules, authorities, and gates it governs.
6. Phase-1 `trade-dim-v1` gets a note under its holes: which are addressed by `trade-dim-incremental-v1` under an assumed decision, without editing the hole rows.
**Confidence after dissent:** MEDIUM, rising to HIGH once checks 1 and 2 reject a deliberately shortcutting body.
**Follow-up artifact:** this section; the harness checks are the executable record.

## Dissent (compile chain versus data pipeline, 2026-09-16)

**Decision under review:** whether the five-link data DAG with per-stage Sketches is compositional CESS at all, given the user's reference case: a JTBD to UI compiler where intent compiles to a semantic component spec, which compiles to device-specific layouts.
**Stakes:** the aim of the repo. If this is a data pipeline with contracts, there is nothing to demonstrate.
**Confidence before dissent:** LOW, after the user's challenge.

### Steel-Man Position
The five links share a role vocabulary, typed handoffs, read containment, a computed revalidation cone, and one CE that enters at one link and is caught at three. Phase 1's own vocabulary is stage, edge, path: a data DAG. The chain is consistent with the repo's history.

### Contrary Evidence
1. **In the reference case, P becomes S.** JTBD -> semantic Sketch -> component spec -> layout. Each level's projection is the next level's governing input. In my chain, no Sketch is compiled from another. The Sketches are siblings, authored by hand, each governing a SQL transform. That is five instances, not a composition.
2. **My semantic layer is hand-authored when it should be compiled.** Semantic types v2, the logical models, the edge contracts, and the `frozen_from_first_encounter` role are exactly what a level-1 intent ("attribute a position to the account version that owned the trade when it was placed") should compile into. I wrote the compiled output by hand and called it the Sketch. So the role is asserted policy, not derived meaning, and the CE can only ever test SQL.
3. **The SQLMesh workaround is a device capability, not semantics.** In the UI chain, "ESP32 has 128 pixels" lives in the target profile, not in the JTBD. I put "SQLMesh has no DuckDB MERGE" in the semantic Sketch. That is a level confusion the reference case exposes immediately. The engine profile belongs to the last compilation step, and there should be several targets to prove the semantic level is engine-independent.
4. **Locating the earliest wrong decision is a compile-chain question.** The repo's aim says locate the first incorrect semantic decision. In a data DAG that means "which stage." In a compile chain it means "which level's sketch lost the meaning": did intent state it, did the semantic compiler derive it, did the engine projection enforce it. The second question is the one nobody's dbt project answers.
5. **Practitioner recognition cuts against me.** Dave has seen dbt contracts, tests, and lineage. He has not seen a business question compiled into mutation roles and then into three engines' incremental strategies with one guard.

### Pre-Mortem Scenarios
1. **Functional:** Sonnet writes five bodies, the CE passes, and the result is indistinguishable from a dbt project with contract tests. Warning sign: every artifact maps one-to-one onto a dbt concept.
2. **Adoption:** the walkthrough teaches "add roles to your types," which is a lint rule, not a method. Nobody changes how they specify pipelines.
3. **Opportunity cost:** the compile-chain demo, intent to semantic model to multiple engine projections, never gets built, and it is the one that mirrors the working JTBD compiler.

### Hidden Assumptions
| Assumption | Evidence | Risk if Wrong | Test |
|---|---|---|---|
| "Chain" means data lineage | Phase-1 vocabulary | Composition is asserted, not real | Does any link consume another link's Sketch as its input? No. |
| Per-stage Sketches compose by sharing types | Shared type file | A vocabulary is not a compilation | Remove one Sketch; do the others change? No. |
| The frozen role is authored policy | I wrote it | The CE cannot test whether meaning was derived correctly | Delete the role and ask what upstream statement would regenerate it. Today: nothing. |
| The engine workaround is semantic | It sits in the Sketch | Semantic layer is not engine-independent | Project the same semantic model to a second engine; the workaround should vanish without touching S2. |

### Reconstructed Story
- **Still true:** the guard, the materialization, the seam checks, the loader, the fixture, and the CE are sound parts. They are level-3 gate machinery and a level-2 validity check, not the chain.
- **Weakest assumption:** that composition lives in the data DAG. It lives in successive compilation.
- **Changed situation model:** the demonstration is a compile chain with three levels. L1 intent Sketch (business hat): analytical jobs and their meaning. L1 to L2 Developer compiles the semantic model: entities, grain, identity, history semantics, mutation roles, attribution paths, invariants. L2, once reviewed, is the Sketch for L3. L2 to L3 Developers compile per engine target with a capability profile: SQLMesh on DuckDB (custom materialization), DuckDB native MERGE, and at least one more. One CE observed at L3 is classified to the earliest level whose sketch lost the meaning. The data DAG is content inside L2 and L3, not the chain.
- **Changed beliefs:** confidence that the current work is a chain: none. Confidence that its parts survive into the compile chain: HIGH. The four seam checks become G for the compiled semantic model. The guard and materialization become G and P for one engine target. The five hand-written Sketches become the expected output of the L1 to L2 compiler, useful as a regression against what a Developer derives.
- **Next action:** return to solution space with the compile-chain frame. Write S1 first, in business language, with holes. Then delegate L1 to L2 to a Developer under a change contract and compare its derived roles with the hand-written ones.

### Decision
**Recommendation:** RECONSIDER.
**Reasoning:** the user's reference case defines composition as projection-becomes-sketch. Nothing built so far does that. The pieces are reusable; the structure is wrong.
**Confidence after dissent:** HIGH that the frame must change.
**Follow-up artifact:** this section; solution space to be rewritten under the compile-chain frame.

## Solution Space (compile chain, 2026-09-16, supersedes the phase-2 mechanism section)

### Solution Space Analysis

**Problem:** Demonstrate compositional CESS as a chain of compilations, where each level's reviewed projection is the next level's Sketch, and a counterexample observed at any level is classified to the earliest level whose sketch lost the meaning, then regenerates only what derives from that change.
**Key Constraint:** Each compile step must be delegable to a low-competence Developer under an explicit change contract. A boundary that needs a strong model to cross is drawn wrong.
**Working Story:** Mirror the working JTBD to UI compiler. L1 is business intent about a brokerage's positions, ownership, and history, in business language with holes. L1 compiles to L2, a semantic model: entities, grain, identity, history semantics, mutation roles, attribution paths, invariants, each element recording the L1 clauses it derives from. L2, once reviewed, compiles to L3 per engine target with a capability profile, each artifact recording the L2 elements it derives from. The data DAG is content inside L2 and L3.
**Success Signal:** (1) A Developer compiles L2 from L1 and derives `frozen_from_first_encounter` on account and customer keys from the attribution clause, without seeing the hand-written reference. (2) Removing that clause from L1 makes a fresh L2 compile omit the role, proving it is derived not asserted. (3) The same L2 projects to two or more engines with one guard, and the SQLMesh workaround appears only in that target's profile. (4) The account-428 CE, observed at L3, is classified to its level with the affected set computed from derivation edges.
**Decision Criteria:** projection-becomes-sketch at every level; derivation recorded on every compiled element; level-scoped CE cones; Developer delegability; reuse of the guard, materialization, seam checks, loader, fixture.
**Critical Assumptions:** L1 can be written in business language precise enough to compile; the L2 shape (types v2, logical models, edge contracts) is an adequate semantic model format; a second engine target is cheap enough to build (DuckDB native MERGE without SQLMesh is nearly free).

### Level structure and CE scope
| Level | Sketch `S` | Anchors `K` | Projection `P` | Gate `G` | A CE here regenerates |
|---|---|---|---|---|---|
| L1 | intent Sketch, business hat | TPC-DI source anchors, natural identities | none; L1 is authored | review only | L2 elements deriving from the changed clause, and their L3 descendants |
| L2 | reviewed L1 projection: the semantic model | L1 clauses, contract schemas v2, role vocabulary | types, logical models, edges, invariants, each with `derived_from` L1 clause ids | schema validity, handoff binding, read containment, role reuse, sketch review against L1 | L3 artifacts deriving from the changed element, in every target |
| L3 | reviewed L2 | engine capability profile per target | SQL models, audits, materialization, each with `derived_from` L2 element ids | AST guard, audits, CE run, sketch review against L2 | that target's projection only |

### Candidates Considered
| Option | Level | Approach | Main Trade-off |
|---|---|---|---|
| A | Reframe | Three-level compile chain as above; L2 Developer delegated first; two L3 targets | Discards the five hand-written Sketches as Sketches; keeps them as a reference output in oracle context |
| B | Local optimum | Keep the five-link DAG, add derivation ids and call it a chain | Composition still asserted; fails the "remove one Sketch" test |
| C | Redesign | Four levels: split L2 into conceptual model and physical-logical model | More faithful to the UI chain's component-spec versus layout split, but nothing in this slice forces the fourth level yet |

### Interpretive Variety Check
- Different frames: B keeps data lineage as the chain; A and C make compilation the chain.
- Current-frame test: A tests projection-becomes-sketch directly with the L1-clause-removal counterfactual.
- Failure would teach: if a Developer cannot derive roles from L1, the L1 language or the L2 format is wrong, which is the boundary lesson the user asked for.

### Risk Retirement Plan
| Risk / Assumption / Alternate Frame | Planned Disposition | Tempting Patch This Must Fail | Required Evidence or Rationale | Stop/Pivot If |
|---|---|---|---|---|
| Roles are derived, not asserted | Retired by evidence | Handing the Developer the reference contracts | Counterfactual compile without the attribution clause omits the role | The role appears anyway; then the Developer is inferring from raw or schema and L1 language must tighten |
| L2 format is a sufficient semantic model | Retired by evidence | Adding fields ad hoc during the Developer run | Developer produces valid L2 that passes the seam checks and review, or returns one precise question | Developer needs more than one question; the format has a hole |
| Engine independence of L2 | Retired by evidence | Leaving the SQLMesh workaround in L2 | Two L3 targets from one L2; workaround appears only in the SQLMesh profile | Any L2 element mentions an engine |
| Level-scoped cones are computable | Retired by evidence | Hard-coding affected lists | `derived_from` on every element; cone command over the derivation graph | Any element lacks provenance |
| Low-competence delegability | Retired by evidence | Using Fable for the Developer | Sonnet Developers for L1 to L2 and each L3 target | A boundary needs Fable; redraw it |
| Constructed CE stays out of records | Triggered if violated | Editing raw fixture | Labeled CE stage, audited | Any raw diff |

### Recommendation
**Selected:** Option A, three-level compile chain.
**Level:** Reframe
**Rationale:** it is the only option where removing an upstream artifact changes downstream ones, which is the definition of composition the reference case uses. The reusable parts all keep their jobs, at the right level.
**Accepted trade-offs:** the five per-stage Sketches stop being Sketches; the SCD2 and holdings semantics move from authored policy to compiled output that must be reviewed; more Developer runs.

### S&T Selection (supersedes the earlier selection)
| Step ID | Disposition | Note |
|---|---|---|
| L1 | selected | Write the intent Sketch in business language with stable clause ids and holes |
| L2 | selected | Sonnet Developer compiles the semantic model under a change contract; harness seam checks are its gate; reviewer judges against L1 |
| L2-cf | selected | Counterfactual compile without the attribution clause |
| L3-sqlmesh | selected | Existing materialization and guard, profiled as a target |
| L3-native | selected | DuckDB native MERGE executed directly, same guard |
| CE-level | selected | CE records carry a level and target; cone over derivation edges |
| U2, E3 | selected (carried) | Conventional repair comparison, now at L3 |
| E1.1, E2, E4, T3 as originally scoped | deferred | Scorer fix, Jev arm, rater study, full XML extraction |

### Execution Handoff
- Preserve: projection-becomes-sketch; derivation recorded on every element; roles derived from L1; engine facts only in L3 profiles; Developers get S and K and a change contract, never the CE archive or the reference output.
- Verify via: the counterfactual compile; two targets from one L2; cone from an L1 clause selects the right L2 elements and L3 artifacts; the 428 CE classified to a level.
- Invalidated if: a Developer cannot compile L2 from L1 with at most one question, or roles survive removal of the clause.
- Needs human verification: the L1 Sketch itself is the business hat's document; the user reviews it before any Developer compiles from it.

### Solution outline addendum: cache, multiple L2s, and Jev (2026-09-16)

**Compile chain.** L1 is one intent Sketch in business language with individually addressable, hashed clauses. Several L2 semantic models compile from it, one per job, each from a subset of clauses: ownership-history (customer and account versions), trade-lifecycle (trades and their ownership), positions (holdings and metrics). Each L2 compiles to L3 projections, one per engine target with a capability profile. Every compiled element records `derived_from`.

**Cache.** Fingerprint of an L1 clause = hash of its normalized text. Fingerprint of an L2 element = hash of the fingerprints it derives from plus the L2 compiler contract version. Fingerprint of an L3 artifact = hash of its L2 inputs plus the target profile. A manifest caches fingerprints. On any change, recompute; unchanged fingerprints are cache hits and never re-project. The revalidation cone is the stale set.

**Jev.** Deterministic hashing is the floor. Above it, Jev (TypeSafe System One) makes the typed decisions over code-built state:
- Invalidation: for each cached element whose input hash changed, Noul "does this clause change alter the behavior this element must produce?" High-confidence no keeps the hit; high-confidence yes invalidates the element and its L3 descendants; low confidence routes to the reviewer. This is the composite selection.
- CE level classification: Choice over {L1 gap, L2 gap, L3 defect} given clauses, element, observed and corrected output; confidence-gated; reviewer confirms.
- L3 strategy selection: Choice over materialization strategies from an L2 element and an engine profile, where capability flags leave it open.
- Review triage: one Noul per clause, "does the observed output follow this clause," selecting cases and clauses for the capable reviewer. Not a replacement for sketch review.
Every call is logged with request and response hashes, probabilities, confidence, and tokens. Without a key the selector records not-run and the cache treats hash-changed as invalidated.

**Developer boundaries.** L1 to L2 per job and L2 to L3 per target and job are delegated to Sonnet under the CESS Developer change contract, given S and K only. The hand-written contracts from earlier today move to oracle context as a reference output for comparison, never as Developer input.

## Dissent (S&T nesting applied to the compile chain, 2026-09-16)

**Decision under review:** the compile-chain design as drafted: L1 clauses, an L2 semantic-model format whose elements carry `derived_from`, a gate over derivation and typing, a fingerprint cache with Jev invalidation, and Developer contracts. Tested against the nesting that `/strategy-clarity` and `/problem-weave` prescribe for strategy and execution.
**Stakes:** if the levels nest the way S&T steps nest, the chain reasons; if they only point upward, it is lineage metadata again.
**Confidence before dissent:** MEDIUM.

### Steel-Man Position
Projection-becomes-sketch is in place at each level boundary. Every L2 element records the L1 clauses it derives from; the gate rejects elements citing clauses the job does not list, frozen roles without a clause, roles on columns, untyped handoffs, and reads outside upstream jobs. Fingerprints over derivation give a cache and a cone. Developers get S and K and a change contract. That is the CESS contract applied three times, connected by derivation.

### Contrary Evidence
1. **`derived_from` is provenance, not justification.** An S&T step carries necessity (why indispensable to the parent), a parallel assumption (why credible under current conditions), and a sufficiency claim about its sibling set. My elements carry a parent pointer. A Developer can cite the attribution clause on anything and the gate cannot tell decoration from derivation; my keyword heuristic for frozen roles is the confession.
2. **Sufficiency is unchecked.** Sufficiency is a claim about a named set of siblings covering a parent, never row-local. Nothing asks whether the elements citing `L1.lifecycle-mutates-outcome` together cover it. A model that omits fees, commission, and tax passes the gate. That is the exact failure `/problem-weave` warns about: a flattened table with free-form links is not a tree.
3. **No dispositions.** S&T steps are candidate, selected, rejected, or deferred, with owner and review trigger, and only selected steps route to planning. My L2 has no disposition, so L3 would compile from unreviewed L2, and the cache would cache candidates. Holes are deferred steps and CE tempting-wrong-repairs are rejected steps; neither has a place in the tree.
4. **No interweave across sibling L2s.** `/problem-weave` compiles independent passes, then normalizes and interweaves with a relation map: overlap, complement, dependency, opposition, gap, contradiction. My three jobs compile independently and are connected only by `upstream_jobs` and a handoff type check, which is one relation (dependency). A clause realized in two jobs with different roles is a contradiction nobody detects. A clause no job covers is a gap nobody reports.
5. **The Developer brief is a prompt, not a strategy artifact.** `/strategy-clarity` says an agent brief carries aim, mechanism, feedback, guardrails, files, behavior contract, checks, stop conditions, and review criteria. Mine has files, behavior contract, checks, and stop conditions. It never states the mechanism (why compiling from clauses should produce a correct model) or the review criteria the judge will apply, so the Developer optimizes for the gate.
6. **Cache unit is wrong.** Fingerprinting individual elements means a clause change stales scattered elements. The natural unit is the sufficiency group under that clause. It is also the unit a reviewer re-judges and the unit Jev should be asked about, with necessity and parallel-assumption text as state, since "why was this credible?" is exactly what a clause change may have broken.

### Pre-Mortem Scenarios
1. **Functional:** Sonnet returns a schema-valid L2 that covers half of each clause; gate passes; L3 is built on a model with unnamed gaps; the CE run "passes" because the fixture never touches the missing half.
2. **Adoption:** a reader sees JSON with `derived_from` arrays and calls it lineage metadata, which it is. What a reader recognizes as reasoning is necessity, assumption, and sufficiency text next to the element.
3. **Opportunity cost:** the interweave step, the only place composition across L2s is judged, never gets built because each job "passes" alone.

### Hidden Assumptions
| Assumption | Evidence | Risk if Wrong | Test |
|---|---|---|---|
| A parent pointer is enough to judge derivation | Gate passes on it | Decorative citations pass | Require necessity text; reviewer rejects an element whose necessity does not follow from the clause |
| A job passing alone means the job is right | Gate is per job | Gaps and contradictions across jobs | Weave step: every L1 clause covered by a group in some job; same semantic kind carries one role across jobs |
| L3 can compile from any gate-passing L2 | Nothing blocks it | Projection of unreviewed policy | Dispositions; L3 compiles only from selected steps |
| Element-level fingerprints are the right cache unit | Convenient | Partial invalidation of a group | Group-level fingerprints with element detail inside |

### Reconstructed Story
- **Still true:** three levels, projection-becomes-sketch, clause-level hashing, role vocabulary, the gate's structural checks, Jev above the hash floor, Developer delegation.
- **Weakest assumption:** that provenance is justification.
- **Changed situation model:** every L2 element is an S&T step. Its strategy is the L1 clause set it serves. Its tactic is the element. It carries necessity, a parallel assumption, feedback (the invariant or gate that checks it), owner hat, review trigger, and a disposition. Each job declares sufficiency groups per clause with mode, coverage claim, and named gap. Holes are deferred steps; tempting wrong repairs from CEs are rejected steps kept visible. After all jobs compile, a weave step produces the relation map across jobs and is itself reviewed. The cache and Jev operate on sufficiency groups. L3 compiles only from selected steps.
- **Changed beliefs:** confidence that the drafted format demonstrates reasoning rather than lineage: LOW. Confidence in the adjusted format: HIGH, because it is the nesting the two skills already use for strategy and the user's compiler uses for UI.
- **Next action:** revise the L2 schema, format, gate, and Developer brief before spawning a Developer; add the weave command; make the cache group-level.

### Decision
**Recommendation:** ADJUST.
**Reasoning:** the chain's levels already nest; the steps inside a level do not. Without necessity, sufficiency, dispositions, and an interweave, the L2 is a typed dependency graph, and the user's "old hat" verdict returns one level down.
**Modifications:**
1. L2 schema v2: each type, entity, attribute, handoff, and invariant carries `necessity`, `parallel_assumption`, `feedback`, `disposition`, `owner_hat`, `review_trigger`, `sufficiency_group`. Job-level `sufficiency_groups`: id, parent clauses, members, mode, coverage claim, gap. Holes are deferred steps citing an L1 hole. Rejected steps allowed with `rejected_because`.
2. Gate: every clause the job lists has at least one group; every element is in exactly one group; frozen roles need non-empty necessity; rejected and deferred steps excluded from anything downstream.
3. `weave`: normalize across jobs; report overlap, dependency, gap, contradiction; write `chain/weave.json` for review.
4. Cache and Jev at group level, with necessity and parallel assumption in the Jev state.
5. Developer brief in agent-brief form: aim, mechanism, feedback, guardrails, files, behavior contract, checks, stop conditions, review criteria. Developers must write necessity and parallel assumption for every element.
6. L1 jobs gain a feedback line naming the validation obligations the reviewer applies to that job.
**Confidence after dissent:** HIGH that the adjusted format is the right unit; MEDIUM that a Sonnet Developer fills necessity and parallel assumption well on the first pass, which is itself the delegability test.

## Execute (compile chain, cycle 1, 2026-09-16)

### CESS cycle report: L1 -> L2, job ownership-history

- **Active case and classification:** initial compilation of `ownership-history` by a Sonnet Developer under `chain/anchors/DEVELOPER-CONTRACT-L1-L2.md`. Gate passed; sketch review (Opus, given S and K and the model only) failed it. Classification: projection defects (undated CDC handoffs, roles by elimination, decorative citations, gaps not naming holes, two possibly missing holes) plus one missing sketch rule at L1 (what a statement carries) plus one anchor gap (no `per_statement` role).
- **Sketch clause before and after:** L1 unchanged pending authority. Proposed `L1.statement-content` filed as `chain/ce/proposed/ce.l1.statement-content.md`.
- **Projection surfaces rebuilt or repaired:** none yet; the Developer's model stands as cycle-1 evidence. Anchor K repaired: `per_statement` added to `semantic-model-v2.schema.json`, `L2-FORMAT.md`, and `merge_guard.ROLES` (treated as never-updated-in-place by the write-surface guard).
- **Deterministic regression added:** six gate rules in `chain_l2.py check`: versioned attributes may not be `mutable`; versioned entities must carry statement content; a handoff from a source with no effective-time handoff must be deferred; group gaps name `none` or an L1 hole; element derivations are a subset of their group's parents; holes list every group with deferred members. Re-running the gate on the cycle-1 model yields 20 rejections where it previously passed.
- **Deterministic results:** gate fail (20 problems) after mechanization; pass before.
- **Sketch review results:** fail; full text retained in `chain/l2/ownership-history/review-1.md`; verdict recorded in `review.json`.
- **Tempting wrong repair and evidence it still fails:** picking customer and account "standing" facts from anchored field names. The gate cannot detect this; the reviewer can, and the CE names it. The Developer contract forbids it.
- **Approval authority and decision:** business authority (the user, data-product-owner hat) for `L1.statement-content`; pending. Data-architect hat (coordinator) for the `per_statement` anchor change; approved as K, settles no business question.
- **CE evidence entailing each new rule:** the content-free `logical.customer` and `logical.account` entail the L1 clause proposal; the four `mutable` versioned attributes entail the anchor role.
- **Adjacent choices left open:** owner-change re-versioning; change effective time; closed-account activity; batch identity.
- **Next active failure:** recompile `ownership-history` after the L1 amendment, under a change contract naming the approved clause and the anchor change. Then review again. Only then compile `trade-lifecycle`.

### Jev
Invalidation selector live: substantive clause reversal 0.93 (invalidate), wording change adding the customer 0.39 (review). Calls logged in `evidence/jev/calls.jsonl`.

### Weave
`chain/weave.json`: four L1 clauses uncovered (they belong to jobs not yet compiled), four holes uncarried, five named gaps. No contradictions yet because only one L2 exists.

### Cycles 2 and 3 (2026-09-17)

- **Cycle 2.** Authority: assumed clause `L1.statement-content` (business declined the dialog; decision recorded in `.oh/metis/issue-8-statement-content-assumed.md` under the review-trigger protocol) and anchor role `per_statement`. Developer (Sonnet) revised; gate ok. Reviewer (Opus) failed: constructed account statements content-free (no status or tax handoffs from the labeled source), five dangling references to an empty questions list, non-nullable status with only deferred sources, overclaiming coverage, two holes neither recorded nor dismissed. All classified projection defects. Developer learning: it resolved an ambiguity by omission because the gate treated a filed question as a hard stop. Gate defect; fixed so questions never block validation.
- **Anchor learning.** The meaning of received action codes (INACT is a customer becoming inactive, CLOSEACCT an account closing) is a source definition with TPC-DI authority, not policy. Added `action_type_meanings` and `status_codes` to `chain/anchors/sources-v1.json`; L2-FORMAT states that interpreting an anchored code is allowed and deciding what standing consists of is not.
- **Format learning.** Some statement values are derived, not handed off: the current flag, and an owner carried forward when a constructed change omits it. Added attribute-level `derivation` to the schema, format, and gate.
- **Cycle 3.** Developer revised; gate ok on first run. Reviewer failed on one defect: the account identity handoff enumerated {ADDACCT, UPDACCT, CLOSEACCT, INACT}, omitting NEW and including INACT, contradicting its sibling; a next-level Developer would create account statements on customer inactivation, silently filling L1.hole.owner-change-reversions-account. Everything else held. Reviewer proposed a K rule; mechanized: action-code enumerations across handoffs into one entity must agree and match anchored subjects. The gate now rejects the cycle-3 model with three problems.
- **Cycle 4.** In progress: same Developer, change-contract-4, text corrections only.
- **Gate mechanizations to date (all from review findings, none invented ahead):** versioned attributes are per_statement; versioned entities carry content; a source with no effective time cannot produce a statement; gaps name none or a hole; derivations are a subset of group parents; holes list blocked groups; dangling question references; non-nullable attributes need a source or a derivation; a projectable source supplies every required attribute; action-code enumerations agree and match subjects. Each turned a reading into a check, which is CESS step 7 done at the anchor level.
- **Pattern.** The reviewer keeps finding the next thing one level finer than the gate. That is the intended division: the gate proves structure and provenance, the reviewer judges meaning, and each review makes the gate one rule stronger. Three cycles on one job is the cost of a Sonnet Developer boundary; the boundary held, since every failure was fixable from the contract without a stronger model.

### Cycle 4 and the first cache test (2026-09-17)

- **Cycle 4.** Developer fixed the enumerations; gate `question` with zero problems. It filed one question: the owner of an account whose first statement is a constructed change. No clause settled it; asking was correct. Answered under the assumed-decision protocol as an authorized clarification of `L1.constructed-scenarios`: a constructed scenario never introduces a customer, account, or trade the brokerage does not have. Evidence discipline, not business policy; recorded as an addendum to `.oh/metis/issue-8-statement-content-assumed.md`.
- **Developer workaround worth noting.** The gate's enumeration check scans bare code tokens anywhere in a handoff's text, so the Developer described the customer-only codes periphrastically in a note to avoid being counted. The check should scan necessity only. Minor; recorded, not yet changed.
- **Cache test.** Fingerprint baseline committed to `chain/manifest.json`, then the clause amended. Plan result: `sg.identity`, `sg.history-asof`, `sg.current-version`, `sg.owner-standing` are hits by hash and will not re-project. `sg.statement-content` and `sg.constructed-scenarios` cite the changed clause; Jev returned 0.34 (medium) and 0.43 (low) on "does this alter the behavior the group must produce" and both routed to review. That is the intended shape: hash is the floor, Jev decides above it only when confident, and the reviewer takes the rest. Calls logged with hashes and tokens.
- **A provenance gap the cache exposed.** The carried-forward owner derivation depends on the constructed-scenarios clause but its attribute did not cite it, so `sg.owner-standing` was a hash hit although its rule text must change. Cycle 5 adds the citation. The reviewer should have caught it; the cache did first.

### Cycle 5: ownership-history selected (2026-09-17)

Developer applied the clarified clause; gate ok; Opus reviewer: pass, no exclusions, all review-3 findings addressed, nothing regressed. `review.json` records the selected element set; `chain/manifest.json` re-baselined. Cache adjudication recorded in `chain/cache-adjudications.jsonl`: of the two Jev-routed groups, one was unchanged and could have been kept, one had to change. Jev's low confidence on both was correct caution: the same clause edit changed one group's required behavior and not the other's, which is exactly the case a hash cannot see and a confident guess would get half wrong.

Five cycles on one job with a Sonnet Developer and an Opus reviewer. Every failure was repairable from the change contract without a stronger Developer. Two failures exposed gaps above the Developer: one in L1 (statement content), one in K (per_statement, derivation, action-code meanings and subjects). Ten gate rules came out of reviews. The job is now the reviewed Sketch for trade-lifecycle.

### L3 simulation finds an L2 gap; trade-lifecycle stops at a hole (2026-09-17)

- **L3 ownership-history on duckdb-native (Sonnet).** Gate ok; 9 of 11 audits clean. Two audits failed on the fixture: customer 238's INACT statement has no tier, account 428's CLOSEACCT statement has no tax treatment. The Developer verified against the source that those action rows carry no such fields, refused to invent a carry-forward, and filed two questions. Five L2 reviews had passed the model; the simulation supplied the field-presence facts the reviewer never had. Classification: L2 projection defect under existing clauses (the reviewer had accepted the same entailment for the owner). Adjudication recorded in `chain/l2/ownership-history/adjudication-l3-sim-1.md`; anchors gained `fields_present` per action code; gate gained the omitted-fact rule (with one false positive on the row envelope, fixed); cycle 6 sent to the L2 Developer.
- **Jev on the level question.** l1_gap 0.46, l2_gap 0.06, l3_defect 0.48, confidence 0.23. Routed to the adjudicator as designed. Its split says the entailment is not obvious from the clauses, so an L1 clarification is proposed (`chain/ce/proposed/ce.l1.omitted-facts-stand.md`) while the L2 repair proceeds. Recorded as evidence beside the adjudication, not as authority.
- **Trade-lifecycle L2 cycle 1 (Sonnet).** Gate question, zero structural problems. It derived the entity as incremental_by_identity, six mutable outcome attributes, a frozen owning account number, and stopped at the placement moment, which is `L1.hole.trade-timestamps`; it filed the question rather than assume the first-encountered row. Answered under the assumed-decision protocol as `L1.placement-moment`: the earliest held report's own time; late first encounters marked. Completion timing stays a hole. Cycle 2 sent.
- **Cross-level cone.** When cycle 6 re-selects ownership-history, only `sg.statement-content` changes; the L3 artifacts deriving from it (customer.sql, account.sql on duckdb-native) re-project; the other groups and their audits are hits. The trade-lifecycle L2 consumes the re-selected account statement shape, which is unchanged in identity and effective time.

### Cycle 6 scoped review; L1.omitted-facts-stand promoted (2026-09-17)

- **Scoped review.** With only `sg.statement-content` changed (confirmed by element-level diff against the last commit: four elements and one group), the reviewer judged that group only. Verdict fail on text: the coverage claim and the content invariants' parallel assumptions still explained coverage by direct handoff and named INACT and CLOSEACCT as producing actions for fields they omit; the invariant statements kept a hedge L3 had enforced unconditionally; the carry-forward rules lacked the owner rule's guarantee of a predecessor. The derivations themselves were accepted.
- **Governance finding, accepted.** The policy sentence "absent fields are not changes; the fact stands as last stated" had migrated into an anchor note and the format, both of which declare they authorize no rule. The reviewer preferred an explicit clause over the identity-plus-history entailment, and read Jev's 0.46/0.48 split as the same signal. Promoted `ce.l1.omitted-facts-stand` to accepted (assumed) and added `L1.omitted-facts-stand` to the Sketch, listed for ownership-history; scrubbed the anchors to shape only. Recorded in the metis addendum.
- **Cache.** The plan marks `sg.statement-content` stale and the other five groups hits. The new clause is uncovered until cycle 7 groups it. The L3 artifacts deriving from the stale group (customer.sql, account.sql on duckdb-native) will re-project after re-selection; the nine passing audits derive from unchanged groups and stay.
- **Assumed decisions now pending business confirmation:** statement content; constructed scenarios never introduce new things; placement moment; omitted facts stand. Each is one clause with its own fingerprint, so confirmation or amendment of any one re-projects only what cites it.

### Trade-lifecycle first review; cycles 7 and 8 of ownership-history (2026-09-17)

- **Trade-lifecycle review 2: fail, six findings.** The first was gate-induced: the cross-job type check demanded an identical mutation role between the upstream statement types and the trade's ownership reference, so the Developer typed a frozen reference `per_statement`, which would have taught L3 to version trade rows. Gate relaxed to meaning and physical type; role belongs to the consuming entity's lifecycle. The other five were coverage honesty: a group claiming no gap while its own hole blocked it; the first-seen-late marker dropped as a note although the clause and contract both called for it; a hole dismissed while two selectors relied on an unanchored ordering of reports; a deletion-marked row silently treated as an ordinary later report; a false premise ("references, not copies") in the constructed-scenarios group. Anchors gained `trade_code_meanings` (status codes and order, cdc_flag meanings) and `report_order` (file production order) as shape. Cycle 3 sent.
- **Ownership-history cycle 7: fail on two text elements.** Contract-7 had limited the owner attribute to a citation, so its rule still entailed the carry from identity and history; the reviewer also caught the same policy sentence in the format's derived-attributes section. Anchor recast; contract-8 corrected the scope; cycle 8 applied it; scoped review 8 in flight.
- **Lesson about contracts.** Two of the last three failures were caused by my contracts, not the Developers: one over-strict gate rule, one over-narrow authorization. The Developer boundary held both times; the Developers did exactly what they were told. The coordinator's artifacts are inside the loop too.

### L3 cycle 2: ownership-history on duckdb-native runs clean (2026-09-17)

- Two stale artifacts re-projected (customer.sql, account.sql); nine audits kept unchanged; two audit header comments refreshed; manifest re-pointed at the cycle-8 review sha. Check ok; run ok; 11 of 11 audits at zero violations. Confirmed independently.
- Samples: customer 238 keeps tier 3 through its 2008 inactivation. Account 428 has three statements: opened 2007 (active, tax 1, owner 238), closed 2012 (inactive, tax 1 carried), and the labeled constructed change of 2017-07-08 00:58 (active, tax 2, provenance controlled_counterexample, owner carried). Customer 238's inactivation created no account statements, which is the correct non-filling of L1.hole.owner-change-reversions-account.
- Gate defect of mine: the L3 layout rule rejected the change contract as an unlisted file and the Developer deleted it to pass. Restored; governance files are now exempt and the L2 to L3 contract says they are not the Developer's to touch.
- The L3 projection now goes to a projection reviewer whose Sketch is the L2 model, not L1. That is the level boundary working: the reviewer cannot recover intent, only check that the SQL does what the model says and decides nothing the model left open.

### First L3 acceptance; a gate rule finds old bookkeeping (2026-09-17)

- **ownership-history on duckdb-native: pass, unconditional.** The projection reviewer, given only the L2 model as its Sketch, verified every selector, the write surface, containment, and all eleven audits, and checked the carry-forwards against the fixture inputs. No policy decided in SQL. Recorded in `chain/l3/duckdb-native/ownership-history/review-1.md` and `review.json`.
- **Trade-lifecycle cycle 3: fail on hole and gap bookkeeping** (a hole said it blocked a group whose gap said none, and the mirror). Mechanized as a two-directional gate rule. The rule immediately found the same class in the selected ownership-history model, five instances the cycle-5 reviewer had called "clearer with a second hole id". Cycle 9 for ownership-history is text only; its group fingerprints hash parents and members, not gap text, so nothing re-projects. Cycle 4 for trade-lifecycle sent.
- **Filed, not decided:** the reviewer's proposed clause distinguishing a late first encounter from a market order that legitimately begins at submitted (`chain/ce/proposed/ce.l1.first-seen-late-market-orders.md`). Until the business answers, first_seen_late stays a review flag with its premise stated.

### Text-only change re-projects nothing; L3 provenance by fingerprint (2026-09-17)

- Ownership-history cycle 9 changed four gap strings and nothing else (element-level diff: zero elements, zero holes). Coordinator reviewed it as bookkeeping and selected it. Cache plan: six hits. The native L3 projection's manifest pinned the cycle-8 review sha, which changed; the L3 check now accepts when every group an artifact derives from has an unchanged fingerprint, and reports that the sha was superseded by a behavior-neutral change. Stamping added (`chain_l3.py stamp`) after a passed projection review. This is the cache reaching across levels: a change that touches no fingerprinted input re-projects nothing at L3, mechanically.
- Trade-lifecycle cycle 4 applied review-3's corrections; gate ok; scoped review 4 in flight.

### Engine independence: two targets, one L2, identical tables (2026-09-17)

- `ownership-history` projected on `duckdb-sqlmesh` by a second Sonnet Developer from the model alone (the native projection was off limits). Check ok; SQLMesh plan and audit clean, 11 of 11. `chain_l3.py compare` shows `governed.customer` and `governed.account` identical row for row across the two engines. The SQLMesh profile's custom-materialization workaround was correctly not used: no entity in this job is incremental_by_identity. The workaround will appear only when trade-lifecycle projects to that target, and only in that profile.
- Developer mechanics recorded in the L2 to L3 contract: dotted audit names must be quoted in SQLMesh; a model whose audit joins another model declares depends_on.
- The Developer also noticed the working tree change under it (the bookkeeping re-selection) and updated its manifest sha after diffing the selection set. With fingerprint provenance stamped it would not have needed to.

### Trade-lifecycle selected; three Developers dispatched (2026-09-17)

- Trade-lifecycle L2 passed at cycle 4 with no exclusions (42 elements, all five groups fully selected). First_seen_late is selected as a review flag with its premise stated; the market-order question stays a filed proposal. Two reviewer notes deferred to a future authorized change and recorded beside the contracts. Weave: two overlaps (downstream frozen copies), two dependencies, and the two positions clauses still uncovered.
- Dispatched in parallel: trade-lifecycle L3 on duckdb-native (native MERGE, matched update limited to mutable columns by the guard), trade-lifecycle L3 on duckdb-sqlmesh (the custom materialization workaround, used for the first time and only in that profile), and the positions L2 compile consuming both selected upstreams. The ownership-history SQLMesh projection review is still in flight.
- The next composite check once trade-lifecycle projects on both engines: `chain_l3.py compare` must show identical `governed.trade` tables, and trade 372101 must pin account 428's 2012 statement rather than the 2017 constructed one on both.

### Both ownership-history projections accepted (2026-09-17)

- duckdb-sqlmesh review 1 failed on one audit whose predicate could not fail: it checked that a present label was not blank, not the invariant's two clauses. The reviewer demonstrated it by inverting provenance on a copy. The Developer applied the prescribed predicate; I verified the inversion control (five violations) and the clean run (zero), and accepted as coordinator since the reviewer had specified the repair in full. Both targets stamped and reviewed; cross-target compare identical.
- Gate learning: audits were not containment-checked; now they are, and a test covers it. The gate still cannot judge whether an audit's predicate matches its invariant. That remains the reviewer's job, and the inversion control is the technique worth keeping: perturb the table in the direction the invariant forbids and require the audit to fire.

### The counterexample runs end to end on SQLMesh (2026-09-17)

- Trade-lifecycle on duckdb-sqlmesh uses `kind CUSTOM governed_merge` with mutable and frozen column lists taken from the model's roles. This is the first and only place the workaround appears, in that target's profile.
- Two-phase simulation added to the runner: project Batch1, reload sources with Batch2 and the labeled constructed account change without dropping governed tables, re-project. Result on trade 372101: status PNDG to CMPT, executed price, fees, commission, tax filled; owning_account_effective_from stays 2012-11-15 18:05:28 and owning customer stays 238, while account 428's current statement is the 2017-07-08 constructed one. Changed columns are exactly mutable ones. This is the rebind the phase-2 aim described, not happening, on real Batch2 rows plus one labeled constructed row.
- Trade 353232 is marked first seen late because its only held report is the historical CMPT row; the historical TradeHistory file is not anchored in this chain. Sent to the projection reviewer as a question about the anchors.
- Gate heuristic added: a trade artifact that references is_current on an entity the model resolves as of an event time is rejected. That is the tempting wrong resolution, mechanized.

### Trade-lifecycle on both engines; the counterexample survives on both (2026-09-17)

- duckdb-native: native MERGE with the matched update limited to the six mutable attributes; check ok; five audits clean; two-phase simulation: PNDG to CMPT, prices filled, ownership reference pinned to 2012 while the constructed 2017 statement is current. Cross-target compare: `governed.trade` identical on duckdb-native and duckdb-sqlmesh. Chain tests green, including both two-phase simulations.
- Same L2, two engines, one guard, one materialization workaround confined to the profile that needs it. That is the solution space's third success signal.
- The native Developer self-reported reading gate source against its brief and drew no policy from it. Recorded; the reads restriction stays in the brief.
- Both trade projections are with projection reviewers. Positions L2 and the counterfactual compile of ownership-history without the statement-content clauses are still running.

### Audit mutation testing mechanized (2026-09-17)

- `chain_l3.py mutate` corrupts one protected value at a time on a scratch copy (null it; swap it for another row's value) and requires an audit to fire. Ownership-history: 18 mutations, 3 unprotected (status swaps, tax-treatment swap): no invariant states that an interpreted value equals its anchored interpretation. Trade-lifecycle: 7 mutations, 3 unprotected (nulls on owning account, placement time, late marker): recomputation audits compare with equality, so a null passes. Both recorded as findings beside the projections and routed to the next authorized changes. The reviewer did this by hand for one projection; now every native projection gets it.

### Anchor gap from an L3 review; counterfactual and positions compiles land (2026-09-17)

- **Trade history was never anchored.** The SQLMesh trade reviewer noticed that a historical-load trade's earliest held report was its snapshot row with its final status. Real Batch1 TradeHistory: trade 353232 was pending on 2017-01-12, submitted and completed on 2017-04-10; the chain had placed it at completion. Anchored `raw.trade_history` as shape under the data-architect hat, added the real rows to the fixture, extended report_order's note, recorded the addendum, accepted the proposal as an anchor amendment. Trade-lifecycle cycle 5 sent: placed_at from the earliest held report across both sources. Expected cone: one stale group, two stale L3 artifacts. Two other proposals filed for the business: late-arriving earlier account statements (re-pin or frozen wins), market orders and first-seen-late.
- **Counterfactual compile (statement-content clauses removed).** Mixed on first reading: the Developer derived no tier or tax treatment from field names, which is the discipline the test was after, but it derived a status from the anchored action meanings under L1.history and filed no question, although the gate's content rule said to ask. Sent to an independent reviewer to classify: derivation-disciplined, policy recovered from anchors, or mixed.
- **Positions L2 cycle 1.** Gate ok: a holding-change entity copying the current trade's frozen ownership, two aggregate position entities, nonnegativity invariants, five holes carried. The Developer aggregated customer position by customer number alone because the trade reference carries no customer statement time, and called that a scope limitation. Sent to review with that as an explicit question.
- **Mutation testing** found six unprotected mutations across the two native projections; recorded as findings routed to the next authorized changes (value-correctness invariants for interpreted handoffs; IS DISTINCT FROM in recomputation audits).

### The cone, mechanically (2026-09-17)

After the trade-history anchor amendment and trade-lifecycle cycle 5, the cache plan marks one group stale in one job (`sg.placement-moment`) and ten groups hit across both jobs. Both L3 trade projections still check ok against the cycle-4 selection; on re-selection their review hash changes and the derived group's fingerprint differs, so both will be rejected until their one stale artifact is re-projected, while the ownership-history projections and the trade audits deriving from unchanged groups stay valid. Re-projection contracts written for both targets.
