# Developer brief and change contract: L1 -> L2 (one job)

## Agent brief

**Purpose:** compile one job of the brokerage's intent Sketch into a semantic model that a later Developer can project to any engine without seeing the Sketch.

**Aim:** a model whose every element a reviewer can trace to a clause and judge necessary, whose groups cover every clause the job lists, and which leaves every hole open.

**Mechanism:** meaning is carried by derivation, not by convention. If each element states why its clauses require it and each group states why its members cover the clause, then a reviewer can reject decoration, detect gaps, and a change to one clause invalidates exactly the groups under it. That is what makes the chain re-projectable instead of re-authored.

**Feedback:** the gate (`.venv/bin/python scripts/chain_l2.py check <job>`) checks structure, derivation, typing, containment, and group coverage. A separate reviewer judges each element's necessity and each group's coverage claim against the clause text, using the job's feedback line in the Sketch as the acceptance test.

**Guardrails:** the clauses are the only authority; holes stay open; no engine, SQL, table, or file names; no rule from data shape or warehouse habit; no reads outside the listed files; a conflict produces one question, not a guess.

## Change contract (CESS working form)

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for your job only.
- **Exact active change authority:** none. Initial compilation. No counterexample is active.
- **Approved outputs and checked fields covered by that authority:** none yet.
- **Current rules that must be preserved:** every clause your job lists, exactly as written.
- **Explicit holes that must remain open:** every `L1.hole.*` that touches your job, carried as a deferred step with its L1 hole id.
- **Retained behavior that must not regress:** none yet.
- **Stable projection contracts:** `chain/anchors/semantic-model-v2.schema.json`, `chain/anchors/L2-FORMAT.md`, `chain/anchors/sources-v1.json`. Output is `chain/l2/<job>/semantic-model.json` and nothing else.
- **Forbidden shortcuts:** deriving from a field name or type; deriving from what warehouses usually do; naming an engine, SQL, table, or file; a mutation role without a clause that entails it; an element without necessity and parallel assumption; a clause without a sufficiency group; consuming a job that is not upstream of yours; reading anything under `oracle/`, `counterexamples/`, `.oh/`, `contracts/`, `docs/`, or other Sketches.
- **Conflict protocol:** leave all files unchanged except your model, put exactly one precise question in `questions_for_authority`, omit the affected elements, return.

## Behavior contract

1. Read the Sketch. For each clause your job lists, write what it entails for your job. If a clause entails nothing for your job, say so in the cycle report.
2. Write the model. Every element is a step: clauses, necessity, parallel assumption, feedback, disposition `candidate`, owner hat, review trigger, group.
3. Declare sufficiency groups per clause with coverage claim and named gap.
4. Run the gate. Fix structural problems. A derivation problem you cannot fix without adding policy is a question for authority.
5. Return a cycle report: clauses used, what each entails, groups and their gaps, holes carried, questions, gate result. Do not paste the JSON.

## Review criteria the judge will apply

- Does each element's necessity follow from the cited clause text alone?
- Does each group's coverage claim hold, and is the named gap honest?
- Is any hole filled, any engine named, any role unsupported by a clause?
- Would a Developer for the next level be able to project this without seeing the Sketch?

## Stop conditions

Return immediately with a question when the Sketch and anchors conflict, when a clause is ambiguous for your job, or when the gate reports a derivation problem you cannot fix without adding policy.
