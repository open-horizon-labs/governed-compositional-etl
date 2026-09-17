-- inv.account_position_is_sum_of_changes: each logical.account_position row's
-- net_quantity equals the sum of quantity_change over every logical.holding_change
-- row sharing its (account_number, account_effective_from) key; every such key
-- among holding_change rows has exactly one account_position row. Two
-- checks, unioned:
--   1. sum mismatch or a key present on only one side (holding changes with
--      no position row, or a position row with no holding changes) -- a full
--      outer join between the recomputed grouped sum and the persisted table,
--      compared null-safely.
--   2. the cardinality half the invariant states directly: a key with more
--      than one governed.account_position row is itself a violation,
--      independent of whether either row's net_quantity happens to match.
-- Zero rows means the invariant holds.

WITH recomputed AS (
    SELECT
        owning_account_number AS account_number,
        owning_account_effective_from AS account_effective_from,
        SUM(quantity_change) AS net_quantity
    FROM governed.holding_change
    GROUP BY owning_account_number, owning_account_effective_from
),
sum_mismatch_or_missing AS (
    SELECT
        COALESCE(r.account_number, ap.account_number) AS account_number,
        COALESCE(r.account_effective_from, ap.account_effective_from) AS account_effective_from
    FROM recomputed AS r
    FULL OUTER JOIN governed.account_position AS ap
      ON ap.account_number IS NOT DISTINCT FROM r.account_number
     AND ap.account_effective_from IS NOT DISTINCT FROM r.account_effective_from
    WHERE r.account_number IS NULL
       OR ap.account_number IS NULL
       OR r.net_quantity IS DISTINCT FROM ap.net_quantity
),
duplicated_position_rows AS (
    SELECT account_number, account_effective_from
    FROM governed.account_position
    GROUP BY account_number, account_effective_from
    HAVING COUNT(*) > 1
)
SELECT * FROM sum_mismatch_or_missing
UNION
SELECT * FROM duplicated_position_rows;
