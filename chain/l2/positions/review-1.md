# Sketch review 1: job positions (verdict: needs-authority)

Reviewer: Opus judge.

Finding: customer position is aggregated per customer number, not per customer statement. L1.no-phantom-positions names "any one statement of an account or customer" and L1.attribution-at-placement fixes ownership "and through it the customer, as they stood" at placement; the trade's frozen reference pins the account statement's time but names the customer only by number. Grouping by number nets a holding opened under one customer statement and closed under another to zero, hiding exactly what the clause says a negative reveals. Not a gap (no L1 hole covers it) and not an honest scope limitation (the material exists upstream); a question for authority, which the Developer resolved by omission.

Other notes: sg.no-phantom-positions should also be bounded by L1.hole.change-effective-time (a holding change whose trade pin does not resolve drops out of every sum); L1.hole.owner-change-reversions-account not carried though it bounds the copied pin; inv.holding_change_not_constructed's statement is inaccurate (three attributes come from logical.trade); no invariant makes the quantity update-in-place and D exclusion checkable; report_order is cited for holding-change reports though the anchor states it for trade reports; aggregate keys declared computed while the sum is a handoff.

Adjudication (coordinator, domain-reviewer hat): the clauses entail the customer statement pin on the trade. This is a trade-lifecycle L2 correction under existing clauses (cycle 6), then a positions cycle 2 keying customer position on (customer_number, customer_statement_effective_from). No L1 change.
