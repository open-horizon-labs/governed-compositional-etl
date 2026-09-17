AUDIT (name "inv.trade_outcome_updates_in_place");

-- For any trade_number, a later raw.trade_cdc report of that same trade with cdc_flag I or U,
-- and with every one of its coded fields (cdc_flag, t_st_id, t_tt_id) anchored, replaces
-- status, executed_price, fees, commission, tax, and quantity with its newly reported values on
-- the same row; the trade_number itself is never replaced. A cdc_flag D report is not a later
-- report under this invariant. A report held under L1.unknown-codes -- any one of its coded
-- fields unanchored -- is likewise not a later report: it is held as a whole, supplies no
-- fact, and does not update the outcome; the hold is reported by inv.unknown_codes_held instead.
WITH latest_change AS (
  SELECT
    t_id AS trade_number,
    t_st_id AS status,
    t_trade_price AS executed_price,
    t_chrg AS fees,
    t_comm AS commission,
    t_tax AS tax,
    t_qty AS quantity
  FROM raw.trade_cdc
  WHERE cdc_flag IN ('I', 'U')
    AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date DESC, cdc_dsn DESC) = 1
)
SELECT
  m.trade_number
FROM @this_model AS m
JOIN latest_change AS l ON l.trade_number = m.trade_number
WHERE m.status IS DISTINCT FROM l.status
   OR m.executed_price IS DISTINCT FROM l.executed_price
   OR m.fees IS DISTINCT FROM l.fees
   OR m.commission IS DISTINCT FROM l.commission
   OR m.tax IS DISTINCT FROM l.tax
   OR m.quantity IS DISTINCT FROM l.quantity;
