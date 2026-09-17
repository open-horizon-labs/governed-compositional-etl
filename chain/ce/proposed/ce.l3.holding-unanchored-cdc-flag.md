### CE: ce.l3.holding-unanchored-cdc-flag

- Status: proposed (constructed, labeled; runnable document `counterexamples/proposed/ce-holding-unanchored-cdc-flag-v1.json`)
- Level: K (anchors) surfaced at L3, observed at L3 review of positions cycle 3 on duckdb-native
- Input and simulation context: one holding report for a fresh pair whose trade is fully pinned, carrying cdc_flag 'X'. `trade_code_meanings.cdc_flag` anchors I, U, D and null for historical rows; nothing says the vocabulary is closed.
- Projection output as found: duckdb-native (cycle 3 as first landed) admitted the report as a candidate, persisted the pair and stayed silent on all audits; duckdb-sqlmesh dropped it and `inv.eligible_holding_report_persisted` fired.
- Corrected output or behavior: both projections enumerate the anchored codes in the candidate position and the converse audit fires on both, naming the pair. Verified 2026-09-17.
- Classification: anchor gap (open vocabulary) decided in SQL, differently per engine, by a contract sentence that presumed two filter phrasings equivalent.
- Proposed generalized change: `sources-v1.json` states whether the cdc_flag domain is closed; the L2 says which reading defines the latest_change candidate set. Filed as a question for authority on both positions manifests.
- Tempting wrong repair: aligning both projections to `IS DISTINCT FROM 'D'` in the candidate position (silences the check on both engines); a flag-validity audit the anchors do not state.
- Proposed by: sketch reviewer (Opus); filed by coordinator.
- Approved or rejected by: pending, anchor authority.
