AUDIT (name "inv.customer_position_not_negative");

-- net_quantity, the sum of quantity_change across every holding_change whose owning_customer_number
-- and owning_customer_effective_from equal this row's customer_number and customer_effective_from,
-- is never negative.
SELECT
  m.customer_number,
  m.customer_effective_from
FROM @this_model AS m
WHERE m.net_quantity < 0;
