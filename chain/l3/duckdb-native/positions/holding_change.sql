-- logical.holding_change: incremental_by_identity entity, one row per
-- (original_trade_number, current_trade_number) pair. Source: raw.holding_history
-- (Batch1 historical rows carry no cdc columns at all -- cdc_flag and cdc_dsn
-- are both NULL, unlike raw.trade_cdc, where the loader normalizes Batch1 to
-- I/0 -- and Batch2+ change records). Upstream: governed.trade
-- (trade-lifecycle, this target), consumed only through the named handoffs for
-- owning_account_number, owning_account_effective_from, owning_customer_number,
-- and owning_customer_effective_from. L1.holdings-follow-trade forbids resolving
-- a holding's owner against the account or customer directly, so this SQL never
-- joins governed.account or governed.customer.
--
-- derived_from:
--   logical.holding_change,
--   logical.holding_change.original_trade_number, logical.holding_change.current_trade_number,
--   logical.holding_change.owning_account_number, logical.holding_change.owning_account_effective_from,
--   logical.holding_change.owning_customer_number, logical.holding_change.owning_customer_effective_from,
--   logical.holding_change.before_qty, logical.holding_change.after_qty, logical.holding_change.quantity_change,
--   type.trade_reference, type.holding_owning_account_reference, type.holding_owning_account_effective_from,
--   type.holding_owning_customer_reference, type.holding_owning_customer_effective_from,
--   type.holding_quantity, type.holding_quantity_change,
--   handoff.raw.holding_history.hh_h_t_id->logical.holding_change.original_trade_number,
--   handoff.raw.holding_history.hh_t_id->logical.holding_change.current_trade_number,
--   handoff.raw.holding_history.hh_before_qty->logical.holding_change.before_qty,
--   handoff.raw.holding_history.hh_after_qty->logical.holding_change.after_qty,
--   handoff.logical.trade.owning_account_number->logical.holding_change.owning_account_number,
--   handoff.logical.trade.owning_account_effective_from->logical.holding_change.owning_account_effective_from,
--   handoff.logical.trade.owning_customer_number->logical.holding_change.owning_customer_number,
--   handoff.logical.trade.owning_customer_effective_from->logical.holding_change.owning_customer_effective_from
--
-- reads: raw.holding_history, governed.trade
--
-- Strategy: strategy_for_incremental_by_identity (native MERGE INTO). Create
-- governed.holding_change if absent; MERGE a computed source over the whole
-- feed; WHEN MATCHED UPDATE SET touches only the three mutable quantity
-- columns (before_qty, after_qty, quantity_change); the four frozen ownership
-- columns are written only on INSERT, copied from governed.trade for the
-- current trade. The CREATE TABLE deliberately carries no NOT NULL: a column
-- constraint would abort the MERGE before any audit runs, turning a
-- reportable violation into a load failure and deciding, in the schema, a
-- disposition the model reserves for review (trade-lifecycle's own review
-- made the same correction). inv.holding_change_ownership_present and
-- inv.holding_quantities_present are the mechanism that makes non-null
-- presence checkable instead.
--
-- Exclusion rule (inv.holding_change_ownership_present, sg.holding-attribution's
-- coverage_claim): the model excludes a holding change whose current trade's
-- ownership pin does not resolve, not merely a change whose current trade row
-- is absent -- those are different sets, since trade.sql LEFT JOINs both pins
-- and so governed.trade can hold a row with a null owning_account_effective_from,
-- owning_customer_number, or owning_customer_effective_from. This SQL LEFT
-- JOINs governed.trade and then filters to keep a report only when all four
-- copied ownership values are non-null, which correctly excludes both cases
-- (no trade row at all, and a trade row with an unresolved pin) without
-- conflating them. An hh_t_id with no trade row at all is a distinct,
-- non-hole-bounded case the model names a review trigger on; it is excluded
-- from this entity the same way here, but now fires through
-- audits/inv.holding_change_current_trade_known.sql instead of vanishing
-- silently (cycle-1 review-1.md finding 2).
--
-- selector latest_change (report_order descending, per
-- inv.holding_quantity_updates_in_place; D rows excluded, provisional pending
-- L1.hole.deletions): before_qty <- hh_before_qty, after_qty <- hh_after_qty
-- from the pair's latest non-deleted raw.holding_history report. Per
-- sources-v1.json, Batch1 HoldingHistory rows carry no cdc columns at all
-- (cdc_flag and cdc_dsn are both NULL, unlike raw.trade_cdc, where the loader
-- normalizes Batch1 to I/0); report_order's applies_to states these historical
-- rows precede all incremental rows regardless of batch_date/cdc_dsn. A
-- cdc_flag IS NULL row is therefore a valid (historical) report, ranked
-- earliest, never excluded the way a D-flagged row is.
-- owning_account_number, owning_account_effective_from, owning_customer_number,
-- owning_customer_effective_from: copied directly from governed.trade's current
-- row for current_trade_number. Because trade-lifecycle's own owning_* columns
-- are themselves frozen_from_first_encounter and never updated after the
-- trade's own first encounter, this copy is safe to read at any cycle and is
-- never re-written once this pair is first inserted (selector first_encounter_only
-- at the holding-change level is enforced by the MERGE's WHEN MATCHED clause
-- leaving these four columns untouched, not by a window function here).
-- quantity_change (computed_within_entity): after_qty minus before_qty, this
-- row's own two attributes; recomputed on every cycle since it is mutable.

CREATE TABLE IF NOT EXISTS governed.holding_change (
    original_trade_number BIGINT,
    current_trade_number BIGINT,
    owning_account_number BIGINT,
    owning_account_effective_from TIMESTAMP,
    owning_customer_number BIGINT,
    owning_customer_effective_from TIMESTAMP,
    before_qty BIGINT,
    after_qty BIGINT,
    quantity_change BIGINT
);

MERGE INTO governed.holding_change AS tgt
USING (
    WITH latest_report AS (
        SELECT hh_h_t_id, hh_t_id, hh_before_qty, hh_after_qty
        FROM raw.holding_history
        WHERE cdc_flag IS NULL OR cdc_flag IN ('I', 'U')
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY hh_h_t_id, hh_t_id
            ORDER BY (cdc_flag IS NULL) ASC, batch_date DESC, cdc_dsn DESC
        ) = 1
    )
    SELECT
        lr.hh_h_t_id AS original_trade_number,
        lr.hh_t_id AS current_trade_number,
        t.owning_account_number,
        t.owning_account_effective_from,
        t.owning_customer_number,
        t.owning_customer_effective_from,
        lr.hh_before_qty AS before_qty,
        lr.hh_after_qty AS after_qty,
        (lr.hh_after_qty - lr.hh_before_qty) AS quantity_change
    FROM latest_report lr
    LEFT JOIN governed.trade t ON t.trade_number = lr.hh_t_id
    WHERE t.owning_account_number IS NOT NULL
      AND t.owning_account_effective_from IS NOT NULL
      AND t.owning_customer_number IS NOT NULL
      AND t.owning_customer_effective_from IS NOT NULL
) AS src
ON tgt.original_trade_number = src.original_trade_number
   AND tgt.current_trade_number = src.current_trade_number
WHEN MATCHED THEN UPDATE SET
    before_qty = src.before_qty,
    after_qty = src.after_qty,
    quantity_change = src.quantity_change
WHEN NOT MATCHED THEN INSERT (
    original_trade_number, current_trade_number,
    owning_account_number, owning_account_effective_from,
    owning_customer_number, owning_customer_effective_from,
    before_qty, after_qty, quantity_change
) VALUES (
    src.original_trade_number, src.current_trade_number,
    src.owning_account_number, src.owning_account_effective_from,
    src.owning_customer_number, src.owning_customer_effective_from,
    src.before_qty, src.after_qty, src.quantity_change
);
