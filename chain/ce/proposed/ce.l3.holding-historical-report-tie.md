### CE: ce.l3.holding-historical-report-tie

- Status: proposed (constructed, labeled; runnable document `counterexamples/proposed/ce-holding-historical-report-tie-v1.json`)
- Level: L3 positions, observed at L3 review of positions cycle 2 on duckdb-sqlmesh
- Input and simulation context: two Batch1 historical reports of one holding-change pair, same batch_date, no CDC columns, different after quantities. `report_order` gives no tie-break; `L1.hole.batch-identity` bounds it.
- Projection output as found: duckdb-native adopted one candidate and ran clean; duckdb-sqlmesh's `inv.holding_quantity_updates_in_place` audit treated the tie as a violation and refused the plan.
- Corrected output or behavior: both engines accept whichever undominated candidate the projection adopted; the tie stays the hole's case. Verified 2026-09-17 after positions L3 cycle 3: silent on both.
- Classification: audit semantics deciding a deferred hole in SQL on one engine.
- Proposed generalized change: none at L1 or L2 beyond naming the tie in `hole.batch_identity` (done, positions cycle 6); a tie-break is anchor authority's.
- Tempting wrong repair: ordering ties by file position; summing tied reports.
- Proposed by: sketch reviewer (Opus); filed by coordinator.
- Approved or rejected by: pending, anchor authority for batch identity.
