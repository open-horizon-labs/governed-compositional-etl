AUDIT (name "inv.trade_first_seen_late_matches_status_order");

-- For any trade_number, first_seen_late is true if and only if the trade's first-encountered
-- raw.trade_cdc report's t_st_id is not PNDG, using trade_code_meanings.status_order's
-- designation of PNDG as the lifecycle's first status and report_order's (batch_date,
-- cdc_dsn) ordering to identify that first-encountered report.
WITH first_report AS (
  SELECT
    t_id AS trade_number,
    t_st_id
  FROM raw.trade_cdc
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
)
SELECT
  m.trade_number
FROM @this_model AS m
JOIN first_report AS f ON f.trade_number = m.trade_number
WHERE m.first_seen_late IS DISTINCT FROM (f.t_st_id <> 'PNDG');
