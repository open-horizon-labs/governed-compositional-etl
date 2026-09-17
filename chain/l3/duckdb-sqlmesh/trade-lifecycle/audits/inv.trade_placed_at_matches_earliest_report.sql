AUDIT (name "inv.trade_placed_at_matches_earliest_report");

-- For any trade_number, placed_at equals th_dts of the trade's earliest raw.trade_history row
-- when any raw.trade_history rows exist for that trade, and otherwise equals t_dts of the
-- trade's earliest raw.trade_cdc row (smallest (batch_date, cdc_dsn)).
WITH first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_dts AS placed_at
  FROM raw.trade_cdc
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
first_history_report AS (
  SELECT
    th_t_id AS trade_number,
    th_dts AS placed_at
  FROM raw.trade_history
  QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts ASC) = 1
),
expected AS (
  SELECT
    c.trade_number,
    COALESCE(h.placed_at, c.placed_at) AS placed_at
  FROM first_cdc_report AS c
  LEFT JOIN first_history_report AS h ON h.trade_number = c.trade_number
)
SELECT
  m.trade_number
FROM @this_model AS m
JOIN expected AS e ON e.trade_number = m.trade_number
WHERE m.placed_at IS DISTINCT FROM e.placed_at;
