### CE: ce.l1.unknown-codes-held

- Status: accepted 2026-09-17 (business authority, demonstration); new clause `L1.unknown-codes`
- Level: L1, observed at L3 review of trade-lifecycle cycle 5 on both engines
- Input and simulation context: a trade whose first report carries an order type outside the anchored four. Both engine projections wrote `first_seen_late` NULL into a non-nullable attribute and no audit fired; the L2 called the case a review trigger but the Sketch gave the compile nothing to do with it.
- Projection output: silent NULL on both engines; the SQLMesh comments called it "undefined", the native comments "not decided here"; neither surfaced it.
- Corrected output or behavior: the record is held and reported as a violation naming the record and the code; nothing is derived from it.
- Classification: Sketch gap. Every job interprets codes; no clause said what an unknown one means.
- Generalized sketch change: `L1.unknown-codes` (evidence discipline): a report carrying a code the vocabulary does not name is held for review, never interpreted, defaulted or dropped, and every job reports it.
- Adjacent behavior not authorized: what the brokerage does with the held record.
- Clarification added 2026-09-17 after the trade-lifecycle L2 review found the undecided case relocated (a held later report against a non-nullable outcome; a trade known only through held reports): a held report changes nothing and creates nothing; facts stand as last stood; a thing known only through held reports is not yet known; the hold is reported. Assumed clarification, business confirmation is the review trigger.
- Tempting wrong repair: an `ELSE` branch (defaulting), or dropping the report from the candidate set (which positions did for cdc_flag, see `ce.l3.holding-unanchored-cdc-flag`; that CE now resolves under this clause too).
- Deterministic assertion: a run over any fixture carrying an unknown status, order type or change flag fails exactly the audit for the unknown-codes invariant of the job that reads it, on every engine.
- Proposed by: sketch reviewers (Opus), trade-lifecycle L3 cycle 5; filed by coordinator.
- Approved or rejected by: approved, business authority (2026-09-17).
