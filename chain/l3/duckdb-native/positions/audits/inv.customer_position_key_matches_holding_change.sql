-- inv.customer_position_key_matches_holding_change: customer_number and
-- customer_effective_from equal the owning_customer_number and
-- owning_customer_effective_from shared by every logical.holding_change row
-- grouped into this row. Checked by recomputing the distinct group keys
-- directly from governed.holding_change and comparing them, null-safely, to
-- governed.customer_position's own persisted keys via a full outer join; any
-- key present on only one side (including a side made unmatched by a null
-- key value) surfaces as a violation. Zero rows means the invariant holds.

WITH recomputed_keys AS (
    SELECT DISTINCT
        owning_customer_number AS customer_number,
        owning_customer_effective_from AS customer_effective_from
    FROM governed.holding_change
)
SELECT
    COALESCE(r.customer_number, cp.customer_number) AS customer_number,
    COALESCE(r.customer_effective_from, cp.customer_effective_from) AS customer_effective_from
FROM recomputed_keys AS r
FULL OUTER JOIN governed.customer_position AS cp
  ON cp.customer_number IS NOT DISTINCT FROM r.customer_number
 AND cp.customer_effective_from IS NOT DISTINCT FROM r.customer_effective_from
WHERE r.customer_number IS NULL
   OR cp.customer_number IS NULL;
