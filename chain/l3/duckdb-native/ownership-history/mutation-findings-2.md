# Audit sensitivity findings (mutation testing), ownership-history on duckdb-native, cycle 3

18 mutations, 0 unprotected (`mutate` reports zero unprotected).

The three mutations left unprotected in `mutation-findings-1.md` now fire:

- **Customer status swap** (swapping `status` between two customer statements) is caught by `inv.customer_status_matches_producing_source`, which recomputes the expected status from `raw.customer_mgmt_action.action_type` under the anchored action_type_meanings and compares with `IS DISTINCT FROM`.
- **Account status swap** (swapping `status` between two account statements) is caught by `inv.account_status_matches_producing_source`, which recomputes the expected status from `raw.customer_mgmt_action.action_type` (historical rows) or `ce.account_changes.status_id` (constructed rows) and compares with `IS DISTINCT FROM`.
- **tax_treatment swap** (swapping `tax_treatment` between two account statements) is caught by `inv.account_tax_treatment_matches_producing_source`, which recomputes the expected value from `ca_tax_st`/`tax_status_id` directly, or carries it forward from the account's immediately preceding statement (recomputed from source) where the producing action (CLOSEACCT) omits the field, and compares with `IS DISTINCT FROM`.

The other two invariants added this cycle, `inv.customer_tier_matches_producing_source` and `inv.account_owner_matches_producing_source`, were not required to close a specific unprotected mutation from cycle 1 (tier-null and owner-null were already protected by `inv.customer_statement_has_content` / `inv.account_asof_carries_customer_asof`), but they now also cover the corresponding swap/value-correctness case for tier and owner, closing the same class of gap the L2 review identified (a projected value that is well-formed but wrong, not merely missing).

All nine previously-hit audits remain unaffected; no invariant lost coverage.
