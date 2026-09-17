-- inv.constructed_account_change_refers_to_known_account: every account
-- statement sourced from the labeled constructed scenario ce.account_changes
-- names an account_number that already has an earlier statement sourced from
-- a received record (raw.customer_mgmt_action). Zero rows means the invariant
-- holds.

SELECT cc.account_id, cc.action_at
FROM ce.account_changes cc
WHERE NOT EXISTS (
    SELECT 1
    FROM raw.customer_mgmt_action r
    WHERE r.ca_id = cc.account_id
      AND r.action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
      AND r.action_ts < cc.action_at
);
