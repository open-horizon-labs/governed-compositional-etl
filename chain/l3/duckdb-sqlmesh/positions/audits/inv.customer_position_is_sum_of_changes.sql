AUDIT (name "inv.customer_position_is_sum_of_changes");

-- Each logical.customer_position row's net_quantity equals the sum of quantity_change over every
-- logical.holding_change row sharing its (customer_number, customer_effective_from) key; every
-- such key present among holding_change rows has exactly one customer_position row -- neither
-- zero (checked by the outer join below) nor more than one (checked by the row count).
WITH recomputed AS (
  SELECT
    owning_customer_number AS customer_number,
    owning_customer_effective_from AS customer_effective_from,
    SUM(quantity_change) AS net_quantity
  FROM governed.holding_change
  GROUP BY owning_customer_number, owning_customer_effective_from
),
model_with_count AS (
  SELECT
    m.*,
    COUNT(*) OVER (PARTITION BY m.customer_number, m.customer_effective_from) AS row_count
  FROM @this_model AS m
)
SELECT
  COALESCE(m.customer_number, r.customer_number) AS customer_number,
  COALESCE(m.customer_effective_from, r.customer_effective_from) AS customer_effective_from
FROM model_with_count AS m
FULL OUTER JOIN recomputed AS r
  ON r.customer_number IS NOT DISTINCT FROM m.customer_number
 AND r.customer_effective_from IS NOT DISTINCT FROM m.customer_effective_from
WHERE m.customer_number IS NULL
   OR r.customer_number IS NULL
   OR m.net_quantity IS DISTINCT FROM r.net_quantity
   OR m.row_count > 1;
