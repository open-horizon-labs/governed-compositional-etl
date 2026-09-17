-- inv.account_statement_never_created_by_activity: every logical.account
-- statement is produced by an anchored raw.customer_mgmt_action row (NEW,
-- ADDACCT, UPDACCT, CLOSEACCT) or a labeled constructed ce.account_changes
-- row -- never by a trade report or a holding-history report. This job
-- reads only raw.customer_mgmt_action and ce.account_changes to produce
-- logical.account (it does not read raw.trade_cdc or raw.holding_history at
-- all), so this is the checkable form of L1.closed-account-activity's
-- "activity never reopens an account: no trade creates a statement" --
-- guarding against a future change silently introducing a third producer.
-- Checked by matching every governed.account statement's (account_number,
-- effective_from) key back to one of the two permitted producers; a
-- statement with no such match is a violation. Zero rows means the
-- invariant holds.

WITH permitted_producers AS (
    SELECT
        ca_id AS account_number,
        action_ts AS effective_from
    FROM raw.customer_mgmt_action
    WHERE action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
    UNION ALL
    SELECT
        account_id AS account_number,
        action_at AS effective_from
    FROM ce.account_changes
)
SELECT a.account_number, a.effective_from
FROM governed.account a
LEFT JOIN permitted_producers p
    ON p.account_number = a.account_number
   AND p.effective_from = a.effective_from
WHERE p.account_number IS NULL;
