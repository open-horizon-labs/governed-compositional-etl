-- inv.trade_order_type_frozen (restated): for any trade_number the job
-- claims a governed.trade row for, order_type equals t_tt_id on the
-- trade's first-encountered anchored raw.trade_cdc report, and every other
-- anchored raw.trade_cdc report of that trade agrees with it (not merely
-- that the frozen value is never replaced by a later report -- every
-- anchored report is checked for agreement, row-scoped to governed.trade
-- like its sibling inv.trade_owning_account_frozen, so it asserts nothing
-- about a trade_number the job does not claim, e.g. one held under either
-- open hole). A held
-- report (any of cdc_flag, t_st_id, t_tt_id outside its anchored vocabulary,
-- null-sensitive) is not evidence either way: it is excluded from this
-- comparison entirely. A trade whose earliest report or earliest
-- raw.trade_cdc report is held has no governed.trade row at all (see
-- inv.unknown_codes_held, inv.trade_held_first_report_unclaimed,
-- inv.every_received_trade_persisted). Zero rows means the invariant holds.

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
    SELECT t_id, t_tt_id
    FROM valid_cdc_rows
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
expected AS (
    SELECT
        t_id AS trade_number,
        t_tt_id AS expected_order_type
    FROM first_cdc_report
)
SELECT t.trade_number, t.order_type, e.expected_order_type, 'frozen_value_mismatch' AS problem
FROM governed.trade AS t
JOIN expected AS e ON e.trade_number = t.trade_number
WHERE t.order_type IS DISTINCT FROM e.expected_order_type

UNION ALL

SELECT vcr.t_id AS trade_number, vcr.t_tt_id AS order_type, e.expected_order_type,
       'anchored_report_disagrees' AS problem
FROM valid_cdc_rows AS vcr
JOIN expected AS e ON e.trade_number = vcr.t_id
JOIN governed.trade AS t ON t.trade_number = vcr.t_id
WHERE vcr.t_tt_id IS DISTINCT FROM e.expected_order_type;
