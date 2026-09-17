-- inv.unknown_codes_held: every raw.holding_history row this job consumes
-- carries a cdc_flag value the anchors name (I, U, or D) or is a historical
-- row carrying no cdc_flag at all (cdc_flag IS NULL); a row carrying any
-- other cdc_flag value is held for review and reported here as a violation,
-- naming the row and its code, never interpreted, defaulted, or dropped
-- silently. Zero rows means the invariant holds.

SELECT
    hh_h_t_id AS original_trade_number,
    hh_t_id AS current_trade_number,
    batch_date,
    cdc_dsn,
    cdc_flag
FROM raw.holding_history
WHERE cdc_flag IS NOT NULL
  AND cdc_flag NOT IN ('I', 'U', 'D');
