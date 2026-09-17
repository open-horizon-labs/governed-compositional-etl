-- inv.eligible_holding_report_persisted: every (original_trade_number,
-- current_trade_number) pair reported by raw.holding_history, none of whose
-- reports carries cdc_flag D, whose current_trade_number resolves to a
-- governed.trade row carrying owning_account_number,
-- owning_account_effective_from, owning_customer_number, and
-- owning_customer_effective_from all non-null, has exactly one
-- governed.holding_change row. A pair with any D report is L1.hole.deletions'
-- case and is not claimed by this invariant.
--
-- The D test is whole-pair abstention, not a per-row filter: a pair is
-- excluded from the expected set the moment any one of its reports carries
-- cdc_flag D, via BOOL_AND(cdc_flag IS DISTINCT FROM 'D') grouped by
-- (hh_h_t_id, hh_t_id) -- a mixed I+D (or historical+D) pair drops out
-- entirely, unlike holding_change.sql's own per-row candidate filter, which
-- only ever discards the D rows themselves while still projecting the pair
-- from its surviving I/U/historical reports.
--
-- Zero rows means the invariant holds (every eligible pair has exactly one
-- persisted row; this audit reports the pairs with zero or with more than one).

WITH eligible_pairs AS (
    SELECT hh_h_t_id, hh_t_id
    FROM raw.holding_history
    GROUP BY hh_h_t_id, hh_t_id
    HAVING BOOL_AND(cdc_flag IS DISTINCT FROM 'D')
),
eligible_pinned_pairs AS (
    SELECT
        ep.hh_h_t_id AS original_trade_number,
        ep.hh_t_id AS current_trade_number
    FROM eligible_pairs AS ep
    JOIN governed.trade AS t
      ON t.trade_number = ep.hh_t_id
    WHERE t.owning_account_number IS NOT NULL
      AND t.owning_account_effective_from IS NOT NULL
      AND t.owning_customer_number IS NOT NULL
      AND t.owning_customer_effective_from IS NOT NULL
)
SELECT
    epp.original_trade_number,
    epp.current_trade_number,
    COUNT(hc.original_trade_number) AS holding_change_row_count
FROM eligible_pinned_pairs AS epp
LEFT JOIN governed.holding_change AS hc
  ON hc.original_trade_number = epp.original_trade_number
 AND hc.current_trade_number = epp.current_trade_number
GROUP BY epp.original_trade_number, epp.current_trade_number
HAVING COUNT(hc.original_trade_number) <> 1;
