AUDIT (name "inv.unknown_codes_held");

-- L1.unknown-codes: a raw.trade_cdc row whose cdc_flag, t_st_id, or t_tt_id is outside its
-- field's anchored vocabulary, or a raw.trade_history row whose th_st_id is outside the
-- anchored status vocabulary, is held for review and never interpreted, defaulted, or dropped.
-- This audit names each held row directly against its source, independent of whether the model
-- used it: models/trade.sql already excludes an unknown cdc_flag from every CTE that
-- establishes identity or an outcome, and leaves first_seen_late NULL rather than ranking an
-- unknown status or order type.
SELECT
  t_id AS trade_number,
  batch_date,
  cdc_dsn,
  'cdc_flag' AS field,
  cdc_flag AS code
FROM raw.trade_cdc
WHERE cdc_flag NOT IN ('I', 'U', 'D')
UNION ALL
SELECT
  t_id AS trade_number,
  batch_date,
  cdc_dsn,
  't_st_id' AS field,
  t_st_id AS code
FROM raw.trade_cdc
WHERE t_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
UNION ALL
SELECT
  t_id AS trade_number,
  batch_date,
  cdc_dsn,
  't_tt_id' AS field,
  t_tt_id AS code
FROM raw.trade_cdc
WHERE t_tt_id NOT IN ('TLB', 'TLS', 'TMB', 'TMS')
UNION ALL
SELECT
  th_t_id AS trade_number,
  batch_date,
  CAST(NULL AS BIGINT) AS cdc_dsn,
  'th_st_id' AS field,
  th_st_id AS code
FROM raw.trade_history
WHERE th_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL');
