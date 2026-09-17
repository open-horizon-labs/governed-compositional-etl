AUDIT (name "inv.account_position_not_negative");

-- net_quantity, the sum of quantity_change across every holding_change whose owning_account_number
-- and owning_account_effective_from equal this row's account_number and account_effective_from,
-- is never negative. net_quantity is nullable: false (type.holding_quantity_change); a null sum
-- is also a violation, not a silent pass.
SELECT
  m.account_number,
  m.account_effective_from
FROM @this_model AS m
WHERE m.net_quantity < 0
   OR m.net_quantity IS NULL;
