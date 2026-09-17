-- inv.trade_first_seen_late_matches_status_order (L2 cycle 2): for any
-- trade_number, first_seen_late is true if and only if the trade's
-- first-encountered report across both anchored sources -- its earliest
-- raw.trade_history row if any exist, otherwise its earliest raw.trade_cdc
-- row -- carries a status (th_st_id or t_st_id, respectively) that is not
-- PNDG. Zero rows means the invariant holds.

WITH first_cdc_report AS (
    SELECT t_id, t_st_id
    FROM raw.trade_cdc
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
first_history_report AS (
    SELECT th_t_id, th_dts, th_st_id
    FROM raw.trade_history
    QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts) = 1
),
first_report AS (
    SELECT
        fc.t_id AS trade_number,
        COALESCE(fh.th_st_id, fc.t_st_id) AS first_status
    FROM first_cdc_report fc
    LEFT JOIN first_history_report fh ON fh.th_t_id = fc.t_id
)
SELECT t.trade_number, t.first_seen_late, fr.first_status AS first_encountered_status
FROM governed.trade AS t
JOIN first_report AS fr ON fr.trade_number = t.trade_number
WHERE t.first_seen_late IS DISTINCT FROM (fr.first_status IS DISTINCT FROM 'PNDG');
