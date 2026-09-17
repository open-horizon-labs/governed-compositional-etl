-- inv.customer_position_is_sum_of_changes: each logical.customer_position
-- row's net_quantity equals the sum of quantity_change over every
-- logical.holding_change row sharing its (customer_number, customer_effective_from)
-- key; every such key among holding_change rows has exactly one
-- customer_position row. Two checks, unioned:
--   1. sum mismatch or a key present on only one side (holding changes with
--      no position row, or a position row with no holding changes) -- a full
--      outer join between the recomputed grouped sum and the persisted table,
--      compared null-safely.
--   2. the cardinality half the invariant states directly: a key with more
--      than one governed.customer_position row is itself a violation,
--      independent of whether either row's net_quantity happens to match.
-- Zero rows means the invariant holds.

WITH recomputed AS (
    SELECT
        owning_customer_number AS customer_number,
        owning_customer_effective_from AS customer_effective_from,
        SUM(quantity_change) AS net_quantity
    FROM governed.holding_change
    GROUP BY owning_customer_number, owning_customer_effective_from
),
sum_mismatch_or_missing AS (
    SELECT
        COALESCE(r.customer_number, cp.customer_number) AS customer_number,
        COALESCE(r.customer_effective_from, cp.customer_effective_from) AS customer_effective_from
    FROM recomputed AS r
    FULL OUTER JOIN governed.customer_position AS cp
      ON cp.customer_number IS NOT DISTINCT FROM r.customer_number
     AND cp.customer_effective_from IS NOT DISTINCT FROM r.customer_effective_from
    WHERE r.customer_number IS NULL
       OR cp.customer_number IS NULL
       OR r.net_quantity IS DISTINCT FROM cp.net_quantity
),
duplicated_position_rows AS (
    SELECT customer_number, customer_effective_from
    FROM governed.customer_position
    GROUP BY customer_number, customer_effective_from
    HAVING COUNT(*) > 1
)
SELECT * FROM sum_mismatch_or_missing
UNION
SELECT * FROM duplicated_position_rows;
