AUDIT (name "inv.trade_owning_account_frozen");

-- For any trade_number, every raw.trade_cdc report of that trade carries the same t_ca_id as
-- the trade's first-encountered report; owning_account_number is set once at first encounter
-- and is never replaced by a later report.
SELECT
  m.trade_number
FROM @this_model AS m
JOIN raw.trade_cdc AS r ON r.t_id = m.trade_number
WHERE r.t_ca_id IS DISTINCT FROM m.owning_account_number;
