-- inv.every_received_trade_persisted (restated): for any trade_number that
-- has at least one received raw.trade_cdc report whose coded fields
-- (cdc_flag, t_st_id, t_tt_id) are all anchored and that does not carry
-- cdc_flag D, and whose earliest report (across both anchored sources) is
-- not itself held under L1.unknown-codes, exactly one governed.trade row
-- exists for that trade_number. A trade_number with any cdc_flag D report
-- among its received raw.trade_cdc reports is L1.hole.deletions' case and is
-- not claimed by this invariant. A trade_number known only through reports
-- held under L1.unknown-codes, or known only through raw.trade_history rows
-- (raw.trade_history alone carries no identity handoff), is not yet known to
-- this job and is not claimed either; inv.unknown_codes_held reports each
-- held report instead. A trade_number whose earliest report is itself held
-- while a later raw.trade_cdc report is anchored is likewise not claimed,
-- pending L1.hole.held-first-report-placement (inv.trade_placed_at_matches_
-- earliest_report agrees): it must NOT appear as a governed.trade row. Zero
-- rows means the invariant holds.

WITH reported_trade_numbers AS (
    SELECT DISTINCT t_id AS trade_number FROM raw.trade_cdc
    UNION
    SELECT DISTINCT th_t_id AS trade_number FROM raw.trade_history
),
trade_cdc_never_deleted AS (
    SELECT
        t_id AS trade_number,
        BOOL_AND(cdc_flag IS DISTINCT FROM 'D') AS none_carry_delete
    FROM raw.trade_cdc
    GROUP BY t_id
),
-- A trade_number has a fully anchored report when at least one of its
-- raw.trade_cdc rows has cdc_flag, t_st_id, and t_tt_id all anchored.
-- raw.trade_history does not count: identity, ownership, and order type are
-- sourced only from raw.trade_cdc (trade.sql's first_cdc_report), so an
-- anchored raw.trade_history report alone does not make the trade known.
has_anchored_report AS (
    SELECT DISTINCT t_id AS trade_number, TRUE AS anchored
    FROM raw.trade_cdc
    WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
      AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
),
-- L1.hole.held-first-report-placement: whether the trade's true earliest
-- report (across both sources, unfiltered, per report_order) is itself
-- held under L1.unknown-codes, null-sensitive.
earliest_cdc_row AS (
    SELECT t_id, cdc_flag, t_st_id, t_tt_id
    FROM raw.trade_cdc
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
earliest_history_row AS (
    SELECT th_t_id, th_st_id
    FROM raw.trade_history
    QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts) = 1
),
earliest_report_held AS (
    SELECT
        COALESCE(h.th_t_id, c.t_id) AS trade_number,
        CASE
            WHEN h.th_t_id IS NOT NULL THEN
                h.th_st_id IS NULL OR h.th_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
            ELSE
                c.cdc_flag IS NULL OR c.cdc_flag NOT IN ('I', 'U', 'D')
                OR c.t_st_id IS NULL OR c.t_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
                OR c.t_tt_id IS NULL OR c.t_tt_id NOT IN ('TLB', 'TLS', 'TMB', 'TMS')
        END AS held
    FROM earliest_history_row h
    FULL OUTER JOIN earliest_cdc_row c ON c.t_id = h.th_t_id
),
qualifying_trade_numbers AS (
    SELECT r.trade_number
    FROM reported_trade_numbers AS r
    LEFT JOIN trade_cdc_never_deleted AS d ON d.trade_number = r.trade_number
    JOIN has_anchored_report AS a ON a.trade_number = r.trade_number
    LEFT JOIN earliest_report_held AS erh ON erh.trade_number = r.trade_number
    -- No raw.trade_cdc row at all (history-only identity, unexpected but not
    -- this invariant's concern) counts as no D report either: COALESCE to
    -- true keeps such a trade_number qualifying.
    WHERE COALESCE(d.none_carry_delete, TRUE)
      AND COALESCE(NOT erh.held, FALSE)
),
non_qualifying_held_only AS (
    -- Known only through held reports (no fully anchored raw.trade_cdc
    -- report at all), OR its earliest report is itself held even though a
    -- later raw.trade_cdc report is anchored (L1.hole.held-first-report-
    -- placement). Either way: must NOT appear as a governed.trade row.
    SELECT r.trade_number
    FROM reported_trade_numbers AS r
    LEFT JOIN trade_cdc_never_deleted AS d ON d.trade_number = r.trade_number
    LEFT JOIN has_anchored_report AS a ON a.trade_number = r.trade_number
    LEFT JOIN earliest_report_held AS erh ON erh.trade_number = r.trade_number
    WHERE COALESCE(d.none_carry_delete, TRUE)
      AND (a.trade_number IS NULL OR COALESCE(erh.held, TRUE))
)
SELECT
    q.trade_number,
    COUNT(t.trade_number) AS governed_row_count,
    'missing_or_duplicate' AS problem
FROM qualifying_trade_numbers AS q
LEFT JOIN governed.trade AS t ON t.trade_number = q.trade_number
GROUP BY q.trade_number
HAVING COUNT(t.trade_number) <> 1

UNION ALL

SELECT h.trade_number, COUNT(t.trade_number), 'held_only_but_persisted' AS problem
FROM non_qualifying_held_only AS h
JOIN governed.trade AS t ON t.trade_number = h.trade_number
GROUP BY h.trade_number;
