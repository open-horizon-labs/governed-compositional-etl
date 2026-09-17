AUDIT (name "inv.holding_quantity_updates_in_place");

-- Clause 1: for any (original_trade_number, current_trade_number) pair, a later
-- raw.holding_history report of that same pair with cdc_flag I or U replaces before_qty and
-- after_qty with its newly reported values on the same row; the pair itself is never replaced.
-- Clause 2: a persisted pair with no surviving I, U, or historical report -- every report of the
-- pair is now cdc_flag D, or no report of the pair remains at all -- is also a violation: a
-- persisted row must still be backed by at least one report, not merely by history.
--
-- A cdc_flag D report is not a later report under this invariant. Historical rows carry no cdc
-- columns of their own (cdc_flag and cdc_dsn both NULL) and precede all incremental rows
-- regardless of batch_date, per sources-v1.json's report_order.applies_to; unlike raw.trade_cdc,
-- they are not synthesized to cdc_flag 'I' and must not be filtered out by a
-- cdc_flag IN ('I', 'U') test.
--
-- The latest report is restated here independently of the model's own QUALIFY/ROW_NUMBER CTE, as
-- an anti-join: a report is latest exactly when no strictly-later, non-D report of the same pair
-- exists. Several historical reports of the same pair (both cdc_flag and cdc_dsn null on every
-- one) would tie under this ordering and under the model's own; this job does not resolve that
-- tie (hole.batch_identity).
WITH candidates AS (
  SELECT
    hh_h_t_id AS original_trade_number,
    hh_t_id AS current_trade_number,
    hh_before_qty AS before_qty,
    hh_after_qty AS after_qty,
    cdc_flag,
    batch_date,
    cdc_dsn
  FROM raw.holding_history
  WHERE cdc_flag IS DISTINCT FROM 'D'
),
latest AS (
  SELECT
    c1.original_trade_number,
    c1.current_trade_number,
    c1.before_qty,
    c1.after_qty
  FROM candidates AS c1
  WHERE NOT EXISTS (
    SELECT 1
    FROM candidates AS c2
    WHERE c2.original_trade_number = c1.original_trade_number
      AND c2.current_trade_number = c1.current_trade_number
      AND (
        -- c2 is an incremental report and c1 is historical: c2 is always later.
        (c1.cdc_flag IS NULL AND c2.cdc_flag IS NOT NULL)
        OR (
          -- c1 and c2 are the same kind (both historical or both incremental): compare by
          -- report_order.
          (c1.cdc_flag IS NULL) = (c2.cdc_flag IS NULL)
          AND (
            c2.batch_date > c1.batch_date
            OR (c2.batch_date = c1.batch_date AND c2.cdc_dsn > c1.cdc_dsn)
          )
        )
      )
  )
)
SELECT
  m.original_trade_number,
  m.current_trade_number
FROM @this_model AS m
LEFT JOIN latest AS l
  ON l.original_trade_number = m.original_trade_number
 AND l.current_trade_number = m.current_trade_number
WHERE l.original_trade_number IS NULL
   OR m.before_qty IS DISTINCT FROM l.before_qty
   OR m.after_qty IS DISTINCT FROM l.after_qty;
