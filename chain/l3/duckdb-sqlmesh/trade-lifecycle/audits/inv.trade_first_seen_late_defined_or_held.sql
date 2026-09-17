AUDIT (name "inv.trade_first_seen_late_defined_or_held");

-- For any trade_number, first_seen_late is NULL if and only if the trade is held: either its
-- first-encountered report's status or order type is outside its anchored vocabulary
-- (L1.unknown-codes, per inv.unknown_codes_held), or it is a market order first reported PNDG
-- (L1.hole.market-order-seen-pending, per inv.trade_market_order_seen_pending_held).
-- first_seen_late is non-null (true or false) for every other trade.
WITH first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_tt_id AS order_type,
    t_st_id AS status_at_first_report
  FROM raw.trade_cdc
  WHERE cdc_flag IN ('I', 'U', 'D')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
first_history_report AS (
  SELECT
    th_t_id AS trade_number,
    th_st_id AS status_at_first_report
  FROM raw.trade_history
  QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts ASC) = 1
),
combined AS (
  SELECT
    c.trade_number,
    c.order_type,
    COALESCE(h.status_at_first_report, c.status_at_first_report) AS status_at_first_report
  FROM first_cdc_report AS c
  LEFT JOIN first_history_report AS h ON h.trade_number = c.trade_number
)
SELECT m.trade_number
FROM @this_model AS m
JOIN combined AS e ON e.trade_number = m.trade_number
WHERE (m.first_seen_late IS NULL) IS DISTINCT FROM (
  e.order_type NOT IN ('TLB', 'TLS', 'TMB', 'TMS')
  OR e.status_at_first_report NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  OR (e.order_type IN ('TMB', 'TMS') AND e.status_at_first_report = 'PNDG')
);
