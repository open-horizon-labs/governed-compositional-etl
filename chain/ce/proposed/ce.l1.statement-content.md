### CE: ce.l1.statement-content

- Status: proposed
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
- Approved or rejected by: pending, business authority (data-product-owner hat, the user).
- Decision rationale: pending.
- Sketch revision reference: pending.
- Projection revision reference: pending.

### Anchor change proposed alongside (not policy): mutation role `per_statement`

The role set identity / frozen_from_first_encounter / mutable / none has no term for a value that belongs to one dated statement and is never replaced in place. The reviewer found every versioned attribute forced into `mutable` by elimination. Under the data-architect hat, add `per_statement` to the vocabulary, and a gate rule that non-identity attributes of a `versioned` entity may not be `mutable`. This is a K change; it settles no business question.
