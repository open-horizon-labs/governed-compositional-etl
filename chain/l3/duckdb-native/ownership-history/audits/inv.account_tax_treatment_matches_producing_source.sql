-- inv.account_tax_treatment_matches_producing_source: for every
-- candidate-sourced account statement whose producing row carries a
-- tax-treatment value directly (a historical action's ca_tax_st on NEW,
-- ADDACCT, or UPDACCT, or a constructed scenario row's tax_status_id),
-- tax_treatment equals that value; for one whose producing historical action
-- omits it (CLOSEACCT), tax_treatment equals the value carried by the
-- account's immediately preceding statement, per L1.omitted-facts-stand.
--
-- Expected tax_treatment is recomputed independently from
-- raw.customer_mgmt_action and ce.account_changes (the two producing sources)
-- with its own carry-forward over the combined, effective_from-ordered
-- producing rows, joined to governed.account on (account_number,
-- effective_from) = (ca_id, action_ts) for historical rows and (account_id,
-- action_at) for ce rows; it is never read back from
-- governed.account.tax_treatment. Zero rows means the invariant holds.

WITH historical AS (
    SELECT
        ca_id AS account_number,
        action_ts AS effective_from,
        ca_tax_st AS tax_direct
    FROM raw.customer_mgmt_action
    WHERE action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
),
constructed AS (
    SELECT
        account_id AS account_number,
        action_at AS effective_from,
        tax_status_id AS tax_direct
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
            tax_direct,
            LAST_VALUE(tax_direct IGNORE NULLS) OVER (
                PARTITION BY account_number ORDER BY effective_from
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS expected_tax_treatment
    FROM combined
)
SELECT a.account_number, a.effective_from
FROM governed.account a
JOIN expected e
    ON e.account_number = a.account_number
   AND e.effective_from = a.effective_from
WHERE a.tax_treatment IS DISTINCT FROM e.expected_tax_treatment;
