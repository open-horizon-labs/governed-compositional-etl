MODEL (
  name governed.trade,
  kind CUSTOM (
    materialization 'governed_merge',
    materialization_properties (
      'unique_key' = 'trade_number',
      'mutable_columns' = 'status,executed_price,fees,commission,tax,quantity',
      'frozen_columns' = 'owning_account_number,placed_at,owning_account_effective_from,owning_customer_number,owning_customer_effective_from,first_seen_late'
    )
  ),
  dialect duckdb,
  columns (
    trade_number BIGINT,
    owning_account_number BIGINT,
    placed_at TIMESTAMP,
    owning_account_effective_from TIMESTAMP,
    owning_customer_number BIGINT,
    owning_customer_effective_from TIMESTAMP,
    first_seen_late BOOLEAN,
    status VARCHAR,
    executed_price DECIMAL(8, 2),
    fees DECIMAL(10, 2),
    commission DECIMAL(10, 2),
    tax DECIMAL(10, 2),
    quantity BIGINT
  ),
  audits (
    "inv.trade_owning_account_frozen",
    "inv.trade_placement_reference_frozen",
    "inv.trade_first_seen_late_matches_status_order",
    "inv.trade_placed_at_matches_earliest_report",
    "inv.trade_outcome_updates_in_place",
    "inv.trade_ownership_provenance_reachable"
  ),
  depends_on (governed.account, governed.customer)
);

-- logical.trade: one row per trade_number, incremental_by_identity. The governed_merge
-- materialization inserts a new trade with every column below and, on match, updates only
-- the mutable_columns; the frozen columns below are therefore only ever taken at insert time
-- from a trade's first-encountered report, never replaced by a later run recomputing them.
--
-- owning_account_number is still, and only, handoff.raw.trade_cdc.t_ca_id->
-- logical.trade.owning_account_number: raw.trade_history carries no account field, so this
-- is always the first-encountered raw.trade_cdc row's t_ca_id regardless of which anchored
-- source supplies placed_at.
WITH first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_dts AS placed_at,
    t_ca_id AS owning_account_number,
    t_st_id AS status_at_first_report
  FROM raw.trade_cdc
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date ASC, cdc_dsn ASC) = 1
),
-- For a historical-load trade, trade_code_meanings.report_order states its earliest held
-- report is its earliest raw.trade_history row (th_dts), not its raw.trade_cdc snapshot row.
first_history_report AS (
  SELECT
    th_t_id AS trade_number,
    th_dts AS placed_at,
    th_st_id AS status_at_first_report
  FROM raw.trade_history
  QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts ASC) = 1
),
-- handoff.raw.trade_history.th_dts->logical.trade.placed_at (preferred where a history row
-- exists) and handoff.raw.trade_cdc.t_dts->logical.trade.placed_at (otherwise), both selector
-- first_encounter_only. logical.trade.first_seen_late (computed_within_entity) compares that
-- same first report's own status against the anchored status_order (PNDG is the lifecycle's
-- first status).
first_report AS (
  SELECT
    c.trade_number,
    c.owning_account_number,
    COALESCE(h.placed_at, c.placed_at) AS placed_at,
    COALESCE(h.status_at_first_report, c.status_at_first_report) <> 'PNDG' AS first_seen_late
  FROM first_cdc_report AS c
  LEFT JOIN first_history_report AS h ON h.trade_number = c.trade_number
),
-- handoff.logical.account.effective_from->logical.trade.owning_account_effective_from and
-- handoff.logical.account.owning_customer_number->logical.trade.owning_customer_number,
-- selector as_of_event_time: the governed.account statement of owning_account_number whose
-- effective_from is the latest at or before placed_at.
account_asof AS (
  SELECT
    f.trade_number,
    a.effective_from AS owning_account_effective_from,
    a.owning_customer_number
  FROM first_report AS f
  JOIN governed.account AS a
    ON a.account_number = f.owning_account_number
   AND a.effective_from <= f.placed_at
  QUALIFY ROW_NUMBER() OVER (PARTITION BY f.trade_number ORDER BY a.effective_from DESC) = 1
),
-- handoff.logical.customer.effective_from->logical.trade.owning_customer_effective_from,
-- selector as_of_event_time: the governed.customer statement of the customer named by the
-- pinned account statement (aa.owning_customer_number) whose effective_from is the latest at
-- or before placed_at.
customer_asof AS (
  SELECT
    f.trade_number,
    c.effective_from AS owning_customer_effective_from
  FROM first_report AS f
  JOIN account_asof AS aa ON aa.trade_number = f.trade_number
  JOIN governed.customer AS c
    ON c.customer_number = aa.owning_customer_number
   AND c.effective_from <= f.placed_at
  QUALIFY ROW_NUMBER() OVER (PARTITION BY f.trade_number ORDER BY c.effective_from DESC) = 1
),
-- mutable outcome facts: selector latest_change from the latest I- or U-flagged report
-- (handoff.raw.trade_cdc.t_st_id/t_trade_price/t_chrg/t_comm/t_tax/t_qty ->
-- logical.trade.status/executed_price/fees/commission/tax/quantity). A D-flagged report is
-- not a later report under inv.trade_outcome_updates_in_place, so it is excluded here.
latest_change AS (
  SELECT
    t_id AS trade_number,
    t_st_id AS status,
    t_trade_price AS executed_price,
    t_chrg AS fees,
    t_comm AS commission,
    t_tax AS tax,
    t_qty AS quantity
  FROM raw.trade_cdc
  WHERE cdc_flag IN ('I', 'U')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date DESC, cdc_dsn DESC) = 1
)
SELECT
  f.trade_number,
  f.owning_account_number,
  f.placed_at,
  aa.owning_account_effective_from,
  aa.owning_customer_number,
  ca.owning_customer_effective_from,
  f.first_seen_late,
  m.status,
  m.executed_price,
  m.fees,
  m.commission,
  m.tax,
  m.quantity
FROM first_report AS f
JOIN account_asof AS aa ON aa.trade_number = f.trade_number
JOIN customer_asof AS ca ON ca.trade_number = f.trade_number
JOIN latest_change AS m ON m.trade_number = f.trade_number;
