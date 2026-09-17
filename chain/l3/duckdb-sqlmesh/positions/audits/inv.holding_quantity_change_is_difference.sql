AUDIT (name "inv.holding_quantity_change_is_difference");

-- On every logical.holding_change row, quantity_change equals after_qty minus before_qty.
SELECT
  m.original_trade_number,
  m.current_trade_number
FROM @this_model AS m
WHERE m.quantity_change IS DISTINCT FROM (m.after_qty - m.before_qty);
