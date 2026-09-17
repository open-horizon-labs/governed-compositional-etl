# Sketch review 1: job ownership-history (verdict: fail)

Reviewer: Opus judge, given only the L1 Sketch, the L2 anchors, and the compiled model.

Summary of findings (full text retained in the session transcript, 2026-09-16):

1. Incremental change records are live handoffs into statements the model refuses to date; they must be deferred under L1.hole.change-effective-time, and the hole's `blocks` must include sg.identity and sg.owner-standing.
2. No element carries what a statement says; as-of answers are content-free. Possible sketch gap; raised as ce.l1.statement-content. Not the Developer's to fill.
3. Mutation roles chosen by elimination: `statement_effective_from` and `account_owner_reference` are `mutable`, which L1.history forbids for statement values. Anchor gap: no `per_statement` role existed.
4. Two no-overlap invariants cite L1.current-version on an argument that does not hold; decorative citation.
5. Group gaps that name neither `none` nor an L1 hole; an anchor limitation belongs in questions_for_authority.
6. Possibly missing holes: L1.hole.closed-account-activity, L1.hole.batch-identity (low confidence).
7. A handoff in sg.constructed-scenarios cites clauses outside that group's parents.

What the model got right: same-moment lookup through owning_customer_number rather than re-versioning accounts on customer change (correct non-filling of L1.hole.owner-change-reversions-account); constructed-scenario labeling rides only on ce.-sourced rows; schema-valid; every group member resolves.

Disposition: fail. Items 1, 3 (once the anchor exists), 4, 5, 6, 7 are projection defects the Developer repairs under the current Sketch. Item 2 awaits the business authority.
