AUDIT (name "inv.trade_placement_reference_frozen");

-- For any trade_number, placed_at, owning_account_effective_from, owning_customer_number,
-- and owning_customer_effective_from are each set once -- from the trade's earliest anchored
-- report and the account and customer statements resolved as of that report's own time -- and
-- are never replaced by a later report of the same trade. Recompute all four fresh (placed_at
-- from the earliest anchored report across both anchored sources -- an unanchored report is
-- held as a whole and is not evidence; the account statement as of the currently stored
-- owning_account_number and placed_at; the customer statement as of the currently stored
-- owning_customer_number and placed_at) and diff against what governed.trade actually holds.
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
first_report AS (
  SELECT
    c.trade_number,
    COALESCE(h.placed_at, c.placed_at) AS placed_at
  FROM first_cdc_report AS c
  LEFT JOIN first_history_report AS h ON h.trade_number = c.trade_number
),
resolved_account AS (
  SELECT
    m.trade_number,
    a.effective_from AS owning_account_effective_from,
    a.owning_customer_number
  FROM @this_model AS m
  JOIN governed.account AS a
    ON a.account_number = m.owning_account_number
   AND a.effective_from <= m.placed_at
  QUALIFY ROW_NUMBER() OVER (PARTITION BY m.trade_number ORDER BY a.effective_from DESC) = 1
),
resolved_customer AS (
  SELECT
    m.trade_number,
    c.effective_from AS owning_customer_effective_from
  FROM @this_model AS m
  JOIN governed.customer AS c
    ON c.customer_number = m.owning_customer_number
   AND c.effective_from <= m.placed_at
  QUALIFY ROW_NUMBER() OVER (PARTITION BY m.trade_number ORDER BY c.effective_from DESC) = 1
)
SELECT
  m.trade_number
FROM @this_model AS m
JOIN first_report AS f ON f.trade_number = m.trade_number
LEFT JOIN resolved_account AS ra ON ra.trade_number = m.trade_number
LEFT JOIN resolved_customer AS rc ON rc.trade_number = m.trade_number
WHERE m.placed_at IS NULL
   OR m.placed_at IS DISTINCT FROM f.placed_at
   OR m.owning_account_effective_from IS DISTINCT FROM ra.owning_account_effective_from
   OR m.owning_customer_number IS DISTINCT FROM ra.owning_customer_number
   OR m.owning_customer_effective_from IS DISTINCT FROM rc.owning_customer_effective_from;
