-- inv.constructed_scenarios_labeled: every account statement whose source is
-- a labeled constructed scenario (ce.account_changes) carries a non-null
-- provenance value; no account statement sourced from received records
-- (raw.customer_mgmt_action) carries a provenance value. Zero rows means the
-- invariant holds.

SELECT a.account_number, a.effective_from
FROM governed.account a
LEFT JOIN ce.account_changes cc
    ON cc.account_id = a.account_number AND cc.action_at = a.effective_from
LEFT JOIN raw.customer_mgmt_action r
    ON r.ca_id = a.account_number
   AND r.action_ts = a.effective_from
   AND r.action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
WHERE (cc.account_id IS NOT NULL AND (a.provenance IS NULL OR a.provenance = ''))
   OR (r.ca_id IS NOT NULL AND a.provenance IS NOT NULL);
