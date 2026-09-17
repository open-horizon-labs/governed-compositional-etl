AUDIT (name "inv.account_position_is_sum_of_changes");

-- Each logical.account_position row's net_quantity equals the sum of quantity_change over every
-- logical.holding_change row sharing its (account_number, account_effective_from) key; every
-- such key present among holding_change rows has exactly one account_position row, and vice
-- versa.
WITH recomputed AS (
  SELECT
    owning_account_number AS account_number,
    owning_account_effective_from AS account_effective_from,
    SUM(quantity_change) AS net_quantity
  FROM governed.holding_change
  GROUP BY owning_account_number, owning_account_effective_from
)
SELECT
  COALESCE(m.account_number, r.account_number) AS account_number,
  COALESCE(m.account_effective_from, r.account_effective_from) AS account_effective_from
FROM @this_model AS m
FULL OUTER JOIN recomputed AS r
  ON r.account_number = m.account_number
 AND r.account_effective_from = m.account_effective_from
WHERE m.account_number IS NULL
   OR r.account_number IS NULL
   OR m.net_quantity IS DISTINCT FROM r.net_quantity;
