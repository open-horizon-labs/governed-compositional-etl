AUDIT (name "inv.account_position_is_sum_of_changes");

-- Each logical.account_position row's net_quantity equals the sum of quantity_change over every
-- logical.holding_change row sharing its (account_number, account_effective_from) key; every
-- such key present among holding_change rows has exactly one account_position row -- neither
-- zero (checked by the outer join below) nor more than one (checked by the row count).
WITH recomputed AS (
  SELECT
    owning_account_number AS account_number,
    owning_account_effective_from AS account_effective_from,
    SUM(quantity_change) AS net_quantity
  FROM governed.holding_change
  GROUP BY owning_account_number, owning_account_effective_from
),
model_with_count AS (
  SELECT
    m.*,
    COUNT(*) OVER (PARTITION BY m.account_number, m.account_effective_from) AS row_count
  FROM @this_model AS m
)
SELECT
  COALESCE(m.account_number, r.account_number) AS account_number,
  COALESCE(m.account_effective_from, r.account_effective_from) AS account_effective_from
FROM model_with_count AS m
FULL OUTER JOIN recomputed AS r
  ON r.account_number IS NOT DISTINCT FROM m.account_number
 AND r.account_effective_from IS NOT DISTINCT FROM m.account_effective_from
WHERE m.account_number IS NULL
   OR r.account_number IS NULL
   OR m.net_quantity IS DISTINCT FROM r.net_quantity
   OR m.row_count > 1;
