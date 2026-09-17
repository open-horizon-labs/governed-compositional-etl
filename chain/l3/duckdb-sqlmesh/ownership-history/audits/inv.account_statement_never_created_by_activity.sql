AUDIT (name "inv.account_statement_never_created_by_activity");

-- L1.closed-account-activity: activity never reopens an account, because no trade creates a
-- statement. Every logical.account statement is produced by an anchored account-subject
-- customer_mgmt_action row (NEW, ADDACCT, UPDACCT, CLOSEACCT) or a labeled constructed scenario
-- row (ce.account_changes); this job reads no trade or holding-history source at all, so this
-- audit is the direct check that every persisted statement traces to one of those two producers
-- and to nothing else -- in particular, never to a trade report.
SELECT
  m.account_number,
  m.effective_from
FROM @this_model AS m
LEFT JOIN raw.customer_mgmt_action AS a
  ON a.ca_id = m.account_number
 AND a.action_ts = m.effective_from
 AND a.action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
LEFT JOIN ce.account_changes AS c
  ON c.account_id = m.account_number
 AND c.action_at = m.effective_from
WHERE a.ca_id IS NULL
  AND c.account_id IS NULL;
