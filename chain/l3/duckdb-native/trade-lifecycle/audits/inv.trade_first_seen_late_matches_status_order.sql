-- inv.trade_first_seen_late_matches_status_order (restated): for any
-- trade_number whose first-encountered report's status and order type are
-- not held under L1.unknown-codes (per inv.unknown_codes_held) and that is
-- not held as a market order seen pending (per
-- inv.trade_market_order_seen_pending_held), first_seen_late is true if and
-- only if that report -- across both anchored sources, the trade's
-- earliest raw.trade_history row if any exist, otherwise its earliest
-- valid_cdc_rows row -- carries a status later, in
-- trade_code_meanings.status_order (PNDG, SBMT, CMPT, with terminal CNCL
-- treated as later than any of them), than order_type's first lifecycle
-- event: PNDG for a limit order (TLB, TLS); SBMT for a market order (TMB,
-- TMS). A trade whose first-encountered report is held, or that is held as
-- a market order seen pending, is not claimed by this invariant and is
-- excluded from scope entirely (not merely defaulted). order_type's own
-- freeze is checked separately by inv.trade_order_type_frozen. Zero rows
-- means the invariant holds.

WITH valid_cdc_rows AS (
    -- A row carrying any code outside its anchored vocabulary in any of
    -- cdc_flag, t_st_id, t_tt_id is held in its entirety.
    SELECT *
    FROM raw.trade_cdc
    WHERE cdc_flag IN ('I', 'U', 'D')
      AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
),
first_cdc_report AS (
    SELECT t_id, t_st_id, t_tt_id
    FROM valid_cdc_rows
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
first_history_report AS (
    SELECT th_t_id, th_dts, th_st_id
    FROM raw.trade_history
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
    -- order_type and first_status must both be anchored, and a market
    -- order whose first-encountered report is PNDG is excluded from this
    -- invariant's claim (held under the hole instead).
    SELECT *
    FROM ranked
    WHERE order_type IN ('TLB', 'TLS', 'TMB', 'TMS')
      AND first_status IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      AND NOT (order_type IN ('TMB', 'TMS') AND first_status = 'PNDG')
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
