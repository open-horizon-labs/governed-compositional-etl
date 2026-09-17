-- inv.trade_outcome_updates_in_place: for any trade_number, a later
-- raw.trade_cdc report of that same trade with cdc_flag I or U replaces
-- status, executed_price, fees, commission, tax, and quantity with its newly
-- reported values on the same row; trade_number itself is never replaced. A
-- cdc_flag D report is not a later report under this invariant (L1.hole.deletions,
-- not decided here). Per L1.unknown-codes and the status handoff's own
-- parallel_assumption ("a report held under L1.unknown-codes -- an
-- unanchored cdc_flag, or, for this field, an unanchored t_st_id -- is not a
-- later report for this handoff's latest_change selection; status stands as
-- it last stood"), a report whose t_st_id is outside the anchored vocabulary
-- is likewise not a later report here: nothing is derived from it. Checked
-- by recomputing the latest I/U, anchored-status report per trade
-- (report_order descending) and diffing the six outcome columns against what
-- governed.trade actually persisted. Zero rows means the invariant holds.

WITH latest_outcome AS (
    SELECT t_id, t_st_id, t_trade_price, t_chrg, t_comm, t_tax, t_qty
    FROM raw.trade_cdc
    WHERE cdc_flag IN ('I', 'U')
      AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date DESC, cdc_dsn DESC) = 1
)
SELECT t.trade_number
FROM governed.trade AS t
JOIN latest_outcome AS lo ON lo.t_id = t.trade_number
WHERE t.status IS DISTINCT FROM lo.t_st_id
   OR t.executed_price IS DISTINCT FROM lo.t_trade_price
   OR t.fees IS DISTINCT FROM lo.t_chrg
   OR t.commission IS DISTINCT FROM lo.t_comm
   OR t.tax IS DISTINCT FROM lo.t_tax
   OR t.quantity IS DISTINCT FROM lo.t_qty;
