-- inv.holding_change_ownership_frozen: for any (original_trade_number,
-- current_trade_number) pair, owning_account_number, owning_account_effective_from,
-- owning_customer_number, and owning_customer_effective_from are set once, at
-- first encounter, and never replaced by a later report. Since
-- governed.holding_change writes these four columns only on INSERT, and they
-- are copied unchanged from governed.trade's own frozen reference for the
-- pair's current trade, this checks every persisted holding_change row against
-- what governed.trade currently holds for that trade. Zero rows means the
-- invariant holds.

SELECT
    hc.original_trade_number,
    hc.current_trade_number
FROM governed.holding_change AS hc
JOIN governed.trade AS t
  ON t.trade_number = hc.current_trade_number
WHERE hc.owning_account_number IS DISTINCT FROM t.owning_account_number
   OR hc.owning_account_effective_from IS DISTINCT FROM t.owning_account_effective_from
   OR hc.owning_customer_number IS DISTINCT FROM t.owning_customer_number
   OR hc.owning_customer_effective_from IS DISTINCT FROM t.owning_customer_effective_from;
