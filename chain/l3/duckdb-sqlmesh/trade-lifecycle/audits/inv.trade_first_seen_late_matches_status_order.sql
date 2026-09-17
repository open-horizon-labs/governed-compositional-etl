AUDIT (name "inv.trade_first_seen_late_matches_status_order");

-- For any trade_number whose first-encountered report's status and order type are not held
-- under L1.unknown-codes (per inv.unknown_codes_held), first_seen_late is true if and only if
-- that report -- across both anchored sources, the trade's earliest raw.trade_history row if
-- any exist, otherwise its earliest raw.trade_cdc row -- carries a status (th_st_id or
-- t_st_id, respectively) later, in trade_code_meanings.status_order (PNDG, SBMT, CMPT, with
-- CNCL terminal and later than any of them), than order_type's own first lifecycle event: PNDG
-- for a limit order (TLB, TLS), per status_order's first entry; PNDG or SBMT, whichever the
-- first-encountered report states, for a market order (TMB, TMS), per L1.placement-moment's
-- amended sentence that the brokerage's own systems record a market order as pending on
-- receipt, before routing it, so PNDG or SBMT is the order's own first lifecycle event and only
-- CMPT or CNCL is late. A market order first reported PNDG is claimed by this invariant, as
-- first_seen_late false, not excluded from it; L1.hole.market-order-seen-pending is closed. A
-- trade whose first-encountered report's status or order type is held is not claimed by this
-- invariant; inv.trade_first_seen_late_defined_or_held covers that case instead. order_type's
-- own freeze is inv.trade_order_type_frozen's own audit, not this one's.
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
expected AS (
  SELECT
    c.trade_number,
    c.order_type,
    COALESCE(h.status_at_first_report, c.status_at_first_report) AS status_at_first_report
  FROM first_cdc_report AS c
  LEFT JOIN first_history_report AS h ON h.trade_number = c.trade_number
)
SELECT
  m.trade_number
FROM @this_model AS m
JOIN expected AS e ON e.trade_number = m.trade_number
WHERE e.order_type IN ('TLB', 'TLS', 'TMB', 'TMS')
  AND e.status_at_first_report IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  AND m.first_seen_late IS DISTINCT FROM (
    (CASE e.status_at_first_report
       WHEN 'PNDG' THEN 0
       WHEN 'SBMT' THEN 1
       WHEN 'CMPT' THEN 2
       WHEN 'CNCL' THEN 3
     END)
    >
    (CASE e.order_type
       WHEN 'TLB' THEN 0
       WHEN 'TLS' THEN 0
       WHEN 'TMB' THEN 1
       WHEN 'TMS' THEN 1
     END)
  );
