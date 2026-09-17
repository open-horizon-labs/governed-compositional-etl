-- inv.trade_first_seen_late_matches_status_order (L2 cycle 5, restated): for
-- any trade_number whose order_type is one of the anchored four codes and
-- whose first-encountered report's status is not PNDG for a market order,
-- first_seen_late is true if and only if that report -- across both anchored
-- sources, the trade's earliest raw.trade_history row if any exist,
-- otherwise its earliest raw.trade_cdc row -- carries a status later, in
-- trade_code_meanings.status_order (PNDG, SBMT, CMPT, with terminal CNCL
-- treated as later than any of them), than order_type's first lifecycle
-- event: PNDG for a limit order (TLB, TLS), per status_order's first entry;
-- SBMT for a market order (TMB, TMS), per L1.placement-moment's amended
-- sentence. A trade whose order_type is outside the anchored four, or a
-- market order whose first-encountered report is PNDG, is not claimed by
-- this invariant and is excluded from scope entirely (not merely defaulted).
-- Also checked: order_type itself is frozen_from_first_encounter (set once
-- from the trade's first-encountered raw.trade_cdc report's t_tt_id and
-- never replaced), since first_seen_late's restated derivation depends on it
-- and a corrupted or drifted order_type would make first_seen_late
-- unrecomputable from its own recorded inputs. Zero rows means the
-- invariant holds.

WITH first_cdc_report AS (
    SELECT t_id, t_st_id, t_tt_id
    FROM raw.trade_cdc
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
    -- order_type must be one of the anchored four, and a market order whose
    -- first-encountered report is PNDG is excluded from this invariant's claim.
    SELECT *
    FROM ranked
    WHERE order_type IN ('TLB', 'TLS', 'TMB', 'TMS')
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
WHERE t.first_seen_late IS DISTINCT FROM e.expected_first_seen_late

UNION ALL

SELECT t.trade_number, 'order_type_not_frozen' AS problem
FROM governed.trade AS t
JOIN first_report fr ON fr.trade_number = t.trade_number
WHERE t.order_type IS DISTINCT FROM fr.order_type;
