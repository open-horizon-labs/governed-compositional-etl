-- inv.trade_placed_at_matches_earliest_report (L2 cycle 2, new): for any
-- trade_number, placed_at equals th_dts of the trade's earliest
-- raw.trade_history row when any raw.trade_history rows exist for that trade,
-- and otherwise equals t_dts of the trade's earliest raw.trade_cdc row
-- (smallest (batch_date, cdc_dsn)). Zero rows means the invariant holds.

WITH first_cdc_report AS (
    SELECT t_id, t_dts
    FROM raw.trade_cdc
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
first_history_report AS (
    SELECT th_t_id, th_dts
    FROM raw.trade_history
    QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts) = 1
),
expected AS (
    SELECT
        fc.t_id AS trade_number,
        COALESCE(fh.th_dts, fc.t_dts) AS expected_placed_at
    FROM first_cdc_report fc
    LEFT JOIN first_history_report fh ON fh.th_t_id = fc.t_id
)
SELECT t.trade_number, t.placed_at, e.expected_placed_at
FROM governed.trade AS t
JOIN expected AS e ON e.trade_number = t.trade_number
WHERE t.placed_at <> e.expected_placed_at;
