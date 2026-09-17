### CE: ce.l1.market-order-seen-pending

- Status: accepted 2026-09-17 (business authority); hole `L1.hole.market-order-seen-pending` closed by the answer
- Level: L1, observed at L3 review of trade-lifecycle cycle 5 on both engines
- Input and simulation context: a market order (TMB) whose earliest held report is PNDG. Under the amended `L1.placement-moment`, a market order has no pending stage; the clause does not say what seeing one means.
- Projection output: both engines wrote `first_seen_late = false` by rank arithmetic (pending ranks below submitted) and the audit excluded the case from its scope, so nothing surfaced it.
- Corrected output or behavior: the trade is held and reported, like an unknown code, until the business answers the hole.
- Question for the business: is a pending market order a late first encounter, a mis-typed order, or a record error?
- Answer (business authority, 2026-09-17): none of those. The brokerage's own systems record a market order as pending on receipt, before routing it; that pending record is the order's own first lifecycle event, so such a trade is not first seen late. `L1.placement-moment` carries the answer and the hole is closed.
- Tempting wrong repair: treating a pending market order as not late by rank arithmetic (the present behavior before this hole), or as late because pending is not its first event.
- Deterministic assertion: with the hole open, a run over a fixture carrying such a trade fails exactly the held-for-review audit on every engine; after the business answers, the answer's own assertion replaces this one.
- Proposed by: sketch reviewer (Opus); filed by coordinator.
- Approved or rejected by: approved, business authority (2026-09-17). Downstream: trade-lifecycle L2 and both L3 projections; the held-for-review counterexample's trade 900004 changes from held to a persisted trade that is not first seen late.
