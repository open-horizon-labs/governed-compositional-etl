### CE: ce.l1.first-seen-late-market-orders

- Status: proposed
- Level: L1, observed at L2 review of trade-lifecycle cycle 3
- Input and simulation context: `first_seen_late` derived as "first-encountered report's status is later than PNDG in the anchored status order".
- Projection output: a market order whose earliest report is SBMT is marked first seen late.
- Corrected output or behavior: a trade that never had a pending stage is not first seen late merely because its earliest held report is submitted.
- Classification: ambiguous sketch rule. L1.placement-moment says late first encounters are marked but not how a legitimately pending-less lifecycle is told apart.
- Proposed generalized sketch change: "A trade whose earliest held report is not the trade's first lifecycle event is marked first seen late. An order sent straight to market has no pending stage and is not first seen late when its earliest report is submitted."
- Adjacent behavior not authorized: completion timing (L1.hole.trade-timestamps); deletions.
- Tempting wrong repair: using TradeType (market versus limit) from the received row to decide, which is interpreting an anchored code and would be allowed once anchored, but the Sketch has not said that trade type governs the lifecycle's first event.
- Deterministic assertion: none until the clause lands; the derivation stays a review flag with its premise stated.
- Proposed by: sketch reviewer (Opus), trade-lifecycle cycle 3.
- Approved or rejected by: pending, business authority.
