AUDIT (name "inv.unknown_codes_held");

-- L1.unknown-codes: a raw.holding_history row whose cdc_flag is outside the anchored
-- vocabulary (I, U, D, or null for a historical-load row with no cdc columns of its own) is
-- held for review, never interpreted, defaulted, or dropped silently; this audit names each
-- such row directly against the source. models/holding_change.sql already excludes an unknown
-- cdc_flag from latest_change's candidate set (its WHERE clause names only null, I, and U, with
-- no ELSE), so a report held under this invariant contributes no derived fact.
SELECT
  hh_h_t_id AS original_trade_number,
  hh_t_id AS current_trade_number,
  batch_date,
  cdc_dsn,
  cdc_flag AS code
FROM raw.holding_history
WHERE cdc_flag IS NOT NULL
  AND cdc_flag NOT IN ('I', 'U', 'D');
