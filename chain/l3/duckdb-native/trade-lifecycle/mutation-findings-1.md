# Audit sensitivity findings (mutation testing), trade-lifecycle on duckdb-native

Protected: placed_at swap, owning_account_effective_from null, owning_customer_number null, first_seen_late swap.
Unprotected: owning_account_number null, placed_at null, first_seen_late null. inv.trade_owning_account_frozen and inv.trade_placement_reference_frozen compare projected values to a recomputation and do not treat a null as a difference. Routed to the next authorized change: audits must use IS DISTINCT FROM (or the model's invariants must state non-nullness explicitly so the L3 audit covers it).
