AUDIT (name "inv.account_status_matches_producing_source");

-- For every candidate-sourced account statement produced by a historical action, status
-- equals the anchored meaning of that action's action_type (NEW, ADDACCT, UPDACCT: open;
-- CLOSEACCT: closed); for one produced by a labeled constructed scenario row, status
-- equals that row's own status_id, used unwrapped so a status_id outside {ACTV, INAC} is
-- also a violation rather than a silently-matching NULL. Of the historical codes,
-- sources-v1.json's action_type_meanings states a status only for CLOSEACCT ("the closing
-- of an account") and, by wording, ADDACCT ("opened"); open for NEW and UPDACCT is the
-- reading recorded in this invariant's own parallel_assumption, not a status
-- sources-v1.json itself states, so this audit is exactly as strong as that assumption.
-- Each producing row is found by joining back to the entity's declared sources on
-- (account_number, effective_from) = (ca_id, action_ts) or (account_id, action_at); the
-- expected value is recomputed from that row, never read back from the status column
-- being checked.
WITH from_actions AS (
  SELECT
    m.account_number,
    m.effective_from,
    m.status,
    CASE a.action_type
      WHEN 'NEW' THEN 'ACTV'
      WHEN 'ADDACCT' THEN 'ACTV'
      WHEN 'UPDACCT' THEN 'ACTV'
      WHEN 'CLOSEACCT' THEN 'INAC'
    END AS expected_status
  FROM @this_model AS m
  JOIN raw.customer_mgmt_action AS a
    ON a.ca_id = m.account_number
    AND a.action_ts = m.effective_from
    AND a.action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
),
from_constructed AS (
  SELECT
    m.account_number,
    m.effective_from,
    m.status,
    c.status_id AS expected_status
  FROM @this_model AS m
  JOIN ce.account_changes AS c
    ON c.account_id = m.account_number
    AND c.action_at = m.effective_from
)
SELECT account_number, effective_from, status
FROM from_actions
WHERE status IS DISTINCT FROM expected_status
UNION ALL
SELECT account_number, effective_from, status
FROM from_constructed
WHERE status IS DISTINCT FROM expected_status;
