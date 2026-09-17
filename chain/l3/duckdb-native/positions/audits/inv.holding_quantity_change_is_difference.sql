-- inv.holding_quantity_change_is_difference: on every logical.holding_change
-- row, quantity_change equals after_qty minus before_qty. Checked by
-- recomputing the difference from the row's own two persisted columns and
-- comparing with IS DISTINCT FROM. Zero rows means the invariant holds.

SELECT
    original_trade_number,
    current_trade_number
FROM governed.holding_change
WHERE quantity_change IS DISTINCT FROM (after_qty - before_qty);
