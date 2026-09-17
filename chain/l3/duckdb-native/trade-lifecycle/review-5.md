# Review 5 (sketch reviewer, scoped): trade-lifecycle on duckdb-native, L3 cycle 5 (verdict: fail, routed to the Sketch)

Scope: the cycle-5 re-projection under the amended `L1.placement-moment`: order_type column, the first-seen-late derivation over the order type's first lifecycle event, the restated audit. Evidence: check ok (8 audits); run ok; two-phase ok; mutate zero unprotected; the market-order counterexample yields 900002 not late and 900003 late; cross-engine compare identical.

## Finding

Faithful on every claimed case. On the two cases the L2 left undefined the projection wrote a value and nothing surfaced it: a market order first reported PNDG got `false` by rank arithmetic; an order type outside the vocabulary got NULL in a non-nullable attribute. Both engines did the same, so compare could not see it. The reviewers asked for NULL guards and an L2 invariant.

## Coordinator disposition

Not fixed in SQL. The cause is upstream: the Sketch said what a market order's earliest submitted report means and nothing about one seen pending, and no clause said what a code outside the brokerage's vocabulary means, so two Developers on two engines each invented a value. The Sketch gained `L1.unknown-codes` (held for review, never interpreted, defaulted or dropped; every job reports it) and `L1.hole.market-order-seen-pending`; CEs `ce.l1.unknown-codes-held` (accepted) and `ce.l1.market-order-seen-pending` (proposed) are filed, with the runnable document `counterexamples/proposed/ce-held-for-review-trades-v1.json`, which today is silent on both engines. Every job recompiles under the new clause; this projection is discarded and re-projected from the new selection. Also recorded for the L2: the order_type frozen check lives inside another invariant's audit and wants its own invariant.

Rejected artifacts: `trade.sql` / `models/trade.sql` and the first-seen-late audit, superseded by the Sketch change.
