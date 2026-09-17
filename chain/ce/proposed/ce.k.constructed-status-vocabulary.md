### CE: ce.k.constructed-status-vocabulary

- Status: proposed
- Level: K (anchors), observed at L3 review of ownership-history cycle 3 on duckdb-sqlmesh
- Input and simulation context: `ce.account_changes.status_id` is an unconstrained string in `sources-v1.json`; `inv.constructed_scenarios_labeled` constrains only `provenance`. The invariant `inv.account_status_matches_producing_source` says a constructed statement's status equals the row's own `status_id`.
- Projection output: the SQLMesh entity SQL narrows the pass-through with `CASE status_id WHEN 'ACTV' THEN 'ACTV' WHEN 'INAC' THEN 'INAC' END`, so a constructed row asserting any other status projects a null status; the first draft of the audit copied the same CASE and so could not see it. The native entity SQL and audit pass the value through.
- Corrected output or behavior: if `status_id` is meant to be restricted to the anchored `status_codes`, the anchor says so and a value outside the vocabulary is a violation with its own name; if it is a free pass-through, the narrowing CASE is an unauthorized projection decision and the engines must agree on pass-through.
- Classification: anchor gap surfaced as a cross-engine divergence in a constructed source's vocabulary.
- Proposed generalized change: `sources-v1.json` entity `ce.account_changes` gains a `status_codes` reference for `status_id` (the same vocabulary as the historical actions), and the L2 invariant's constructed arm then reads as a vocabulary-checked pass-through.
- Adjacent behavior not authorized: what a constructed status outside the vocabulary would mean for the account.
- Tempting wrong repair: mapping unknown constructed statuses to inactive, or dropping such rows; both invent policy for a source that exists to state scenarios plainly.
- Deterministic assertion: after the amendment, a constructed row with `status_id` outside the vocabulary fails one audit on both engines and both engines' account tables are identical.
- Proposed by: sketch reviewer (Opus), ownership-history L3 cycle-3 review on duckdb-sqlmesh; filed by coordinator.
- Approved or rejected by: pending, anchor authority.
