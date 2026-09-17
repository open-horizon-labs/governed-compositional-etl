-- inv.every_received_trade_persisted (restated): for any trade_number that
-- has at least one raw.trade_cdc report whose coded fields (cdc_flag,
-- t_st_id, t_tt_id) are all anchored (per L1.unknown-codes) and none of
-- whose received reports carries cdc_flag D, exactly one governed.trade row
-- exists for that trade_number. A trade_number with any cdc_flag D report
-- is L1.hole.deletions' case and is not claimed by this invariant. Only
-- raw.trade_cdc counts toward "has a fully anchored report": identity,
-- ownership, and order type are sourced only from raw.trade_cdc, so a
-- trade whose only raw.trade_cdc report is held is known only through a
-- held report and is not yet known to this job even when a raw.trade_history
-- report for the same trade is itself anchored -- it must NOT appear as a
-- governed.trade row; inv.unknown_codes_held reports each such held report
-- instead. Zero rows means the invariant holds.

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
    WHERE cdc_flag IN ('I', 'U', 'D')
      AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
),
qualifying_trade_numbers AS (
    SELECT r.trade_number
    FROM reported_trade_numbers AS r
    LEFT JOIN trade_cdc_never_deleted AS d ON d.trade_number = r.trade_number
    JOIN has_anchored_report AS a ON a.trade_number = r.trade_number
    -- No raw.trade_cdc row at all (history-only identity, unexpected but not
    -- this invariant's concern) counts as no D report either: COALESCE to
    -- true keeps such a trade_number qualifying.
    WHERE COALESCE(d.none_carry_delete, TRUE)
),
non_qualifying_held_only AS (
    SELECT r.trade_number
    FROM reported_trade_numbers AS r
    LEFT JOIN trade_cdc_never_deleted AS d ON d.trade_number = r.trade_number
    LEFT JOIN has_anchored_report AS a ON a.trade_number = r.trade_number
    WHERE COALESCE(d.none_carry_delete, TRUE)
      AND a.trade_number IS NULL
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
