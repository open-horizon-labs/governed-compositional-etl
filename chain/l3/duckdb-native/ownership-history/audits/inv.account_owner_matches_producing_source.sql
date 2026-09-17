-- inv.account_owner_matches_producing_source: for every candidate-sourced
-- account statement whose producing historical action carries c_id,
-- owning_customer_number equals that action's c_id; for one produced by a
-- constructed scenario row, which carries no owner field, owning_customer_number
-- equals the value carried by the account's immediately preceding statement,
-- per L1.omitted-facts-stand.
--
-- Expected owner is recomputed independently from raw.customer_mgmt_action and
-- ce.account_changes (the two producing sources) with its own carry-forward
-- over the combined, effective_from-ordered producing rows, joined to
-- governed.account on (account_number, effective_from) = (ca_id, action_ts)
-- for historical rows and (account_id, action_at) for ce rows; it is never
-- read back from governed.account.owning_customer_number. Zero rows means the
-- invariant holds.

WITH historical AS (
    SELECT
        ca_id AS account_number,
        action_ts AS effective_from,
        c_id AS owner_direct
    FROM raw.customer_mgmt_action
    WHERE action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
),
constructed AS (
    SELECT
        account_id AS account_number,
        action_at AS effective_from,
        CAST(NULL AS BIGINT) AS owner_direct
    FROM ce.account_changes
),
combined AS (
    SELECT * FROM historical
    UNION ALL
    SELECT * FROM constructed
),
expected AS (
    SELECT
        account_number,
        effective_from,
        COALESCE(
            owner_direct,
            LAST_VALUE(owner_direct IGNORE NULLS) OVER (
                PARTITION BY account_number ORDER BY effective_from
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS expected_owner
    FROM combined
)
SELECT a.account_number, a.effective_from
FROM governed.account a
JOIN expected e
    ON e.account_number = a.account_number
   AND e.effective_from = a.effective_from
WHERE a.owning_customer_number IS DISTINCT FROM e.expected_owner;
