-- inv.holding_quantities_present: on every persisted logical.holding_change
-- row, before_qty, after_qty, and quantity_change are all non-null. Zero rows
-- means the invariant holds.

SELECT
    original_trade_number,
    current_trade_number
FROM governed.holding_change
WHERE before_qty IS NULL
   OR after_qty IS NULL
   OR quantity_change IS NULL;
