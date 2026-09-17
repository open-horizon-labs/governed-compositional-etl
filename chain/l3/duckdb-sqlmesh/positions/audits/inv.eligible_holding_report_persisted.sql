AUDIT (name "inv.eligible_holding_report_persisted");

-- Every (original_trade_number, current_trade_number) pair reported by raw.holding_history, none
-- of whose reports carries cdc_flag D, whose current_trade_number resolves to a logical.trade
-- row carrying owning_account_number, owning_account_effective_from, owning_customer_number, and
-- owning_customer_effective_from all non-null, has exactly one logical.holding_change row. A
-- pair with any cdc_flag D report is L1.hole.deletions' case and is not claimed here.
--
-- The D test is whole-pair abstention (BOOL_AND over every report of the pair), not a per-row
-- filter: a single D-flagged report anywhere in the pair's history drops the whole pair from this
-- claim, even though its other reports are null-flagged or I/U.
WITH eligible AS (
  SELECT
    hh_h_t_id AS original_trade_number,
    hh_t_id AS current_trade_number
  FROM raw.holding_history
  GROUP BY hh_h_t_id, hh_t_id
  HAVING BOOL_AND(cdc_flag IS DISTINCT FROM 'D')
),
eligible_pinned AS (
  SELECT
    e.original_trade_number,
    e.current_trade_number
  FROM eligible AS e
  JOIN governed.trade AS t ON t.trade_number = e.current_trade_number
  WHERE t.owning_account_number IS NOT NULL
    AND t.owning_account_effective_from IS NOT NULL
    AND t.owning_customer_number IS NOT NULL
    AND t.owning_customer_effective_from IS NOT NULL
)
SELECT
  ep.original_trade_number,
  ep.current_trade_number
FROM eligible_pinned AS ep
LEFT JOIN @this_model AS m
  ON m.original_trade_number = ep.original_trade_number
 AND m.current_trade_number = ep.current_trade_number
GROUP BY ep.original_trade_number, ep.current_trade_number
HAVING COUNT(m.original_trade_number) <> 1;
