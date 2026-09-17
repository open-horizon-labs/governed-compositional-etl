AUDIT (name "inv.account_position_key_matches_holding_change");

-- account_number and account_effective_from equal the owning_account_number and
-- owning_account_effective_from shared by every logical.holding_change row grouped into this
-- row: every distinct (owning_account_number, owning_account_effective_from) pair present in
-- governed.holding_change has exactly one matching account_position row, and vice versa.
WITH holding_keys AS (
  SELECT DISTINCT
    owning_account_number AS account_number,
    owning_account_effective_from AS account_effective_from
  FROM governed.holding_change
)
SELECT
  COALESCE(m.account_number, hk.account_number) AS account_number,
  COALESCE(m.account_effective_from, hk.account_effective_from) AS account_effective_from
FROM @this_model AS m
FULL OUTER JOIN holding_keys AS hk
  ON hk.account_number = m.account_number
 AND hk.account_effective_from = m.account_effective_from
WHERE m.account_number IS NULL OR hk.account_number IS NULL;
