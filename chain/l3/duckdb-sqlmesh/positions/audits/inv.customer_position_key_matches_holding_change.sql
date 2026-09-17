AUDIT (name "inv.customer_position_key_matches_holding_change");

-- customer_number and customer_effective_from equal the owning_customer_number and
-- owning_customer_effective_from shared by every logical.holding_change row grouped into this
-- row: every distinct (owning_customer_number, owning_customer_effective_from) pair present in
-- governed.holding_change has exactly one matching customer_position row, and vice versa.
WITH holding_keys AS (
  SELECT DISTINCT
    owning_customer_number AS customer_number,
    owning_customer_effective_from AS customer_effective_from
  FROM governed.holding_change
)
SELECT
  COALESCE(m.customer_number, hk.customer_number) AS customer_number,
  COALESCE(m.customer_effective_from, hk.customer_effective_from) AS customer_effective_from
FROM @this_model AS m
FULL OUTER JOIN holding_keys AS hk
  ON hk.customer_number = m.customer_number
 AND hk.customer_effective_from = m.customer_effective_from
WHERE m.customer_number IS NULL OR hk.customer_number IS NULL;
