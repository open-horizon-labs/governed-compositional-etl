-- inv.trade_held_first_report_unclaimed: for any trade_number whose earliest
-- report of either anchored source (raw.trade_cdc or raw.trade_history) is
-- held under L1.unknown-codes, or any of whose placement-fixing facts
-- (placement, owning account, order type) would come from a held report --
-- the earliest report of the source that supplies that fact is held,
-- whatever another source's earliest report says -- no governed.trade row
-- exists for that trade_number; it is reported by inv.unknown_codes_held
-- instead. Checked two ways: (1) the trade's true earliest report (across
-- both sources, unfiltered, per report_order) is held, or (2) the trade's
-- true earliest raw.trade_cdc report specifically is held (owning account
-- and order type always come from that exact report, even under an
-- anchored earliest history row) -- either way, this trade_number must NOT
-- appear as a governed.trade row. Zero rows means the invariant holds.

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
earliest_cdc_held AS (
    SELECT
        t_id AS trade_number,
        cdc_flag IS NULL OR cdc_flag NOT IN ('I', 'U', 'D')
        OR t_st_id IS NULL OR t_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
        OR t_tt_id IS NULL OR t_tt_id NOT IN ('TLB', 'TLS', 'TMB', 'TMS') AS held
    FROM earliest_cdc_row
),
earliest_overall_held AS (
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
trade_unclaimed AS (
    SELECT trade_number FROM earliest_overall_held WHERE held
    UNION
    SELECT trade_number FROM earliest_cdc_held WHERE held
)
SELECT tu.trade_number, COUNT(t.trade_number) AS governed_row_count
FROM trade_unclaimed tu
JOIN governed.trade t ON t.trade_number = tu.trade_number
GROUP BY tu.trade_number;
