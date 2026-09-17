# Audit sensitivity findings, ownership-history on duckdb-sqlmesh

18 mutations, 3 unprotected: customer status swap, account status swap, account tax-treatment swap. Same as duckdb-native. Routed to ownership-history L2 cycle 10 (value-correctness invariants), after which both targets add the corresponding audits.
