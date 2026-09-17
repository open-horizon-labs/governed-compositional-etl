AUDIT (name "inv.every_received_trade_persisted");

-- For any trade_number that has at least one received report whose coded fields are all
-- anchored (cdc_flag, t_st_id, and t_tt_id for a raw.trade_cdc report; th_st_id for a
-- raw.trade_history report) and none of whose received reports carries cdc_flag D, exactly one
-- governed.trade row exists for that trade_number. A trade_number with any cdc_flag D report is
-- L1.hole.deletions' case and is not claimed by this invariant. A trade_number known only
-- through reports held under L1.unknown-codes -- none of its received reports has fully
-- anchored codes -- is not yet known to this job and is not claimed either; inv.unknown_codes_
-- held reports each such held report instead. raw.trade_history carries no cdc_flag column, so
-- a history report never carries D on its own.
WITH fully_anchored_trade_numbers AS (
  SELECT t_id AS trade_number
  FROM raw.trade_cdc
  WHERE cdc_flag IN ('I', 'U', 'D')
    AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
  UNION
  SELECT th_t_id AS trade_number
  FROM raw.trade_history
  WHERE th_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
),
-- IS DISTINCT FROM is null-safe: it keeps any row whose cdc_flag is absent in scope rather
-- than unknown; raw.trade_history contributes no rows here since it has no cdc_flag column.
cdc_flag_scope AS (
  SELECT
    t_id AS trade_number,
    BOOL_AND(cdc_flag IS DISTINCT FROM 'D') AS has_no_d_report
  FROM raw.trade_cdc
  GROUP BY t_id
),
in_scope_trade_numbers AS (
  SELECT DISTINCT f.trade_number
  FROM fully_anchored_trade_numbers AS f
  LEFT JOIN cdc_flag_scope AS s ON s.trade_number = f.trade_number
  WHERE COALESCE(s.has_no_d_report, TRUE)
)
SELECT
  i.trade_number
FROM in_scope_trade_numbers AS i
LEFT JOIN @this_model AS m ON m.trade_number = i.trade_number
GROUP BY i.trade_number
HAVING COUNT(m.trade_number) <> 1;
