-- inv.trade_owning_account_frozen: for any trade_number, every raw.trade_cdc
-- report of that trade carries the same t_ca_id as the trade's
-- first-encountered report; owning_account_number is set once at first
-- encounter and never replaced by a later report. Since governed.trade's
-- owning_account_number is written only on INSERT from the first-encountered
-- report, this checks every raw report against the frozen value actually
-- persisted. Zero rows means the invariant holds.

SELECT
    tc.t_id AS trade_number,
    tc.t_ca_id AS reported_account,
    t.owning_account_number AS frozen_account
FROM raw.trade_cdc AS tc
JOIN governed.trade AS t
  ON t.trade_number = tc.t_id
WHERE tc.t_ca_id IS DISTINCT FROM t.owning_account_number;
