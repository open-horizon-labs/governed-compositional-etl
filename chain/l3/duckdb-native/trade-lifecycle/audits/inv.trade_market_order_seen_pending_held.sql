-- inv.trade_market_order_seen_pending_held: for any trade_number whose
-- order_type is TMB or TMS (a market order) and whose first-encountered
-- report -- across both anchored sources -- carries status PNDG, this
-- invariant reports the trade as held for review under
-- L1.hole.market-order-seen-pending, naming the trade_number and its
-- first-encountered status; first_seen_late for such a trade is null, not
-- true or false (checked by inv.trade_first_seen_late_defined_or_held).
-- Recomputed independently from raw.trade_cdc and raw.trade_history
-- (mirroring trade.sql's own first_report derivation). Zero rows means no
-- such trade exists in this run.

WITH valid_cdc_rows AS (
    SELECT *
    FROM raw.trade_cdc
    WHERE cdc_flag IN ('I', 'U', 'D')
      AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
),
first_cdc_report AS (
    SELECT t_id, t_dts, t_st_id, t_tt_id
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
)
SELECT trade_number, order_type, first_status
FROM first_report
WHERE order_type IN ('TMB', 'TMS')
  AND first_status = 'PNDG';
