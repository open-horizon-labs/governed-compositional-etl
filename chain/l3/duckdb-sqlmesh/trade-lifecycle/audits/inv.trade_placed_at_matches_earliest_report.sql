AUDIT (name "inv.trade_placed_at_matches_earliest_report");

-- For any trade_number whose earliest report (across both anchored sources) is not held under
-- L1.unknown-codes, placed_at equals th_dts of the trade's earliest anchored raw.trade_history
-- row when any exist, and otherwise equals t_dts of the trade's earliest anchored raw.trade_cdc
-- row (smallest (batch_date, cdc_dsn) among rows with cdc_flag, t_st_id, and t_tt_id all
-- anchored). A trade whose earliest report is itself held, with a later report that is not, is
-- unclaimed by this invariant until L1.hole.held-first-report-placement is answered: it is held
-- and reported by inv.unknown_codes_held, given no placed_at value and no logical.trade row by
-- this job, so it is never a row @this_model holds for this audit to check.
WITH first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_dts AS placed_at
  FROM raw.trade_cdc
  WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
    AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
first_history_report AS (
  SELECT
    th_t_id AS trade_number,
    th_dts AS placed_at
  FROM raw.trade_history
  WHERE th_st_id IS NOT NULL AND th_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
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
