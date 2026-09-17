-- inv.trade_first_seen_late_matches_status_order: for any trade_number,
-- first_seen_late is true if and only if the trade's first-encountered
-- raw.trade_cdc report's t_st_id is not PNDG (trade_code_meanings.status_order's
-- first status), using report_order's (batch_date, cdc_dsn) ordering to
-- identify that first-encountered report. Zero rows means the invariant holds.

WITH first_report AS (
    SELECT t_id, t_st_id
    FROM raw.trade_cdc
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
)
SELECT t.trade_number, t.first_seen_late, fr.t_st_id AS first_encountered_status
FROM governed.trade AS t
JOIN first_report AS fr ON fr.t_id = t.trade_number
WHERE t.first_seen_late <> (fr.t_st_id <> 'PNDG');
