-- inv.customer_tier_matches_producing_source: for every candidate-sourced
-- customer statement whose producing action carries c_tier (NEW, UPDCUST),
-- tier equals that row's c_tier; for one whose producing action omits it
-- (INACT), tier equals the value carried by the customer's immediately
-- preceding statement, per L1.omitted-facts-stand.
--
-- Expected tier is recomputed independently from raw.customer_mgmt_action
-- (the producing source) with its own carry-forward over the same
-- action-producing rows, joined to governed.customer on (customer_number,
-- effective_from) = (c_id, action_ts) for comparison; it is never read back
-- from governed.customer.tier. Zero rows means the invariant holds.

WITH producing AS (
    SELECT
        c_id AS customer_number,
        action_ts AS effective_from,
        c_tier AS tier_direct
    FROM raw.customer_mgmt_action
    WHERE action_type IN ('NEW', 'UPDCUST', 'INACT')
),
expected AS (
    SELECT
        customer_number,
        effective_from,
        COALESCE(
            tier_direct,
            LAST_VALUE(tier_direct IGNORE NULLS) OVER (
                PARTITION BY customer_number ORDER BY effective_from
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS expected_tier
    FROM producing
)
SELECT c.customer_number, c.effective_from
FROM governed.customer c
JOIN expected e
    ON e.customer_number = c.customer_number
   AND e.effective_from = c.effective_from
WHERE c.tier IS DISTINCT FROM e.expected_tier;
