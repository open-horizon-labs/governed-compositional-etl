AUDIT (name "inv.holding_quantity_updates_in_place");

-- Clause 1 (tolerant): a persisted (original_trade_number, current_trade_number) pair is a
-- violation only when at least one undominated candidate report of the pair exists, but none of
-- the undominated candidates matches the pair's persisted before_qty/after_qty. "Undominated"
-- means no strictly-later candidate of the same pair exists under report_order; when several
-- candidates tie (hole.batch_identity's case: several historical reports of the same pair, both
-- cdc_flag and cdc_dsn null on every one, so none strictly dominates another), every tied
-- candidate is undominated, and this audit accepts any of them matching -- it does not resolve
-- the tie, it only requires the persisted row to agree with something the tie leaves standing.
--
-- Clause 2 (kept separate): a persisted pair with no candidate report at all -- every report of
-- the pair is cdc_flag D, or no report of the pair remains -- is a violation regardless of
-- clause 1: a persisted row must still be backed by at least one candidate report, not merely by
-- history. This is checked independently of clause 1's EXISTS/NOT EXISTS pair, which is silent
-- (neither true) when there are no candidates at all.
--
-- The candidate set uses the model's own filter (cdc_flag IS NULL OR cdc_flag IN ('I', 'U')):
-- historical rows carry no cdc columns of their own (cdc_flag and cdc_dsn both NULL) and are not
-- synthesized to cdc_flag 'I' the way raw.trade_cdc's are, so they must be kept explicitly rather
-- than folded into an IN ('I', 'U') test. report_order compares batch_date, then cdc_dsn
-- COALESCEd to a value lower than any real dsn, so two same-batch candidates that both carry a
-- null cdc_dsn (or one that does) tie instead of comparing null as neither greater nor less.
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
  WHERE cdc_flag IS NULL OR cdc_flag IN ('I', 'U')
),
undominated AS (
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
          -- report_order, cdc_dsn compared null-safe so a null dsn never spuriously wins or
          -- loses against a real one.
          (c1.cdc_flag IS NULL) = (c2.cdc_flag IS NULL)
          AND (
            c2.batch_date > c1.batch_date
            OR (
              c2.batch_date = c1.batch_date
              AND COALESCE(c2.cdc_dsn, -1) > COALESCE(c1.cdc_dsn, -1)
            )
          )
        )
      )
  )
)
SELECT
  m.original_trade_number,
  m.current_trade_number
FROM @this_model AS m
WHERE NOT EXISTS (
  SELECT 1
  FROM candidates AS c
  WHERE c.original_trade_number = m.original_trade_number
    AND c.current_trade_number = m.current_trade_number
)
OR (
  EXISTS (
    SELECT 1
    FROM undominated AS u
    WHERE u.original_trade_number = m.original_trade_number
      AND u.current_trade_number = m.current_trade_number
  )
  AND NOT EXISTS (
    SELECT 1
    FROM undominated AS u
    WHERE u.original_trade_number = m.original_trade_number
      AND u.current_trade_number = m.current_trade_number
      AND u.before_qty IS NOT DISTINCT FROM m.before_qty
      AND u.after_qty IS NOT DISTINCT FROM m.after_qty
  )
);
