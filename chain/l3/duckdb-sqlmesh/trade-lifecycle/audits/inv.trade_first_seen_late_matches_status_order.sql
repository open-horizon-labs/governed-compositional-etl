AUDIT (name "inv.trade_first_seen_late_matches_status_order");

-- For any trade_number whose order_type is one of the anchored four codes and whose
-- first-encountered report's status is not PNDG for a market order, first_seen_late is true
-- if and only if that report -- across both anchored sources, the trade's earliest
-- raw.trade_history row if any exist, otherwise its earliest raw.trade_cdc row -- carries a
-- status (th_st_id or t_st_id, respectively) later, in trade_code_meanings.status_order
-- (PNDG, SBMT, CMPT, with CNCL terminal and later than any of them), than order_type's first
-- lifecycle event: PNDG for a limit order (TLB, TLS), per status_order's first entry; SBMT for
-- a market order (TMB, TMS), per L1.placement-moment's amended sentence that an order sent
-- straight to market has no pending stage. A trade whose order_type is outside the anchored
-- four, or a market order whose first-encountered report is PNDG, is not claimed by this
-- invariant. order_type itself is handoff.raw.trade_cdc.t_tt_id->logical.trade.order_type,
-- selector first_encounter_only, frozen_from_first_encounter; this recomputes it fresh from
-- the trade's first-encountered raw.trade_cdc row (unconditionally, not only in the claimed
-- cases above) and diffs it against what governed.trade actually holds, so a later report's
-- change to the stored order_type -- the value this invariant's own comparison depends on --
-- is itself a violation this audit can name.
WITH first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_tt_id AS order_type,
    t_st_id AS status_at_first_report
  FROM raw.trade_cdc
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
first_history_report AS (
  SELECT
    th_t_id AS trade_number,
    th_st_id AS status_at_first_report
  FROM raw.trade_history
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
WHERE m.order_type IS DISTINCT FROM e.order_type
   OR (
     m.order_type IN ('TLB', 'TLS', 'TMB', 'TMS')
     AND NOT (m.order_type IN ('TMB', 'TMS') AND e.status_at_first_report = 'PNDG')
     AND m.first_seen_late IS DISTINCT FROM (
       (CASE e.status_at_first_report
          WHEN 'PNDG' THEN 0
          WHEN 'SBMT' THEN 1
          WHEN 'CMPT' THEN 2
          WHEN 'CNCL' THEN 3
        END)
       >
       (CASE m.order_type
          WHEN 'TLB' THEN 0
          WHEN 'TLS' THEN 0
          WHEN 'TMB' THEN 1
          WHEN 'TMS' THEN 1
        END)
     )
   );
