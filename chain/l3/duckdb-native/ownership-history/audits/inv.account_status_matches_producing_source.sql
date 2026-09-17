-- inv.account_status_matches_producing_source: for every candidate-sourced
-- account statement produced by a historical action, status equals the
-- interpreted meaning of that action's action_type (NEW, ADDACCT, UPDACCT:
-- open; CLOSEACCT: closed); for one produced by a labeled constructed
-- scenario row, status equals that row's own status_id. sources-v1.json's
-- action_type_meanings state a status only for CLOSEACCT (the row reports
-- the closing of an account) and, by wording, ADDACCT (the row reports an
-- additional account opened); open for NEW and UPDACCT is not stated there
-- but is the reading recorded in this invariant's parallel_assumption.
--
-- Expected status is recomputed from raw.customer_mgmt_action and
-- ce.account_changes (the two producing sources), joined to governed.account
-- on (account_number, effective_from) = (ca_id, action_ts) for historical rows
-- and (account_id, action_at) for ce rows; it is never read back from
-- governed.account.status. Zero rows means the invariant holds.

WITH expected AS (
    SELECT
        ca_id AS account_number,
        action_ts AS effective_from,
        CASE action_type
            WHEN 'NEW'       THEN 'ACTV'
            WHEN 'ADDACCT'   THEN 'ACTV'
            WHEN 'UPDACCT'   THEN 'ACTV'
            WHEN 'CLOSEACCT' THEN 'INAC'
        END AS expected_status
    FROM raw.customer_mgmt_action
    WHERE action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
    UNION ALL
    SELECT
        account_id AS account_number,
        action_at AS effective_from,
        status_id AS expected_status
    FROM ce.account_changes
)
SELECT a.account_number, a.effective_from
FROM governed.account a
JOIN expected e
    ON e.account_number = a.account_number
   AND e.effective_from = a.effective_from
WHERE a.status IS DISTINCT FROM e.expected_status;
