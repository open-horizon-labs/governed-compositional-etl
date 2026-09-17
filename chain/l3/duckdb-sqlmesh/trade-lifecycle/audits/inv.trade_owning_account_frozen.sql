AUDIT (name "inv.trade_owning_account_frozen");

-- For any trade_number, every anchored raw.trade_cdc report of that trade (cdc_flag, t_st_id,
-- and t_tt_id all anchored; L1.unknown-codes holds a report as a whole, so an unanchored report
-- is not evidence) carries the same t_ca_id as the trade's first-encountered report;
-- owning_account_number is set once at first encounter and is never replaced by a later report.
SELECT
  m.trade_number
FROM @this_model AS m
JOIN raw.trade_cdc AS r ON r.t_id = m.trade_number
WHERE r.cdc_flag IS NOT NULL AND r.cdc_flag IN ('I', 'U', 'D')
  AND r.t_st_id IS NOT NULL AND r.t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  AND r.t_tt_id IS NOT NULL AND r.t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  AND r.t_ca_id IS DISTINCT FROM m.owning_account_number;
