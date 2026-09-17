AUDIT (name "inv.trade_first_seen_late_matches_status_order");

-- For any trade_number, first_seen_late is true if and only if the trade's first-encountered
-- report across both anchored sources -- its earliest raw.trade_history row if any exist,
-- otherwise its earliest raw.trade_cdc row -- carries a status (th_st_id or t_st_id,
-- respectively) that is not PNDG, using trade_code_meanings.status_order's designation of
-- PNDG as the lifecycle's first status and report_order to identify that first-encountered
-- report.
WITH first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_st_id AS status_at_first_report
  FROM raw.trade_cdc
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
first_history_report AS (
  SELECT
    th_t_id AS trade_number,
    th_st_id AS status_at_first_report
  FROM raw.trade_history
  QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts ASC) = 1
),
expected AS (
  SELECT
    c.trade_number,
    COALESCE(h.status_at_first_report, c.status_at_first_report) AS status_at_first_report
  FROM first_cdc_report AS c
  LEFT JOIN first_history_report AS h ON h.trade_number = c.trade_number
)
SELECT
  m.trade_number
FROM @this_model AS m
JOIN expected AS e ON e.trade_number = m.trade_number
WHERE m.first_seen_late IS DISTINCT FROM (e.status_at_first_report IS DISTINCT FROM 'PNDG');
