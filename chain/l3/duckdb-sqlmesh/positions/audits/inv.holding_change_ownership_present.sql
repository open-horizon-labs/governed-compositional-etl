AUDIT (name "inv.holding_change_ownership_present");

-- Every persisted logical.holding_change row carries owning_account_number,
-- owning_account_effective_from, owning_customer_number, and owning_customer_effective_from
-- non-null.
SELECT
  m.original_trade_number,
  m.current_trade_number
FROM @this_model AS m
WHERE m.owning_account_number IS NULL
   OR m.owning_account_effective_from IS NULL
   OR m.owning_customer_number IS NULL
   OR m.owning_customer_effective_from IS NULL;
