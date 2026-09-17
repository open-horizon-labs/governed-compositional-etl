-- inv.trade_order_type_frozen: for any trade_number, order_type equals
-- t_tt_id on the trade's first-encountered raw.trade_cdc report (a trade
-- whose only raw.trade_cdc report is held under L1.unknown-codes -- any of
-- cdc_flag, t_st_id, t_tt_id outside its anchored vocabulary -- has no
-- governed.trade row at all; see inv.unknown_codes_held and
-- inv.every_received_trade_persisted), and is never replaced by a later
-- report's t_tt_id. Zero rows means the invariant holds.

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
SELECT t.trade_number, t.order_type, e.expected_order_type
FROM governed.trade AS t
JOIN expected AS e ON e.trade_number = t.trade_number
WHERE t.order_type IS DISTINCT FROM e.expected_order_type;
