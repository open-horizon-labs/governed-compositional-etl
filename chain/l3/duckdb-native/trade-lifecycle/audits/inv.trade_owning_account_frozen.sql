-- inv.trade_owning_account_frozen (restated): for any trade_number, every
-- anchored raw.trade_cdc report of that trade (cdc_flag, t_st_id, t_tt_id
-- all anchored, null-sensitive) carries the same t_ca_id as the trade's
-- first-encountered report; owning_account_number is set once at first
-- encounter and never replaced by a later report. A report held under
-- L1.unknown-codes is not evidence here: it is held as a whole and is not
-- a later report to compare against the frozen value. Since governed.trade's
-- owning_account_number is written only on INSERT from the first-encountered
-- report, this checks every anchored raw report against the frozen value
-- actually persisted. Zero rows means the invariant holds.

SELECT
    tc.t_id AS trade_number,
    tc.t_ca_id AS reported_account,
    t.owning_account_number AS frozen_account
FROM raw.trade_cdc AS tc
JOIN governed.trade AS t
  ON t.trade_number = tc.t_id
WHERE tc.cdc_flag IS NOT NULL AND tc.cdc_flag IN ('I', 'U', 'D')
  AND tc.t_st_id IS NOT NULL AND tc.t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  AND tc.t_tt_id IS NOT NULL AND tc.t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  AND tc.t_ca_id IS DISTINCT FROM t.owning_account_number;
