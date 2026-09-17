AUDIT (name "inv.account_owner_matches_producing_source");

-- For every candidate-sourced account statement whose producing historical action carries
-- c_id, owning_customer_number equals that action's c_id; for one produced by a
-- constructed scenario row, which carries no owner field, owning_customer_number equals
-- the value carried by the account's immediately preceding statement. Both the direct
-- value and the carried-forward value are recomputed here from raw.customer_mgmt_action
-- and ce.account_changes directly, never read back from the owning_customer_number
-- column being checked.
WITH source_rows AS (
  SELECT
    ca_id AS account_number,
    action_ts AS effective_from,
    c_id AS owner_as_reported
  FROM raw.customer_mgmt_action
  WHERE action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
  UNION ALL
  SELECT
    account_id AS account_number,
    action_at AS effective_from,
    CAST(NULL AS BIGINT) AS owner_as_reported
  FROM ce.account_changes
),
expected AS (
  SELECT
    account_number,
    effective_from,
    LAST_VALUE(owner_as_reported IGNORE NULLS) OVER (
      PARTITION BY account_number
      ORDER BY effective_from
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS expected_owner
  FROM source_rows
)
SELECT
  m.account_number,
  m.effective_from,
  m.owning_customer_number
FROM @this_model AS m
JOIN expected AS e
  ON e.account_number = m.account_number
  AND e.effective_from = m.effective_from
WHERE m.owning_customer_number IS DISTINCT FROM e.expected_owner;
