MODEL (
  name governed.trade,
  kind CUSTOM (
    materialization 'governed_merge',
    materialization_properties (
      'unique_key' = 'trade_number',
      'mutable_columns' = 'status,executed_price,fees,commission,tax,quantity',
      'frozen_columns' = 'owning_account_number,placed_at,owning_account_effective_from,owning_customer_number,owning_customer_effective_from,first_seen_late,order_type'
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
    order_type VARCHAR,
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
    "inv.trade_order_type_frozen",
    "inv.trade_first_seen_late_matches_status_order",
    "inv.trade_first_seen_late_defined_or_held",
    "inv.trade_market_order_seen_pending_held",
    "inv.trade_placed_at_matches_earliest_report",
    "inv.trade_outcome_updates_in_place",
    "inv.trade_ownership_provenance_reachable",
    "inv.trade_ownership_pin_present",
    "inv.every_received_trade_persisted",
    "inv.unknown_codes_held"
  ),
  depends_on (governed.account, governed.customer)
);

-- logical.trade: one row per trade_number, incremental_by_identity. The governed_merge
-- materialization inserts a new trade with every column below and, on match, updates only
-- the mutable_columns; the frozen columns below are therefore only ever taken at insert time
-- from a trade's first-encountered report, never replaced by a later run recomputing them.
--
-- L1.unknown-codes (a report is held as a whole: one unknown code holds the record): every
-- CTE below that reads raw.trade_cdc keeps only rows whose cdc_flag, t_st_id, and t_tt_id are
-- all anchored (null-sensitive: IS NULL OR NOT IN counts as unanchored), and every CTE that
-- reads raw.trade_history keeps only rows whose th_st_id is anchored. A held row supplies no
-- fact anywhere -- not to identity, not to placement, not to outcome (inv.unknown_codes_held
-- reports it directly against the source).
--
-- L1.hole.held-first-report-placement: a trade whose earliest report (across both anchored
-- sources, per trade_code_meanings.report_order) is itself held is unclaimed by this job even
-- when a later report is anchored: no placed_at, no row. earliest_report_held below computes
-- exactly that set and the final SELECT excludes it.
WITH history_presence AS (
  SELECT DISTINCT th_t_id AS trade_number
  FROM raw.trade_history
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
-- A trade with a raw.trade_history row is held at first encounter iff that earliest history
-- row's th_st_id is unanchored (per report_order, its history row is the earliest report, not
-- its cdc snapshot). A trade with no raw.trade_history row is held at first encounter iff its
-- single earliest raw.trade_cdc row is not fully anchored on all three coded fields.
earliest_report_held AS (
  SELECT trade_number
  FROM earliest_history_any
  WHERE status_at_first_report IS NULL
     OR status_at_first_report NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  UNION
  SELECT e.trade_number
  FROM earliest_cdc_any AS e
  LEFT JOIN history_presence AS h ON h.trade_number = e.trade_number
  WHERE h.trade_number IS NULL
    AND (
      e.cdc_flag IS NULL OR e.cdc_flag NOT IN ('I', 'U', 'D')
      OR e.t_st_id IS NULL OR e.t_st_id NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      OR e.t_tt_id IS NULL OR e.t_tt_id NOT IN ('TLB', 'TLS', 'TMB', 'TMS')
    )
),
-- owning_account_number is still, and only, handoff.raw.trade_cdc.t_ca_id->
-- logical.trade.owning_account_number: raw.trade_history carries no account field, so this
-- is always the earliest fully-anchored raw.trade_cdc row's t_ca_id regardless of which
-- anchored source supplies placed_at.
first_cdc_report AS (
  SELECT
    t_id AS trade_number,
    t_dts AS placed_at,
    t_ca_id AS owning_account_number,
    t_tt_id AS order_type,
    t_st_id AS status_at_first_report
  FROM raw.trade_cdc
  WHERE cdc_flag IS NOT NULL AND cdc_flag IN ('I', 'U', 'D')
    AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
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
  WHERE th_st_id IS NOT NULL AND th_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts ASC) = 1
),
-- handoff.raw.trade_history.th_dts->logical.trade.placed_at (preferred where an anchored
-- history row exists) and handoff.raw.trade_cdc.t_dts->logical.trade.placed_at (otherwise),
-- both selector first_encounter_only. handoff.raw.trade_cdc.t_tt_id->logical.trade.order_type,
-- selector first_encounter_only: raw.trade_history carries no order-type field, so order_type
-- is always the earliest fully-anchored raw.trade_cdc row's t_tt_id, mirroring
-- owning_account_number. logical.trade.first_seen_late (computed_within_entity) compares that
-- same first report's own status against the anchored status_order (PNDG, SBMT, CMPT, with
-- CNCL terminal and later than any of them), ranked relative to order_type's own first
-- lifecycle event -- PNDG for a limit order (TLB, TLS), SBMT for a market order (TMB, TMS)
-- sent straight to market and so never pending. Held cases leave first_seen_late NULL, with no
-- rank arithmetic reaching them: a market order whose first-encountered report is PNDG
-- (L1.hole.market-order-seen-pending; reported by inv.trade_market_order_seen_pending_held). A
-- trade whose earliest report is held has no row at all (excluded below via
-- earliest_report_held), so first_seen_late is never computed against a held first report here.
first_report AS (
  SELECT
    c.trade_number,
    c.owning_account_number,
    c.order_type,
    COALESCE(h.placed_at, c.placed_at) AS placed_at,
    COALESCE(h.status_at_first_report, c.status_at_first_report) AS status_at_first_report
  FROM first_cdc_report AS c
  LEFT JOIN first_history_report AS h ON h.trade_number = c.trade_number
),
first_seen_late_computed AS (
  SELECT
    trade_number,
    owning_account_number,
    order_type,
    placed_at,
    CASE
      WHEN order_type IN ('TMB', 'TMS') AND status_at_first_report = 'PNDG' THEN NULL
      ELSE
        (CASE status_at_first_report
           WHEN 'PNDG' THEN 0
           WHEN 'SBMT' THEN 1
           WHEN 'CMPT' THEN 2
           WHEN 'CNCL' THEN 3
         END)
        >
        (CASE order_type
           WHEN 'TLB' THEN 0
           WHEN 'TLS' THEN 0
           WHEN 'TMB' THEN 1
           WHEN 'TMS' THEN 1
         END)
    END AS first_seen_late
  FROM first_report
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
  FROM first_seen_late_computed AS f
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
  FROM first_seen_late_computed AS f
  JOIN account_asof AS aa ON aa.trade_number = f.trade_number
  JOIN governed.customer AS c
    ON c.customer_number = aa.owning_customer_number
   AND c.effective_from <= f.placed_at
  QUALIFY ROW_NUMBER() OVER (PARTITION BY f.trade_number ORDER BY c.effective_from DESC) = 1
),
-- mutable outcome facts: selector latest_change from the latest I- or U-flagged report all of
-- whose coded fields (cdc_flag, t_st_id, t_tt_id) are anchored (handoff.raw.trade_cdc.t_st_id/
-- t_trade_price/t_chrg/t_comm/t_tax/t_qty -> logical.trade.status/executed_price/fees/
-- commission/tax/quantity). A D-flagged report is not a later report under
-- inv.trade_outcome_updates_in_place, so it is excluded here; a report held under
-- L1.unknown-codes is likewise not a later report -- it is held as a whole, so the outcome
-- stands as last derived from the latest anchored report, falling back as far as the
-- first-encountered report if every later report is held.
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
    AND t_st_id IS NOT NULL AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
    AND t_tt_id IS NOT NULL AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
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
  f.order_type,
  m.status,
  m.executed_price,
  m.fees,
  m.commission,
  m.tax,
  m.quantity
FROM first_seen_late_computed AS f
JOIN account_asof AS aa ON aa.trade_number = f.trade_number
JOIN customer_asof AS ca ON ca.trade_number = f.trade_number
JOIN latest_change AS m ON m.trade_number = f.trade_number
LEFT JOIN earliest_report_held AS held ON held.trade_number = f.trade_number
WHERE held.trade_number IS NULL;
