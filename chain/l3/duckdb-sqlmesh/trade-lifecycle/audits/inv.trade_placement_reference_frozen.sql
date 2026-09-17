AUDIT (name "inv.trade_placement_reference_frozen");

-- For any trade_number, placed_at, owning_account_effective_from, and owning_customer_number
-- are each set once -- from the trade's first-encountered report and the account statement
-- resolved as of that report's own time -- and are never replaced by a later report of the
-- same trade. Recompute both halves fresh (placed_at from the first-encountered report;
-- the account statement as of the currently stored owning_account_number and placed_at) and
-- diff against what governed.trade actually holds.
WITH first_report AS (
  SELECT
    t_id AS trade_number,
    t_dts AS placed_at
  FROM raw.trade_cdc
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
resolved AS (
  SELECT
    m.trade_number,
    a.effective_from AS owning_account_effective_from,
    a.owning_customer_number
  FROM @this_model AS m
  JOIN governed.account AS a
    ON a.account_number = m.owning_account_number
   AND a.effective_from <= m.placed_at
  QUALIFY ROW_NUMBER() OVER (PARTITION BY m.trade_number ORDER BY a.effective_from DESC) = 1
)
SELECT
  m.trade_number
FROM @this_model AS m
JOIN first_report AS f ON f.trade_number = m.trade_number
LEFT JOIN resolved AS r ON r.trade_number = m.trade_number
WHERE m.placed_at IS DISTINCT FROM f.placed_at
   OR m.owning_account_effective_from IS DISTINCT FROM r.owning_account_effective_from
   OR m.owning_customer_number IS DISTINCT FROM r.owning_customer_number;
