-- inv.customer_position_is_sum_of_changes: each logical.customer_position
-- row's net_quantity equals the sum of quantity_change over every
-- logical.holding_change row sharing its (customer_number, customer_effective_from)
-- key; every such key among holding_change rows has exactly one
-- customer_position row. Checked by recomputing the grouped sum directly from
-- governed.holding_change and comparing, null-safely, against
-- governed.customer_position via a full outer join: a key present on only one
-- side (holding changes with no position row, or a position row with no
-- holding changes) surfaces the same way a sum mismatch does. Zero rows means
-- the invariant holds.

WITH recomputed AS (
    SELECT
        owning_customer_number AS customer_number,
        owning_customer_effective_from AS customer_effective_from,
        SUM(quantity_change) AS net_quantity
    FROM governed.holding_change
    GROUP BY owning_customer_number, owning_customer_effective_from
)
SELECT
    COALESCE(r.customer_number, cp.customer_number) AS customer_number,
    COALESCE(r.customer_effective_from, cp.customer_effective_from) AS customer_effective_from,
    r.net_quantity AS recomputed_net_quantity,
    cp.net_quantity AS persisted_net_quantity
FROM recomputed AS r
FULL OUTER JOIN governed.customer_position AS cp
  ON cp.customer_number IS NOT DISTINCT FROM r.customer_number
 AND cp.customer_effective_from IS NOT DISTINCT FROM r.customer_effective_from
WHERE r.customer_number IS NULL
   OR cp.customer_number IS NULL
   OR r.net_quantity IS DISTINCT FROM cp.net_quantity;
