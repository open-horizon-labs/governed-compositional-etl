-- inv.holding_change_current_trade_known: every raw.holding_history report
-- whose cdc_flag is not D names an hh_t_id that resolves to a logical.trade
-- row in trade-lifecycle's model (governed.trade on this target). Batch1
-- historical rows carry a null cdc_flag and are in scope for this check --
-- `cdc_flag <> 'D'` would silently drop them (NULL <> 'D' is NULL, not true),
-- so this uses `cdc_flag IS DISTINCT FROM 'D'` instead. Distinguishes the
-- unknown-trade case from an unresolved ownership pin
-- (inv.holding_change_ownership_present): a report whose hh_t_id has no
-- governed.trade row at all fires here, rather than silently dropping out of
-- logical.holding_change the way an unresolved pin does. Zero rows means the
-- invariant holds.

SELECT DISTINCT
    hh.hh_h_t_id AS original_trade_number,
    hh.hh_t_id AS current_trade_number
FROM raw.holding_history AS hh
LEFT JOIN governed.trade AS t
  ON t.trade_number = hh.hh_t_id
WHERE hh.cdc_flag IS DISTINCT FROM 'D'
  AND t.trade_number IS NULL;
