AUDIT (name "inv.every_received_trade_persisted");

-- For any trade_number none of whose received reports carries cdc_flag D, exactly one
-- governed.trade row exists for that trade_number; a trade_number with any cdc_flag D report
-- is L1.hole.deletions' case and is not claimed by this invariant. raw.trade_history carries
-- no cdc_flag column, so a history report never carries D on its own.
WITH reported_trade_numbers AS (
  SELECT t_id AS trade_number FROM raw.trade_cdc
  UNION
  SELECT th_t_id AS trade_number FROM raw.trade_history
),
-- IS DISTINCT FROM is null-safe: it keeps any row whose cdc_flag is absent in scope rather
-- than unknown; raw.trade_history contributes trade_numbers with no cdc_flag column at all.
cdc_flag_scope AS (
  SELECT
    t_id AS trade_number,
    BOOL_AND(cdc_flag IS DISTINCT FROM 'D') AS has_no_d_report
  FROM raw.trade_cdc
  GROUP BY t_id
),
in_scope_trade_numbers AS (
  SELECT r.trade_number
  FROM reported_trade_numbers AS r
  LEFT JOIN cdc_flag_scope AS s ON s.trade_number = r.trade_number
  WHERE COALESCE(s.has_no_d_report, TRUE)
)
SELECT
  i.trade_number
FROM in_scope_trade_numbers AS i
LEFT JOIN @this_model AS m ON m.trade_number = i.trade_number
GROUP BY i.trade_number
HAVING COUNT(m.trade_number) <> 1;
