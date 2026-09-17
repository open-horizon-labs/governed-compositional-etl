# Audit sensitivity findings 2, ownership-history on duckdb-sqlmesh

18 mutations, 0 unprotected. The three mutations left unprotected in mutation-findings-1.md are now each caught by the value-correctness audit added for it in L3 cycle 3:

- customer status swap -> `inv.customer_status_matches_producing_source`
- account status swap -> `inv.account_status_matches_producing_source`
- account tax-treatment swap -> `inv.account_tax_treatment_matches_producing_source`

All other mutations remain caught by their existing audits (no regressions); full per-mutation detail in the `mutate` run's `results` array.
