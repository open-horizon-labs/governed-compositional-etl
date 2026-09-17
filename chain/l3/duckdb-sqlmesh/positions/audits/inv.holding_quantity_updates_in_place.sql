AUDIT (name "inv.holding_quantity_updates_in_place");

-- For any (original_trade_number, current_trade_number) pair, a later raw.holding_history
-- report of that same pair with cdc_flag I or U replaces before_qty and after_qty with its
-- newly reported values on the same row; the pair itself is never replaced. A cdc_flag D report
-- is not a later report under this invariant. Historical rows carry no cdc columns of their own
-- (cdc_flag and cdc_dsn both NULL) and precede all incremental rows regardless of batch_date,
-- per sources-v1.json's report_order.applies_to; unlike raw.trade_cdc, they are not synthesized
-- to cdc_flag 'I' and must not be filtered out by a cdc_flag IN ('I', 'U') test.
WITH latest_change AS (
  SELECT
    hh_h_t_id AS original_trade_number,
    hh_t_id AS current_trade_number,
    hh_before_qty AS before_qty,
    hh_after_qty AS after_qty
  FROM raw.holding_history
  WHERE cdc_flag IS NULL OR cdc_flag IN ('I', 'U')
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY hh_h_t_id, hh_t_id
    ORDER BY (cdc_flag IS NOT NULL) DESC, batch_date DESC, cdc_dsn DESC
  ) = 1
)
SELECT
  m.original_trade_number,
  m.current_trade_number
FROM @this_model AS m
JOIN latest_change AS l
  ON l.original_trade_number = m.original_trade_number
 AND l.current_trade_number = m.current_trade_number
WHERE m.before_qty IS DISTINCT FROM l.before_qty
   OR m.after_qty IS DISTINCT FROM l.after_qty;
