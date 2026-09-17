-- inv.holding_quantity_updates_in_place: for any (original_trade_number,
-- current_trade_number) pair, a later raw.holding_history report of that same
-- pair with cdc_flag I or U replaces before_qty and after_qty with its newly
-- reported values on the same row; the pair itself is never replaced. A
-- cdc_flag D report is not a later report under this invariant
-- (L1.hole.deletions, not decided here). Two clauses, both checked:
--   1. a persisted row's before_qty/after_qty must match some eligible report
--      of the pair that nothing else eligible for that pair dominates (is
--      strictly later than, per report_order: any incremental report beats
--      any historical one; among reports of the same kind, greater
--      (batch_date, cdc_dsn) wins).
--   2. a persisted pair with no surviving eligible report at all (every report
--      of the pair is now D-flagged, or none remain) is itself a violation --
--      the row should not still be there with nothing to justify it.
-- Restated independently of the projection's own ROW_NUMBER/QUALIFY selection:
-- here "the latest report" is expressed as "a report nothing else dominates",
-- via correlated NOT EXISTS, rather than by reusing that window-function CTE.
-- Note (L1.hole.batch-identity, not resolved here): several historical reports
-- of the same pair would tie under this order (null cdc_dsn, and possibly the
-- same batch_date), since ordering rests on file production order, not on a
-- report carrying which file delivered it; a persisted row matching any one of
-- several tied, undominated candidates is not treated as a violation.
-- Zero rows means the invariant holds.

WITH eligible AS (
    SELECT hh_h_t_id, hh_t_id, hh_before_qty, hh_after_qty, cdc_flag, batch_date, cdc_dsn
    FROM raw.holding_history
    WHERE cdc_flag IS NULL OR cdc_flag IN ('I', 'U')
),
undominated AS (
    -- An eligible report r1 with no other eligible report r2 of the same pair
    -- strictly later than it: any incremental r2 beats a historical r1; among
    -- reports of the same kind (both historical or both incremental), a
    -- greater (batch_date, cdc_dsn) beats a lesser one.
    SELECT r1.*
    FROM eligible AS r1
    WHERE NOT EXISTS (
        SELECT 1
        FROM eligible AS r2
        WHERE r2.hh_h_t_id = r1.hh_h_t_id
          AND r2.hh_t_id = r1.hh_t_id
          AND (
                (r2.cdc_flag IS NOT NULL AND r1.cdc_flag IS NULL)
             OR (
                  (r2.cdc_flag IS NOT NULL) = (r1.cdc_flag IS NOT NULL)
                  AND (r2.batch_date, COALESCE(r2.cdc_dsn, -1)) > (r1.batch_date, COALESCE(r1.cdc_dsn, -1))
                )
          )
    )
),
clause_1_stale AS (
    SELECT hc.original_trade_number, hc.current_trade_number
    FROM governed.holding_change AS hc
    WHERE EXISTS (
            SELECT 1 FROM undominated AS u
            WHERE u.hh_h_t_id = hc.original_trade_number AND u.hh_t_id = hc.current_trade_number
          )
      AND NOT EXISTS (
            SELECT 1 FROM undominated AS u
            WHERE u.hh_h_t_id = hc.original_trade_number
              AND u.hh_t_id = hc.current_trade_number
              AND u.hh_before_qty IS NOT DISTINCT FROM hc.before_qty
              AND u.hh_after_qty IS NOT DISTINCT FROM hc.after_qty
          )
),
clause_2_orphaned AS (
    SELECT hc.original_trade_number, hc.current_trade_number
    FROM governed.holding_change AS hc
    WHERE NOT EXISTS (
        SELECT 1 FROM eligible AS e
        WHERE e.hh_h_t_id = hc.original_trade_number
          AND e.hh_t_id = hc.current_trade_number
    )
)
SELECT * FROM clause_1_stale
UNION
SELECT * FROM clause_2_orphaned;
