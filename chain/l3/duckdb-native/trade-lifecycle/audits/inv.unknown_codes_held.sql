-- inv.unknown_codes_held: for every raw.trade_cdc row this job consumes,
-- cdc_flag is one of {I, U, D}, t_st_id is one of {PNDG, SBMT, CMPT, CNCL},
-- and t_tt_id is one of {TLB, TLS, TMB, TMS}; for every raw.trade_history
-- row this job consumes, th_st_id is one of {PNDG, SBMT, CMPT, CNCL}. A row
-- carrying a value outside its field's anchored vocabulary is a violation
-- of this invariant, naming the record and the code; it is held for
-- review, not interpreted, defaulted, or dropped. Null-sensitive: a null
-- coded field (raw.trade_cdc always carries a non-null cdc_flag, per the
-- loader's Batch1 normalization to I/0) is itself not a named code, not a
-- pass. Zero rows means the invariant holds.

SELECT
    t_id AS trade_number,
    cdc_flag,
    NULL AS th_dts,
    t_st_id,
    t_tt_id,
    'raw.trade_cdc' AS source
FROM raw.trade_cdc
WHERE cdc_flag IS NULL OR cdc_flag NOT IN ('I', 'U', 'D')
   OR t_st_id IS NULL OR t_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
   OR t_tt_id IS NULL OR t_tt_id NOT IN ('TLB', 'TLS', 'TMB', 'TMS')

UNION ALL

SELECT
    th_t_id AS trade_number,
    NULL AS cdc_flag,
    th_dts,
    th_st_id AS t_st_id,
    NULL AS t_tt_id,
    'raw.trade_history' AS source
FROM raw.trade_history
WHERE th_st_id IS NULL OR th_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL');
