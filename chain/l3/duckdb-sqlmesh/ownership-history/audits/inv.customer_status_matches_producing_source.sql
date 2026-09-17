AUDIT (name "inv.customer_status_matches_producing_source");

-- For every candidate-sourced customer statement produced by a historical action, status
-- equals the anchored meaning of that action's action_type (NEW, UPDCUST: active; INACT:
-- inactive). Of these, sources-v1.json's action_type_meanings states a status only for
-- INACT ("a customer becoming inactive"); active for NEW and UPDCUST is the reading
-- recorded in this invariant's own parallel_assumption, not a status sources-v1.json
-- itself states, so this audit is exactly as strong as that assumption. The producing row
-- is found by joining back to raw.customer_mgmt_action on (customer_number, effective_from)
-- = (c_id, action_ts), with no action_type filter: that identifier is enough to find the
-- row on correct data, and the exhaustive CASE below falls to NULL for any other code, so
-- a customer statement wrongly produced from an account-subject action becomes a
-- violation instead of a silently dropped row. The expected value is recomputed from that
-- row's action_type, never read back from the status column being checked.
SELECT
  m.customer_number,
  m.effective_from,
  m.status
FROM @this_model AS m
JOIN raw.customer_mgmt_action AS a
  ON a.c_id = m.customer_number
  AND a.action_ts = m.effective_from
WHERE m.status IS DISTINCT FROM (
  CASE a.action_type
    WHEN 'NEW' THEN 'ACTV'
    WHEN 'UPDCUST' THEN 'ACTV'
    WHEN 'INACT' THEN 'INAC'
  END
);
