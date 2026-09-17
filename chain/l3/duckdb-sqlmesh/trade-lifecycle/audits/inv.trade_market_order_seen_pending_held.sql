AUDIT (name "inv.trade_market_order_seen_pending_held");

-- L1.hole.market-order-seen-pending: reports every trade_number whose order_type is a market
-- order (TMB, TMS) and whose first-encountered report -- across both anchored sources, its
-- earliest raw.trade_history row if any exist, otherwise its earliest raw.trade_cdc row among
-- those with an anchored cdc_flag -- carries status PNDG. This invariant reports the trade held
-- for review; it does not resolve the hole. first_seen_late for such a trade is NULL, never
-- true or false.
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
SELECT trade_number
FROM combined
WHERE order_type IN ('TMB', 'TMS')
  AND status_at_first_report = 'PNDG';
