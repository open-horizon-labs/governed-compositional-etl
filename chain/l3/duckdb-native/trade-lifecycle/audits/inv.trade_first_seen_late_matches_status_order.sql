-- inv.trade_first_seen_late_matches_status_order (restated,
-- L1.hole.market-order-seen-pending answered and closed): for any
-- trade_number whose first-encountered report's status and order type are
-- not held under L1.unknown-codes (per inv.unknown_codes_held),
-- first_seen_late is true if and only if that report -- across both
-- anchored sources, the trade's earliest raw.trade_history row if any
-- exist, otherwise its earliest valid_cdc_rows row -- carries a status
-- later, in trade_code_meanings.status_order (PNDG, SBMT, CMPT, with
-- terminal CNCL treated as later than any of them), than order_type's own
-- first lifecycle event: PNDG for a limit order (TLB, TLS); PNDG or SBMT
-- for a market order (TMB, TMS), since the brokerage's own systems record a
-- market order as pending on receipt, before routing it, so PNDG or SBMT is
-- the order's own first lifecycle event and only CMPT or CNCL is late. A
-- market order first reported PNDG is claimed by this invariant, as
-- first_seen_late false, not excluded from it. A trade whose
-- first-encountered report is held is not claimed by this invariant and is
-- excluded from scope entirely (not merely defaulted). order_type's own
-- freeze is checked separately by inv.trade_order_type_frozen. Zero rows
-- means the invariant holds.

WITH valid_cdc_rows AS (
    -- A row carrying any code outside its anchored vocabulary in any of
    -- cdc_flag, t_st_id, t_tt_id (null-sensitive) is held in its entirety.
    SELECT *
    FROM raw.trade_cdc
    WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
      AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
),
first_cdc_report AS (
    SELECT t_id, t_st_id, t_tt_id
    FROM valid_cdc_rows
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
first_history_report AS (
    -- th_st_id must itself be anchored: no COALESCE over a held row's
    -- status. A trade with no anchored history row falls through to
    -- first_cdc_report's own t_st_id.
    SELECT th_t_id, th_dts, th_st_id
    FROM raw.trade_history
    WHERE th_st_id IS NOT NULL AND th_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts) = 1
),
first_report AS (
    SELECT
        fc.t_id AS trade_number,
        fc.t_tt_id AS order_type,
        COALESCE(fh.th_st_id, fc.t_st_id) AS first_status
    FROM first_cdc_report fc
    LEFT JOIN first_history_report fh ON fh.th_t_id = fc.t_id
),
ranked AS (
    SELECT
        trade_number,
        order_type,
        first_status,
        CASE first_status
            WHEN 'PNDG' THEN 0 WHEN 'SBMT' THEN 1 WHEN 'CMPT' THEN 2 WHEN 'CNCL' THEN 3
        END AS status_rank,
        CASE order_type
            WHEN 'TLB' THEN 0 WHEN 'TLS' THEN 0
            WHEN 'TMB' THEN 1 WHEN 'TMS' THEN 1
        END AS first_lifecycle_rank
    FROM first_report
),
in_scope AS (
    -- order_type and first_status must both be anchored; a market order
    -- first reported PNDG is now claimed (first_lifecycle_rank 1, same as
    -- SBMT), not excluded.
    SELECT *
    FROM ranked
    WHERE order_type IN ('TLB', 'TLS', 'TMB', 'TMS')
      AND first_status IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
),
expected AS (
    SELECT
        trade_number,
        (status_rank > first_lifecycle_rank) AS expected_first_seen_late
    FROM in_scope
)
SELECT t.trade_number, 'first_seen_late_mismatch' AS problem
FROM governed.trade AS t
JOIN expected AS e ON e.trade_number = t.trade_number
WHERE t.first_seen_late IS DISTINCT FROM e.expected_first_seen_late;
