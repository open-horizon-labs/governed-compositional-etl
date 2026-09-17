AUDIT (name "inv.customer_position_is_sum_of_changes");

-- Each logical.customer_position row's net_quantity equals the sum of quantity_change over every
-- logical.holding_change row sharing its (customer_number, customer_effective_from) key; every
-- such key present among holding_change rows has exactly one customer_position row, and vice
-- versa.
WITH recomputed AS (
  SELECT
    owning_customer_number AS customer_number,
    owning_customer_effective_from AS customer_effective_from,
    SUM(quantity_change) AS net_quantity
  FROM governed.holding_change
  GROUP BY owning_customer_number, owning_customer_effective_from
)
SELECT
  COALESCE(m.customer_number, r.customer_number) AS customer_number,
  COALESCE(m.customer_effective_from, r.customer_effective_from) AS customer_effective_from
FROM @this_model AS m
FULL OUTER JOIN recomputed AS r
  ON r.customer_number = m.customer_number
 AND r.customer_effective_from = m.customer_effective_from
WHERE m.customer_number IS NULL
   OR r.customer_number IS NULL
   OR m.net_quantity IS DISTINCT FROM r.net_quantity;
