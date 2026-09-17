### CE: ce.l1.statement-content

- Status: approved (assumed; pending business confirmation)
- Level: L1 (intent Sketch), observed at L2 review of job ownership-history, cycle 1
- Input and simulation context: `chain/l2/ownership-history/semantic-model.json` compiled by a Sonnet Developer from `sketches/l1-brokerage-intent-v1.md` under `chain/anchors/DEVELOPER-CONTRACT-L1-L2.md`; gate `chain_l2.py check` passed; sketch review by an Opus reviewer (chain/l2/ownership-history/review-1.md).
- Projection output: `logical.customer` carries only customer_number, effective_from, is_current; `logical.account` adds owning_customer_number and provenance. No element carries what a statement asserts about the customer or account.
- Corrected output or behavior: each dated statement carries the facts the brokerage reports about the customer or account at that moment, so an as-of answer has content.
- Classification: missing sketch rule. L1.history says a change makes "a new dated statement about the same one" and L1.owner-standing says an account's standing includes its owner's standing, but no clause says what a statement or a standing consists of.
- Existing violated clause, if any: none violated; L1.history and L1.owner-standing are under-specified.
- Proposed generalized sketch change: add a clause `L1.statement-content`: "A statement about a customer or an account carries the facts the brokerage reports about it at that moment. For a customer: [enumerated by the business]. For an account: [enumerated by the business], and which customer owns it." The enumeration is the business authority's to give.
- Adjacent behavior not authorized by this decision: whether a customer change re-versions its accounts (L1.hole.owner-change-reversions-account) stays open; when incremental changes take effect (L1.hole.change-effective-time) stays open.
- Tempting wrong repair: the Developer or reviewer picks the facts from the anchored field names (c_st_id, c_tier, ca_st_id, ca_tax_st) because they are there. That derives policy from data shape, which L2-FORMAT forbids and the guardrail `no-policy-from-structure` names.
- Why the wrong repair is plausible: the fields are exactly the ones a warehouse engineer would pick, and the fixture would make any choice look right.
- Deterministic assertion to add, or why none is expressible: gate rule: a `versioned` entity must carry at least one non-identity, non-time, non-flag attribute, otherwise its as-of answers are content-free. Expressible and added to `chain_l2.py check`. Which facts those are stays a review judgment against the amended clause.
- Sketch review still required: yes, of the recompiled model against the amended clause.
- Proposed by: sketch reviewer (Opus), adjudicated as a proposal by the coordinator.
- Approved or rejected by: data-product-owner hat, assumed decision `.oh/metis/issue-8-statement-content-assumed.md`; business confirmation pending.
- Decision rationale: the enumeration is the brokerage's own standing vocabulary; personal data stays out of scope; a later amendment re-projects only the groups under the clause.
- Sketch revision reference: `sketches/l1-brokerage-intent-v1.md`, clause `L1.statement-content`, added 2026-09-17, marked assumed.
- Projection revision reference: `chain/l2/ownership-history/semantic-model.json`, cycle 2 (pending).

### Anchor change proposed alongside (not policy): mutation role `per_statement`

The role set identity / frozen_from_first_encounter / mutable / none has no term for a value that belongs to one dated statement and is never replaced in place. The reviewer found every versioned attribute forced into `mutable` by elimination. Under the data-architect hat, add `per_statement` to the vocabulary, and a gate rule that non-identity attributes of a `versioned` entity may not be `mutable`. This is a K change; it settles no business question.

### Sketch change: sc.l1.statement-content

- Active approved CE, or `none`: ce.l1.statement-content
- Approved input/output fields and clause: content-free `logical.customer` and `logical.account` (input); statements carrying standing facts (corrected); clause `L1.statement-content`.
- Proposed general rule: a dated statement carries the brokerage's standing facts at that moment, enumerated for customer and account.
- Why that rule is required by the CE: without it the job's own purpose, how a customer or account stood, has no content and the reviewer cannot judge L1.history or L1.owner-standing.
- Earlier rules and anchors preserved: all existing clauses unchanged; anchors unchanged except the `per_statement` role added under the data-architect hat.
- Adjacent choices left open: L1.hole.owner-change-reversions-account, L1.hole.change-effective-time, L1.hole.closed-account-activity, L1.hole.batch-identity, L1.hole.deletions.
- Decision: approve (assumed)
- Decision rationale: see `.oh/metis/issue-8-statement-content-assumed.md`.
- Approver: data-product-owner hat under the review-trigger protocol; business confirmation is the review trigger.
