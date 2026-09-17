MODEL (
  name governed.holding_change,
  kind CUSTOM (
    materialization 'governed_merge',
    materialization_properties (
      'unique_key' = 'original_trade_number,current_trade_number',
      'mutable_columns' = 'before_qty,after_qty,quantity_change',
      'frozen_columns' = 'owning_account_number,owning_account_effective_from,owning_customer_number,owning_customer_effective_from'
    )
  ),
  dialect duckdb,
  columns (
    original_trade_number BIGINT,
    current_trade_number BIGINT,
    owning_account_number BIGINT,
    owning_account_effective_from TIMESTAMP,
    owning_customer_number BIGINT,
    owning_customer_effective_from TIMESTAMP,
    before_qty BIGINT,
    after_qty BIGINT,
    quantity_change BIGINT
  ),
  audits (
    "inv.holding_change_ownership_frozen",
    "inv.holding_quantity_updates_in_place",
    "inv.holding_quantity_change_is_difference",
    "inv.holding_change_ownership_present",
    "inv.holding_change_current_trade_known",
    "inv.holding_quantities_present"
  ),
  depends_on (governed.trade)
);

-- logical.holding_change: one row per (original_trade_number, current_trade_number) pair,
-- incremental_by_identity. The governed_merge materialization inserts a new pair with every
-- column below and, on match, updates only the mutable_columns; the frozen_columns below are
-- therefore only ever taken at insert time from the pair's first-encountered report, never
-- replaced by a later run recomputing them.
--
-- original_trade_number/current_trade_number: handoff.raw.holding_history.hh_h_t_id/hh_t_id->
-- logical.holding_change.original_trade_number/current_trade_number.
--
-- before_qty/after_qty: handoff.raw.holding_history.hh_before_qty/hh_after_qty->
-- logical.holding_change.before_qty/after_qty, selector latest_change (the latest report of the
-- pair by report_order: batch_date, cdc_dsn; historical rows carry no cdc columns of their own
-- -- cdc_flag and cdc_dsn both NULL -- and precede all incremental rows regardless of batch_date,
-- per sources-v1.json's report_order.applies_to). A cdc_flag D report is not a later report
-- under inv.holding_quantity_updates_in_place, so it is excluded here; what D means otherwise is
-- L1.hole.deletions, not decided by this job. Unlike raw.trade_cdc, raw.holding_history's own
-- historical rows are not synthesized to cdc_flag 'I': they are NULL and must be kept, not
-- filtered out by a cdc_flag IN ('I', 'U') test.
--
-- owning_account_number/owning_account_effective_from/owning_customer_number/
-- owning_customer_effective_from: handoff.logical.trade.owning_account_number/
-- owning_account_effective_from/owning_customer_number/owning_customer_effective_from->
-- logical.holding_change's same-named attributes, selector first_encounter_only. These are
-- copied straight from trade-lifecycle's already-frozen governed.trade for this pair's
-- current_trade_number -- never re-derived against governed.account or governed.customer,
-- which L1.holdings-follow-trade forbids -- and are stable at any read since governed.trade's
-- own ownership reference never changes after its own first encounter.
--
-- quantity_change: computed_within_entity, after_qty minus before_qty.
WITH latest_change AS (
  SELECT
    hh_h_t_id AS original_trade_number,
    hh_t_id AS current_trade_number,
    hh_before_qty AS before_qty,
    hh_after_qty AS after_qty
  FROM raw.holding_history
  WHERE cdc_flag IS NULL OR cdc_flag IN ('I', 'U')
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY hh_h_t_id, hh_t_id
    ORDER BY (cdc_flag IS NOT NULL) DESC, batch_date DESC, cdc_dsn DESC
  ) = 1
)
SELECT
  lc.original_trade_number,
  lc.current_trade_number,
  t.owning_account_number,
  t.owning_account_effective_from,
  t.owning_customer_number,
  t.owning_customer_effective_from,
  lc.before_qty,
  lc.after_qty,
  lc.after_qty - lc.before_qty AS quantity_change
FROM latest_change AS lc
JOIN governed.trade AS t ON t.trade_number = lc.current_trade_number;
