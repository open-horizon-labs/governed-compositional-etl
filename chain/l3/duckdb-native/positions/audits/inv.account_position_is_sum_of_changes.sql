-- inv.account_position_is_sum_of_changes: each logical.account_position row's
-- net_quantity equals the sum of quantity_change over every logical.holding_change
-- row sharing its (account_number, account_effective_from) key; every such key
-- among holding_change rows has exactly one account_position row. Checked by
-- recomputing the grouped sum directly from governed.holding_change and
-- comparing, null-safely, against governed.account_position via a full outer
-- join: a key present on only one side (holding changes with no position row,
-- or a position row with no holding changes) surfaces the same way a sum
-- mismatch does. Zero rows means the invariant holds.

WITH recomputed AS (
    SELECT
        owning_account_number AS account_number,
        owning_account_effective_from AS account_effective_from,
        SUM(quantity_change) AS net_quantity
    FROM governed.holding_change
    GROUP BY owning_account_number, owning_account_effective_from
)
SELECT
    COALESCE(r.account_number, ap.account_number) AS account_number,
    COALESCE(r.account_effective_from, ap.account_effective_from) AS account_effective_from,
    r.net_quantity AS recomputed_net_quantity,
    ap.net_quantity AS persisted_net_quantity
FROM recomputed AS r
FULL OUTER JOIN governed.account_position AS ap
  ON ap.account_number IS NOT DISTINCT FROM r.account_number
 AND ap.account_effective_from IS NOT DISTINCT FROM r.account_effective_from
WHERE r.account_number IS NULL
   OR ap.account_number IS NULL
   OR r.net_quantity IS DISTINCT FROM ap.net_quantity;
