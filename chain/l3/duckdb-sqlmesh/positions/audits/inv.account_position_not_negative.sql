AUDIT (name "inv.account_position_not_negative");

-- net_quantity, the sum of quantity_change across every holding_change whose owning_account_number
-- and owning_account_effective_from equal this row's account_number and account_effective_from,
-- is never negative.
SELECT
  m.account_number,
  m.account_effective_from
FROM @this_model AS m
WHERE m.net_quantity < 0;
