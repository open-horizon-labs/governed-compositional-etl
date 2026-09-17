### CE: ce.l1.held-first-report-placement

- Status: proposed; hole `L1.hole.held-first-report-placement` opened 2026-09-17
- Level: L1, observed at L3 review of trade-lifecycle cycle 6 on duckdb-native
- Input and simulation context: a trade whose earliest report carries an unknown status and whose later report is anchored (trade 900008 in `counterexamples/proposed/ce-held-for-review-trades-v1.json`).
- Projection output as found: placement moved to the earliest anchored report, relocating the ownership pin, with nothing in the Sketch, CEs or L2 saying so.
- Question for the business: placed at the earliest readable report, or held entirely until the first report is resolved?
- Tempting wrong repair: stepping past the held report silently (the present behavior); or treating the held report's own time as the placement (reading a fact from a held report).
- Deterministic assertion: with the hole open, such a trade is reported by the held audit and no job asserts its placement; after the business answers, the answer's assertion replaces this one.
- Proposed by: sketch reviewer (Opus); filed by coordinator.
- Approved or rejected by: pending, business authority.
