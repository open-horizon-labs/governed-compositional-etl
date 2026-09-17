AUDIT (name "inv.trade_order_type_frozen");

-- For any trade_number, order_type equals t_tt_id on the trade's first-encountered
-- raw.trade_cdc report, and is never replaced by a later report's t_tt_id. order_type is in
-- neither the outcome set (status, executed price, fees, commission, tax, quantity) L1.lifecycle
-- -mutates-outcome names nor the ownership set a later report leaves untouched, so nothing a
-- later report does moves it; this recomputes it fresh from every raw.trade_cdc report of the
-- trade (unconditionally, regardless of that report's own cdc_flag or t_st_id) and diffs it
-- against what governed.trade actually holds.
SELECT
  m.trade_number
FROM @this_model AS m
JOIN raw.trade_cdc AS r ON r.t_id = m.trade_number
WHERE r.t_tt_id IS DISTINCT FROM m.order_type;
