AUDIT (name "inv.trade_order_type_frozen");

-- For any trade_number, order_type equals t_tt_id on the trade's first-encountered anchored
-- raw.trade_cdc report, and every anchored report agrees with that first-encountered value.
-- Recompute the first-encountered anchored value fresh (not merely trust m.order_type) and
-- compare both m.order_type and every anchored report's t_tt_id against it. A held report is
-- not evidence either way: it neither confirms nor contradicts order_type, and is excluded
-- from this invariant's comparison entirely.
WITH first_anchored AS (
  SELECT
    t_id AS trade_number,
    t_tt_id AS order_type
  FROM raw.trade_cdc
  WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
    AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
)
SELECT DISTINCT
  m.trade_number
FROM @this_model AS m
JOIN first_anchored AS f ON f.trade_number = m.trade_number
JOIN raw.trade_cdc AS r ON r.t_id = m.trade_number
WHERE r.cdc_flag IS NOT NULL AND r.cdc_flag IN ('I', 'U', 'D')
  AND r.t_st_id IS NOT NULL AND r.t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  AND r.t_tt_id IS NOT NULL AND r.t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  AND (
    m.order_type IS DISTINCT FROM f.order_type
    OR r.t_tt_id IS DISTINCT FROM f.order_type
  );
