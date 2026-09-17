AUDIT (name "inv.trade_order_type_frozen");

-- For any trade_number, order_type equals t_tt_id on every anchored raw.trade_cdc report of
-- the trade (cdc_flag, t_st_id, and t_tt_id all anchored; an unanchored report is held as a
-- whole and is not evidence), and is never replaced by a later report's t_tt_id. order_type is
-- in neither the outcome set (status, executed price, fees, commission, tax, quantity)
-- L1.lifecycle-mutates-outcome names nor the ownership set a later report leaves untouched, so
-- nothing a later anchored report does moves it.
SELECT
  m.trade_number
FROM @this_model AS m
JOIN raw.trade_cdc AS r ON r.t_id = m.trade_number
WHERE r.cdc_flag IS NOT NULL AND r.cdc_flag IN ('I', 'U', 'D')
  AND r.t_st_id IS NOT NULL AND r.t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  AND r.t_tt_id IS NOT NULL AND r.t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  AND r.t_tt_id IS DISTINCT FROM m.order_type;
