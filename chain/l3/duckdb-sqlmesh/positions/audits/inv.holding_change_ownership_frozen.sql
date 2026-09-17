AUDIT (name "inv.holding_change_ownership_frozen");

-- For any (original_trade_number, current_trade_number) pair, the frozen ownership copied at
-- first encounter (owning_account_number, owning_account_effective_from, owning_customer_number,
-- owning_customer_effective_from) still agrees with trade-lifecycle's own frozen reference for
-- this pair's current_trade_number. The governed_merge materialization writes these four columns
-- only on insert, so a difference here means the copy no longer matches its source.
SELECT
  m.original_trade_number,
  m.current_trade_number
FROM @this_model AS m
JOIN governed.trade AS t ON t.trade_number = m.current_trade_number
WHERE t.owning_account_number IS DISTINCT FROM m.owning_account_number
   OR t.owning_account_effective_from IS DISTINCT FROM m.owning_account_effective_from
   OR t.owning_customer_number IS DISTINCT FROM m.owning_customer_number
   OR t.owning_customer_effective_from IS DISTINCT FROM m.owning_customer_effective_from;
