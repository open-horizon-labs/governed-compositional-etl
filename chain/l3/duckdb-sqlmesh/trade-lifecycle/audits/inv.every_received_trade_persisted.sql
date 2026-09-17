AUDIT (name "inv.every_received_trade_persisted");

-- For any trade_number that has at least one received raw.trade_cdc report whose coded fields
-- (cdc_flag, t_st_id, t_tt_id) are all anchored and that does not carry cdc_flag D, and none of
-- whose placement-fixing facts (placement, owning account, or order type) would come from a
-- held report, exactly one governed.trade row exists for that trade_number. A trade_number
-- with any cdc_flag D report is L1.hole.deletions' case and is not claimed here. A trade_number
-- known only through reports held under L1.unknown-codes, or known only through
-- raw.trade_history rows (no identity handoff of its own), is not yet known to this job and is
-- not claimed either; inv.unknown_codes_held reports each held report instead. A trade_number
-- any of whose placement-fixing facts would come from a held report -- the earliest report of
-- either anchored source, or the earliest raw.trade_cdc report specifically -- is likewise not
-- yet claimed, pending L1.hole.held-first-report-placement; inv.trade_held_first_report_unclaimed
-- makes this the audit's own checkable claim.
WITH fully_anchored_trade_numbers AS (
  SELECT DISTINCT t_id AS trade_number
  FROM raw.trade_cdc
  WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
    AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
),
-- IS DISTINCT FROM is null-safe: it keeps any row whose cdc_flag is absent in scope rather
-- than unknown.
cdc_flag_scope AS (
  SELECT
    t_id AS trade_number,
    BOOL_AND(cdc_flag IS DISTINCT FROM 'D') AS has_no_d_report
  FROM raw.trade_cdc
  GROUP BY t_id
),
earliest_history_any AS (
  SELECT
    th_t_id AS trade_number,
    th_st_id AS status_at_first_report
  FROM raw.trade_history
  QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts ASC) = 1
),
earliest_cdc_any AS (
  SELECT
    t_id AS trade_number,
    cdc_flag,
    t_st_id,
    t_tt_id
  FROM raw.trade_cdc
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
earliest_report_held AS (
  SELECT trade_number
  FROM earliest_history_any
  WHERE status_at_first_report IS NULL
     OR status_at_first_report NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  UNION
  SELECT trade_number
  FROM earliest_cdc_any
  WHERE cdc_flag IS NULL OR cdc_flag NOT IN ('I', 'U', 'D')
     OR t_st_id IS NULL OR t_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
     OR t_tt_id IS NULL OR t_tt_id NOT IN ('TLB', 'TLS', 'TMB', 'TMS')
),
in_scope_trade_numbers AS (
  SELECT f.trade_number
  FROM fully_anchored_trade_numbers AS f
  LEFT JOIN cdc_flag_scope AS s ON s.trade_number = f.trade_number
  LEFT JOIN earliest_report_held AS held ON held.trade_number = f.trade_number
  WHERE COALESCE(s.has_no_d_report, TRUE)
    AND held.trade_number IS NULL
)
SELECT
  i.trade_number
FROM in_scope_trade_numbers AS i
LEFT JOIN @this_model AS m ON m.trade_number = i.trade_number
GROUP BY i.trade_number
HAVING COUNT(m.trade_number) <> 1;
