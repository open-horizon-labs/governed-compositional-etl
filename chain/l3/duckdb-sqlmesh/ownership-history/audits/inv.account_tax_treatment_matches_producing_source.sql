AUDIT (name "inv.account_tax_treatment_matches_producing_source");

-- For every candidate-sourced account statement whose producing row carries a
-- tax-treatment value directly (a historical action's ca_tax_st on NEW, ADDACCT, or
-- UPDACCT, or a constructed scenario row's tax_status_id), tax_treatment equals that
-- value; for one whose producing historical action omits it (CLOSEACCT), tax_treatment
-- equals the value carried by the account's immediately preceding statement. Both the
-- direct value and the carried-forward value are recomputed here from
-- raw.customer_mgmt_action and ce.account_changes directly, never read back from the
-- tax_treatment column being checked.
WITH source_rows AS (
  SELECT
    ca_id AS account_number,
    action_ts AS effective_from,
    CASE WHEN action_type IN ('NEW', 'ADDACCT', 'UPDACCT') THEN ca_tax_st ELSE NULL END AS tax_treatment_as_reported
  FROM raw.customer_mgmt_action
  WHERE action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
  UNION ALL
  SELECT
    account_id AS account_number,
    action_at AS effective_from,
    tax_status_id AS tax_treatment_as_reported
  FROM ce.account_changes
),
expected AS (
  SELECT
    account_number,
    effective_from,
    LAST_VALUE(tax_treatment_as_reported IGNORE NULLS) OVER (
      PARTITION BY account_number
      ORDER BY effective_from
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS expected_tax_treatment
  FROM source_rows
)
SELECT
  m.account_number,
  m.effective_from,
  m.tax_treatment
FROM @this_model AS m
JOIN expected AS e
  ON e.account_number = m.account_number
  AND e.effective_from = m.effective_from
WHERE m.tax_treatment IS DISTINCT FROM e.expected_tax_treatment;
