# Sketch review 6 (scoped): job trade-lifecycle (verdict: fail, consistency)

Reviewer: Opus judge. Customer statement pin correct in type, role, selector, citations, and invariant coverage; sg.placement-moment's claim honest about the pair of statements; every review-5 item addressed; hole/gap agreement holds; no unauthorized element edited.

Defect: `inv.trade_ownership_provenance_reachable.parallel_assumption` still says logical.account "continues to be the only source of a trade's ownership reference", false now that logical.customer feeds the frozen reference; `sg.constructed-scenarios.coverage_claim` says nothing about why the customer pin cannot introduce an unlabeled constructed fact (logical.customer has no provenance attribute; no ce.customer_* source is anchored) and speaks of the pinned statement in the singular.

Recommendations: placed_at and both its handoffs should list inv.trade_placed_at_matches_earliest_report in feedback; the entity's review trigger should span both sources; the customer-pin elements should also cite L1.lifecycle-mutates-outcome like their siblings; hole.change_effective_time should name owning_customer_effective_from among the pins that may be unavailable.
