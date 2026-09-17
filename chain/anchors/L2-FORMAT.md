# L2 semantic model: format and vocabulary (anchor K for the L1 -> L2 Developer)

You compile one job of `sketches/l1-brokerage-intent-v1.md` into `chain/l2/<job>/semantic-model.json`, valid against `chain/anchors/semantic-model-v2.schema.json`. You derive; you do not decide. Every element cites the L1 clause ids it derives from. If a clause does not entail an element, the element does not exist. If a hole covers it, record the hole and stop there.

## Mutation roles (on types, never on attributes)

- `identity`: the value that says which thing a row is about. Two rows with equal identity values describe the same thing.
- `per_statement`: the value belongs to one dated statement about a thing. It is never replaced in place; a later change creates a new statement beside it. Derive this from clauses about kept history. Non-identity attributes of a `versioned` entity carry this role, never `mutable`.
- `frozen_from_first_encounter`: set when the thing is first seen; never changed by later reports about the same thing. Derive this only from a clause that says something does not change after it is first recorded.
- `mutable`: may be replaced by a later report about the same thing.
- `none`: not carried into any entity; a source-only value.

## Entity history kinds

- `versioned`: one row per dated statement about a thing; rows carry an effective interval and a current flag. Derive from clauses about kept history and as-of.
- `incremental_by_identity`: one row per thing; later reports update mutable attributes and leave frozen ones. Derive from clauses about later reports updating outcome but not ownership.
- `append_by_identity`: one row per event, identified by its own identifiers, never updated.
- `aggregate`: one row per group, recomputed from another entity.

## Handoffs

A handoff moves a value from a source field (`raw.<entity>.<field>` from `chain/anchors/sources-v1.json`, or `ce.<entity>.<field>` for labeled constructed scenarios) or from an upstream job's entity attribute (`logical.<entity>.<attribute>`) into an attribute. `selector` names how one value is chosen when several qualify. You may consume only your own job's entities and those of jobs listed in `upstream_jobs`.

## What "derived" means here

- Name the clause. `derived_from` is not decoration; the harness rejects an element citing a clause that does not exist, a frozen role with no clause, or an entity whose job does not list the clause.
- Do not read the received data to decide policy. Field names and types are shape, not meaning.
- Do not name engines, SQL, tables, or files. That is level 3.
- Leave every L1 hole that touches your job as a hole in your model, with the L1 hole id, and do not fill it.
- If the Sketch and anchors conflict or leave the permitted derivation ambiguous, put exactly one precise question in `questions_for_authority`, omit the affected elements, and return.

## Every element is a step, not a row

An element without justification is decoration and is rejected in review. Each type, entity, attribute, handoff, and invariant carries:

- `necessity`: why the clauses it cites make this element indispensable. Write it so a reader can check it against the clause text alone.
- `parallel_assumption`: the condition under which this derivation is credible now, and which would trigger review if it stopped holding (for example: "change records arrive as a complete feed, so ordering by effective time is total").
- `feedback`: the invariant ids, gate names, or `sketch-review` that check this element.
- `disposition`: write `candidate`. Reviewers promote steps to selected outside your file. Write `rejected` with `rejected_because` for a derivation you considered and the clauses forbid; keeping it visible protects the next Developer. Holes are the `deferred` steps.
- `owner_hat`, `review_trigger`: who reassesses this element and when.
- `sufficiency_group`: the group this element belongs to.

## Sufficiency groups

Sufficiency is a claim about a set, never about one element. For every clause your job lists, declare at least one group: its parent clauses, its members, its mode (`all_required`, `alternatives`, `conditional`), a coverage claim a reader can check against the clause text, and a named gap (`none`, or the L1 hole that bounds it). A clause with no group is a gap the gate reports. A member that does not exist is an error.

## Rules the gate enforces because a review found them missing (cycle 1)

- A `versioned` entity's non-identity attributes carry `per_statement`, not `mutable`.
- A `versioned` entity carries at least one attribute that is not an identifier, an effective time, or a current flag; otherwise its as-of answers are content-free. If the Sketch does not say what a statement carries, that is a question for authority, not a gap to paper over.
- A handoff into a `versioned` entity from a source that supplies no effective-time handoff to that entity is not projectable; mark it `deferred` and cite the hole that blocks it.
- A group's `gap` is `none` or names an L1 hole id. Anchor limitations go in `questions_for_authority`.
- An element's `derived_from` is a subset of its group's `parent_clauses`.
- A hole's `blocks` lists every group that contains a deferred member.
