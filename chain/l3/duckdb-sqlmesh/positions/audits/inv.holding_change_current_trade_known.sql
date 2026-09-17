AUDIT (name "inv.holding_change_current_trade_known");

-- Every raw.holding_history report whose cdc_flag is not D names an hh_t_id that resolves to a
-- logical.trade row in trade-lifecycle's model. cdc_flag IS DISTINCT FROM 'D' (not <> 'D') keeps
-- historical rows -- cdc_flag NULL -- in scope; <> 'D' would silently drop them, since NULL <>
-- 'D' is NULL, not true.
SELECT DISTINCT
  h.hh_h_t_id AS original_trade_number,
  h.hh_t_id AS current_trade_number
FROM raw.holding_history AS h
LEFT JOIN governed.trade AS t ON t.trade_number = h.hh_t_id
WHERE h.cdc_flag IS DISTINCT FROM 'D'
  AND t.trade_number IS NULL;
