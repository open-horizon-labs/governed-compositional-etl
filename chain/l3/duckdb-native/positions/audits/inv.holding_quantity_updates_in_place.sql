-- inv.holding_quantity_updates_in_place: for any (original_trade_number,
-- current_trade_number) pair, a later raw.holding_history report of that same
-- pair with cdc_flag I or U replaces before_qty and after_qty with its newly
-- reported values on the same row; the pair itself is never replaced. A
-- cdc_flag D report is not a later report under this invariant
-- (L1.hole.deletions, not decided here). Checked by recomputing the latest
-- non-deleted report per pair (report_order descending; Batch1 rows carry no
-- cdc columns at all and precede all incremental rows, per sources-v1.json)
-- and diffing before_qty and after_qty against what governed.holding_change
-- actually persisted. Zero rows means the invariant holds.

WITH latest_report AS (
    SELECT hh_h_t_id, hh_t_id, hh_before_qty, hh_after_qty
    FROM raw.holding_history
    WHERE cdc_flag IS NULL OR cdc_flag IN ('I', 'U')
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY hh_h_t_id, hh_t_id
        ORDER BY (cdc_flag IS NULL) ASC, batch_date DESC, cdc_dsn DESC
    ) = 1
)
SELECT
    hc.original_trade_number,
    hc.current_trade_number
FROM governed.holding_change AS hc
JOIN latest_report AS lr
  ON lr.hh_h_t_id = hc.original_trade_number
 AND lr.hh_t_id = hc.current_trade_number
WHERE hc.before_qty IS DISTINCT FROM lr.hh_before_qty
   OR hc.after_qty IS DISTINCT FROM lr.hh_after_qty;
