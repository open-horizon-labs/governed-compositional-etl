# Developer brief and change contract: L2 -> L3 (one job, one engine target)

## Agent brief

**Purpose:** project one reviewed L2 semantic model onto one engine target so the model runs, without seeing the L1 Sketch.

**Aim:** SQL and audits that implement exactly the selected L2 elements for the job, read only the sources and upstream entities the model's handoffs name, respect every mutation role on every write, and check every deterministic invariant, with each artifact recording the L2 element ids it derives from.

**Mechanism:** the semantic model already carries the meaning. If the projection derives each column, join, and write surface from a named L2 element and each audit from a named invariant, then a change to one L2 group re-projects only the artifacts deriving from it, and a defect found here is a projection defect unless the model itself is silent, in which case it is a question for the model's authority, never a decision made in SQL.

**Feedback:** the gate (`.venv/bin/python scripts/chain_l3.py check <target> <job>`) checks layout, provenance, read containment, and the write-surface guard; `run` loads the fixture and executes the projection and audits. A reviewer judges the projection against the L2 model.

**Guardrails:** the L2 model and the engine profile are the only authority; no policy from data shape; no reading L1, other jobs' models except upstream ones the model names, or anything under `oracle/`, `counterexamples/`, `.oh/`, `contracts/`, `docs/`, `sketches/`.

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
