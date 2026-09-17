AUDIT (name "inv.customer_tier_matches_producing_source");

-- For every candidate-sourced customer statement whose producing action carries c_tier
-- (NEW, UPDCUST), tier equals that row's c_tier; for one whose producing action omits it
-- (INACT), tier equals the value carried by the customer's immediately preceding
-- statement. Both the producing row and its immediately preceding tier-bearing row are
-- recomputed here from raw.customer_mgmt_action directly, never read back from the tier
-- column being checked.
WITH producing AS (
  SELECT
    c_id,
    action_ts,
    CASE WHEN action_type IN ('NEW', 'UPDCUST') THEN c_tier ELSE NULL END AS tier_as_reported
  FROM raw.customer_mgmt_action
  WHERE action_type IN ('NEW', 'UPDCUST', 'INACT')
),
expected AS (
  SELECT
    c_id,
    action_ts,
    LAST_VALUE(tier_as_reported IGNORE NULLS) OVER (
      PARTITION BY c_id
      ORDER BY action_ts
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS expected_tier
  FROM producing
)
SELECT
  m.customer_number,
  m.effective_from,
  m.tier
FROM @this_model AS m
JOIN expected AS e
  ON e.c_id = m.customer_number
  AND e.action_ts = m.effective_from
WHERE m.tier IS DISTINCT FROM e.expected_tier;
