---
id: issue-8-statement-content-assumed
title: "Assume what a customer or account statement carries, pending business confirmation"
outcome: governed-compositional-etl-repair
status: assumed-pending-business-confirmation
---

# Statement content: assumed decision

**Date:** 2026-09-17

**Decision hat:** data-product-owner, acting as business authority under the repository's review-trigger protocol (AGENTS.md: present evidence and choices, select a reasonable assumed choice, record it, continue).

## Trigger

Cycle 1 of the L1 -> L2 compile for job `ownership-history`. The sketch reviewer found that the L1 Sketch says a change creates "a new dated statement" but never says what a statement carries, so the compiled customer and account entities had no standing facts. CE proposal `ce.l1.statement-content`. The business authority was asked and declined the dialog, instructing the work to continue.

## Choices presented

1. Standing and tier: customer active or inactive plus tier; account open or closed, tax treatment, owning customer. (Recommended.)
2. Status only: customer active or inactive; account open or closed and owning customer; tier and tax treatment left as holes.
3. Everything the records carry: every attribute versions the statement, pulling names, addresses, and tax identifiers into scope.

## Decision

Assume choice 1. It matches the brokerage vocabulary already used in the Sketch (standing, owner) and the jobs' purposes, and it keeps personal data out of scope. Recorded as clause `L1.statement-content`, marked assumed in the Sketch text.

## Assumptions and justification

- The facts named are the ones the brokerage means by "standing" in its own language. If the business means more or less, the clause changes and only the sufficiency groups under it re-project.
- The tempting wrong repair, deriving the facts from anchored field names, is what this decision replaces with a stated clause; the coincidence with those fields is not the justification.

## Review trigger

The business confirms or amends the enumeration. On amendment, the clause fingerprint changes, the Jev invalidation selector is consulted for each dependent sufficiency group, and only stale groups recompile.

## Addendum, 2026-09-17: constructed scenarios never introduce new things

Cycle 4 of `ownership-history` filed one question: what determines an account's owner when a constructed change is the account's first statement. No clause settled it. Under the same hat and protocol, clarify `L1.constructed-scenarios`: a constructed scenario changes something the received records already know and never introduces a customer, account, or trade the brokerage does not have. This is evidence discipline, not business policy; it settles no open hole. Consequence: the carried-forward owner always has a previous received statement to carry from, and a constructed change naming an unknown account is a labeling error to reject. Review trigger: business confirmation.

## Addendum, 2026-09-17: placement moment

The trade-lifecycle Developer filed: which received report and field is the moment of placement, given a later report can arrive without earlier ones. This is L1.hole.trade-timestamps. Under the same hat and protocol, add `L1.placement-moment`: a trade is placed at the moment of the earliest report the brokerage holds, as that report states its own time; a trade first seen through a later report is treated as placed then and marked first-seen-late for review. Completion timing stays a hole. Justification: the received records' own timestamps are the only moment the brokerage states; batch dates are not. Marking late first encounters keeps the assumption visible in the data. Review trigger: business confirmation.

## Addendum, 2026-09-17: omitted facts stand

The cycle-6 reviewer observed that the rule "a change that does not mention a fact leaves it as it last stood" had migrated into an anchor note and the L2 format, both of which declare they authorize no rule, and that Jev's split on the level question showed the entailment from identity and history was not self-evident. Under the same hat and protocol, add `L1.omitted-facts-stand` to the Sketch and remove the policy sentence from the anchors, which keep only the structural fact of which fields each action carries. Review trigger: business confirmation.

## Addendum, 2026-09-17: the customer statement is part of a trade's recorded ownership

The positions reviewer found customer position could only be summed per customer number because the trade's frozen ownership reference carries the account statement's effective time but not the customer statement's. L1.attribution-at-placement says a trade belongs to the account "and through it the customer, as they stood at the moment the trade was placed"; L1.no-phantom-positions speaks of any one statement of an account or customer. Under the domain-reviewer hat: these clauses entail that the frozen reference carries the customer statement in force at placement (the customer named by the pinned account statement, as of placed_at). This is an L2 correction at trade-lifecycle under existing clauses, not a Sketch change. Adjacent question left open: L1.hole.owner-change-reversions-account.
