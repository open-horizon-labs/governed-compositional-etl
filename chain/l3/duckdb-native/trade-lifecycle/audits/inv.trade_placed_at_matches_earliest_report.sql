-- inv.trade_placed_at_matches_earliest_report (restated): for any
-- trade_number whose earliest report (across both anchored sources) is not
-- held under L1.unknown-codes, placed_at equals th_dts of the trade's
-- earliest anchored raw.trade_history row when any exist for that trade,
-- and otherwise equals t_dts of the trade's earliest anchored raw.trade_cdc
-- row (smallest (batch_date, cdc_dsn)). A trade whose earliest report is
-- itself held, with a later raw.trade_cdc report that is not, is unclaimed
-- by this invariant (L1.hole.held-first-report-placement): it has no
-- placed_at value and no governed.trade row (see
-- inv.every_received_trade_persisted); it is reported by
-- inv.unknown_codes_held instead. Zero rows means the invariant holds.

WITH earliest_cdc_row AS (
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
first_cdc_report AS (
    SELECT t_id, t_dts
    FROM raw.trade_cdc
    WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
      AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
first_history_report AS (
    SELECT th_t_id, th_dts
    FROM raw.trade_history
    WHERE th_st_id IS NOT NULL AND th_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts) = 1
),
expected AS (
    SELECT
        fc.t_id AS trade_number,
        COALESCE(fh.th_dts, fc.t_dts) AS expected_placed_at
    FROM first_cdc_report fc
    LEFT JOIN first_history_report fh ON fh.th_t_id = fc.t_id
    WHERE fc.t_id IN (SELECT trade_number FROM earliest_report_held WHERE NOT held)
)
SELECT t.trade_number, t.placed_at, e.expected_placed_at
FROM governed.trade AS t
JOIN expected AS e ON e.trade_number = t.trade_number
WHERE t.placed_at IS DISTINCT FROM e.expected_placed_at;
