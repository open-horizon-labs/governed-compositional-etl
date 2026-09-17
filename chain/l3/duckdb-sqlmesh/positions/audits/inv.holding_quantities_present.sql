AUDIT (name "inv.holding_quantities_present");

-- On every persisted logical.holding_change row, before_qty, after_qty, and quantity_change are
-- all non-null.
SELECT
  m.original_trade_number,
  m.current_trade_number
FROM @this_model AS m
WHERE m.before_qty IS NULL
   OR m.after_qty IS NULL
   OR m.quantity_change IS NULL;
