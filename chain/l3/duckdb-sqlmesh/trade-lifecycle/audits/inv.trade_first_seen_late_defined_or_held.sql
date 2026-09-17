AUDIT (name "inv.trade_first_seen_late_defined_or_held");

-- For any trade_number that inv.every_received_trade_persisted claims a logical.trade row for,
-- first_seen_late is NULL if and only if the trade is held: it is a market order first reported
-- PNDG (L1.hole.market-order-seen-pending, per inv.trade_market_order_seen_pending_held).
-- first_seen_late is non-null (true or false) for every other such trade. A trade_number whose
-- earliest report is itself held while a later raw.trade_cdc report is not is not claimed by
-- inv.every_received_trade_persisted at all, pending L1.hole.held-first-report-placement, and so
-- has no row in @this_model for this audit to check either.
WITH first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_tt_id AS order_type,
    t_st_id AS status_at_first_report
  FROM raw.trade_cdc
  WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
    AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
first_history_report AS (
  SELECT
    th_t_id AS trade_number,
    th_st_id AS status_at_first_report
  FROM raw.trade_history
  WHERE th_st_id IS NOT NULL AND th_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
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
  e.order_type IN ('TMB', 'TMS') AND e.status_at_first_report = 'PNDG'
);
