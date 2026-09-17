# Change contract, L3 cycle 3: trade-lifecycle on duckdb-native (audit null sensitivity)

- **Prior policy authority:** `chain/l2/trade-lifecycle/semantic-model.json` as selected (unchanged since cycle 2).
- **Exact active change authority:** none at L2. Projection-defect correction authorized by the duckdb-native review-2 and the mutation findings: audit predicates that compare with `<>` where the invariant states equality let a NULL pass through three-valued logic.
- **Authorized correction:** in every audit under this job, replace equality comparisons used to detect a difference with `IS DISTINCT FROM` (and `IS NOT DISTINCT FROM` where equality is asserted), so a NULL projected value counts as a violation of an invariant that states equality or an iff. Also make the "earlier report than placed_at" legs treat a NULL placed_at as a violation. Do not change models, manifests beyond the audit list if needed, or any predicate's meaning otherwise.
- **Acceptance:** `chain_l3.py check` ok; `run` ok; on duckdb-native, `chain_l3.py mutate duckdb-native trade-lifecycle` reports zero unprotected mutations (owning_account_number null, placed_at null, first_seen_late null must each fire an audit); on duckdb-sqlmesh, the same predicates apply and the runner's audits stay green.
- **Forbidden shortcuts / conflict protocol:** unchanged.
