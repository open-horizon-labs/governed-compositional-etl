AUDIT (name "inv.trade_held_first_report_unclaimed");

-- For any trade_number whose earliest report of either anchored source (raw.trade_cdc or
-- raw.trade_history) is held under L1.unknown-codes, or whose earliest raw.trade_cdc report --
-- the source of owning_account_number and order_type, whatever the earliest raw.trade_history
-- row says -- is held, no logical.trade row exists. When every raw.trade_history row for a
-- trade is held, the earliest one still orders first and the trade is held on that account too.
WITH earliest_history_any AS (
  SELECT
    th_t_id AS trade_number,
    th_st_id AS status_at_first_report
  FROM raw.trade_history
  QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts ASC) = 1
),
earliest_cdc_any AS (
  SELECT
    t_id AS trade_number,
    cdc_flag,
    t_st_id,
    t_tt_id
  FROM raw.trade_cdc
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
earliest_report_held AS (
  SELECT trade_number
  FROM earliest_history_any
  WHERE status_at_first_report IS NULL
     OR status_at_first_report NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  UNION
  SELECT trade_number
  FROM earliest_cdc_any
  WHERE cdc_flag IS NULL OR cdc_flag NOT IN ('I', 'U', 'D')
     OR t_st_id IS NULL OR t_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
     OR t_tt_id IS NULL OR t_tt_id NOT IN ('TLB', 'TLS', 'TMB', 'TMS')
)
SELECT
  h.trade_number
FROM earliest_report_held AS h
JOIN @this_model AS m ON m.trade_number = h.trade_number;
