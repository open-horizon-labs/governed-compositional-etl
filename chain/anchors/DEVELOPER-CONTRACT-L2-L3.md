# Developer brief and change contract: L2 -> L3 (one job, one engine target)

## Agent brief

**Purpose:** project one reviewed L2 semantic model onto one engine target so the model runs, without seeing the L1 Sketch.

**Aim:** SQL and audits that implement exactly the selected L2 elements for the job, read only the sources and upstream entities the model's handoffs name, respect every mutation role on every write, and check every deterministic invariant, with each artifact recording the L2 element ids it derives from.

**Mechanism:** the semantic model already carries the meaning. If the projection derives each column, join, and write surface from a named L2 element and each audit from a named invariant, then a change to one L2 group re-projects only the artifacts deriving from it, and a defect found here is a projection defect unless the model itself is silent, in which case it is a question for the model's authority, never a decision made in SQL.

**Feedback:** the gate (`.venv/bin/python scripts/chain_l3.py check <target> <job>`) checks layout, provenance, read containment, and the write-surface guard; `run` loads the fixture and executes the projection and audits. A reviewer judges the projection against the L2 model.

**Guardrails:** the L2 model and the engine profile are the only authority; no policy from data shape; no reading L1, other jobs' models except upstream ones the model names, or anything under `oracle/`, `counterexamples/`, `.oh/`, `contracts/`, `docs/`, `sketches/`.

## An invariant that reports rather than holds

Some invariants carry `reports: true`. Their rows are findings the chain hands the business, not defects in your projection: the compiled thing did exactly what the Sketch told it to, and the records contain something only the business can resolve. Write the audit exactly as you would any other, and never weaken it to keep a run quiet. The rows are the point.

The two engines need different declarations, but the harness reports them identically. On `duckdb-native` nothing extra is required. On `duckdb-sqlmesh` an audit that returns rows blocks promotion, which is the wrong outcome for a finding, so declare it non-blocking: `AUDIT (name "inv.x", blocking false);`. SQLMesh 0.236.1 supports this, and its plan then applies while logging a `[WARNING]`. Register the audit in the manifest and in the model's audits list like any other. Note that `sqlmesh audit` still counts a non-blocking failure as an audit error; the harness records that verdict under `sqlmesh.audit_ok` but does not decide your run on it.

Reading the reports. Every path counts a reporting invariant's rows under `reported` rather than `violations`, so the key tells you what a count means and you should never index one blindly. `run` stays `ok` while listing the rows under `findings_for_the_business`. `simulate` separates two questions that are easy to conflate: `fired` is every audit that returned rows, because a counterexample expecting a report is answered by a reported audit and must not read as silent, while `failures` is only the must-hold audits that broke. When you judge whether a counterexample was *caught*, read `failures`. `mutate` ignores reporting invariants entirely: a report already fires on the received fixture, so it is no evidence that a mutation was noticed.

## Acceptance is not yours

`chain_l3.py stamp` records that a reviewed projection is accepted. It is the reviewer's step, never the Developer's, and the mechanism enforces part of that: stamping refuses a projection whose content changed after the review that accepted it, and refuses a review whose verdict is not pass. Do not run it, and do not write or edit `review.json` or any `review-*.md`; they are the reviewer's record of what was judged, and the reviewer's name is on them.

Two consequences you will see. `check` reports `acceptance` separately from `status`: a projection you are still working on is well-formed and not yet accepted, which is the normal mid-cycle state and not a problem. And `run` refuses to build on an upstream job whose projection is not accepted, so if an upstream is mid-cycle, wait for its acceptance rather than compiling on top of it.

## You may be one of several Developers in this working tree

Other Developers may be compiling other jobs or other engine targets at the same time as you, in the same checkout.
So `git status` will show files modified that you did not write, and that is normal and expected. A modified file
outside your write surface is someone else's work in progress. It is not evidence of a tool bug, and it is never
yours to clean up.

Therefore: never run a git command that changes the working tree. No `git checkout --`, `git restore`, `git stash`,
`git clean`, `git reset`, `git checkout <branch>`. Reading is fine -- `git status`, `git diff`, `git log`, `git show`.
If you believe a tool corrupted a file, say so in your final message and leave the file alone. Reverting another
Developer's file destroys work in flight, and the destruction is silent: the other Developer does not find out.

For the record, because this has been misdiagnosed once and cost a concurrent Developer its edits: `chain_l2.py check`
writes nothing at all, and `chain_l2.py weave` writes only `chain/weave.json`, which is its own declared output.
Neither one writes any job's `semantic-model.json`. If you see another job's model modified while you work, another
Developer is writing it.

## A review finding is a claim, not an authority

When a reviewer reports a defect, it is telling you what it believes. It is not telling you a fact you must adopt.
Reviewers read quickly across a lot of material and they do make mistakes of detail -- a transposed pair of ids, a
misread partition key, a line number off by a file.

So: where a finding asserts something you can check, check it. If the check agrees, fix the defect. If the check
disagrees, say so in your report, show what you ran and what it returned, and do not write the finding's version
into the model. Writing a claim you have evidence against is worse than leaving a gap, because a gap is visible as
a gap while a confident false statement reads as settled -- and the model is what the next Developer and every
projection compile from.

This has happened. A reviewer called an invariant vacuous because it read a counterexample's constructed pair
`(372101, 353232)` as the received pair `(353232, 372101)` -- the reverse ordering, and a different partition key.
The Developer was told the measurement and deferred to the finding anyway, on the grounds that verifying it was
the reviewer's job rather than its own, which put a falsehood about the fixture into a coverage claim. One query
would have settled it.

Deferring to a review is not humility when you hold the evidence. Your job is to be right about your own model.

## Change contract (CESS working form)

- **Prior policy authority:** `chain/l2/<job>/semantic-model.json`, restricted to `selected_element_ids` in `chain/l2/<job>/review.json`. Deferred elements are not projected; rejected elements never.
- **Exact active change authority:** none for initial compilation.
- **Stable projection contracts:** output under `chain/l3/<target>/<job>/`: `manifest.json` (see `chain/anchors/l3-manifest-v1.schema.json`), one SQL file per entity named `<entity>.sql`, one SQL file per deterministic invariant under `audits/<invariant id>.sql` returning zero rows when the invariant holds, and nothing else of yours. Governance files the coordinator places beside them (`change-contract-N.md`, `review-N.md`, `review.json`, `adjudication-*.md`) are not yours to create, edit, or delete; the gate ignores them. The engine profile is `chain/profiles/<target>.json`; follow its strategies. Source tables exist under the schemas the anchors name (`raw.*`, `ce.*`); upstream entities exist as `governed.<entity name>`; you create `governed.<entity name>` for your job's entities.
- **Write surface:** for `versioned` entities, rebuild from the complete change feed (no updates in place; `per_statement` values are never updated). For `incremental_by_identity` entities, a MERGE whose WHEN MATCHED UPDATE SET names only mutable-role columns; frozen columns are written on insert only. For `aggregate`, rebuild. The guard reads your SQL and rejects any write to a frozen or per_statement column in an update path.
- **Read containment:** each entity's SQL may reference only the source entities its handoffs name and the upstream entities its handoffs name. The gate reads table references from the parsed SQL.
- **Selectors:** implement each handoff's `selector` as stated (for example `as_of_event_time` selects the latest statement of the identity whose effective_from is at or before the event moment; use an effective_to only if the model declares one, `status_from_action_meaning` maps codes exactly as `chain/anchors/sources-v1.json` states them, `carried_forward_from_previous_statement` takes the last non-null earlier statement of the same identity). `computed_within_entity` derivations follow their stated rule.
- **Forbidden shortcuts:** inventing a mapping the model or anchors do not state; reading L1; resolving ownership from a current statement when the model says as-of; hand-tuning to the fixture; any table outside the containment set.
- **Conflict protocol:** if the model is silent or ambiguous about something the SQL must decide, write one precise question in `manifest.json` under `questions_for_authority`, omit the affected artifacts, and return. Never resolve it in SQL.

## Target-specific layout: SQLMesh targets

When the profile's orchestrator is SQLMesh, each entity artifact is `models/<entity>.sql`: a SQLMesh `MODEL (...)` header naming `governed.<entity>` with `kind FULL` for versioned and aggregate entities, or `kind CUSTOM (materialization 'governed_merge', materialization_properties (...))` for incremental_by_identity entities per the profile, followed by one SELECT. Each audit is `audits/<invariant id>.sql`: an `AUDIT (name <invariant id>);` header followed by one SELECT over `@this_model` returning zero rows when the invariant holds; the MODEL header lists its audits. Upstream jobs' models on the same target are placed in the same project by the runner; reference them as `governed.<entity>`. The `governed_merge` materialization is supplied by the runner; you do not write it. Everything else in this contract applies unchanged: containment, provenance, the write guard, and the conflict protocol.

Non-obvious SQLMesh mechanics a Developer found: audit names containing dots must be double-quoted both in `AUDIT (name "inv.x");` and in the model's `audits ("inv.x", ...)` list, or the parser truncates them; a model whose audit joins another model must declare `depends_on (governed.<other>)` because the dependency is not inferable from the model's own SELECT.

## Frozen protects against later reports, not against a changed derivation

A `frozen_from_first_encounter` value is never updated by a later report. When the L2 model changes how that value is derived (a new source, a corrected selector), existing rows hold values derived the old way and the MERGE will keep them. A stale sufficiency group on a frozen attribute is therefore a restatement signal: the entity is rebuilt from the sources under the new derivation, then incremental runs resume. The runner's fixture simulations rebuild from scratch; a production target would need an explicit restatement step here, and the cache's stale set names exactly which entities.
