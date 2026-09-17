AUDIT (name "inv.trade_first_seen_late_defined_or_held");

-- For any trade_number that inv.every_received_trade_persisted claims a logical.trade row for,
-- first_seen_late is NULL if and only if inv.unknown_codes_held reports its first-encountered
-- report's status or order type as outside the anchored vocabularies. first_seen_late is
-- non-null (true or false) for every other such trade, including a market order first reported
-- PNDG, which is now decided (false) rather than held: L1.hole.market-order-seen-pending is
-- closed. A trade_number any of whose placement-fixing facts (placement, owning account, or
-- order type) would come from a held report is not claimed by inv.every_received_trade_persisted
-- at all, pending L1.hole.held-first-report-placement, and so has no first_seen_late value for
-- this invariant to claim either.
WITH first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_tt_id AS order_type,
    t_st_id AS status_at_first_report
  FROM raw.trade_cdc
  WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
    AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
first_history_report AS (
  SELECT
    th_t_id AS trade_number,
    th_st_id AS status_at_first_report
  FROM raw.trade_history
  WHERE th_st_id IS NOT NULL AND th_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts ASC) = 1
),
combined AS (
  SELECT
    c.trade_number,
    c.order_type,
    COALESCE(h.status_at_first_report, c.status_at_first_report) AS status_at_first_report
  FROM first_cdc_report AS c
  LEFT JOIN first_history_report AS h ON h.trade_number = c.trade_number
)
SELECT m.trade_number
FROM @this_model AS m
JOIN combined AS e ON e.trade_number = m.trade_number
WHERE (m.first_seen_late IS NULL) IS DISTINCT FROM (
  e.order_type IS NULL OR e.order_type NOT IN ('TLB', 'TLS', 'TMB', 'TMS')
  OR e.status_at_first_report IS NULL OR e.status_at_first_report NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
);
