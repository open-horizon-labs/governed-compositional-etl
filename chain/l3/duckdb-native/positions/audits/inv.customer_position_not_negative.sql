-- inv.customer_position_not_negative: net_quantity, the sum of quantity_change
-- across every holding_change whose owning_customer_number and
-- owning_customer_effective_from equal this row's customer_number and
-- customer_effective_from, is never negative. A null net_quantity is treated
-- as a violation rather than silently passing an inequality test. Zero rows
-- means the invariant holds.

SELECT
    customer_number,
    customer_effective_from,
    net_quantity
FROM governed.customer_position
WHERE net_quantity < 0
   OR net_quantity IS NULL;
