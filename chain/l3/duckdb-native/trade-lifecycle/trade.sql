-- logical.trade: incremental_by_identity entity, one row per trade_number.
-- Source: raw.trade_cdc (Batch1 initial encounters, cdc_flag I, cdc_dsn 0; and
-- Batch2+ change records). Upstream: governed.account (ownership-history, this
-- target), consumed only through the two named handoffs on effective_from and
-- owning_customer_number.
--
-- derived_from:
--   logical.trade,
--   logical.trade.trade_number, logical.trade.owning_account_number, logical.trade.placed_at,
--   logical.trade.owning_account_effective_from, logical.trade.owning_customer_number,
--   logical.trade.first_seen_late, logical.trade.status, logical.trade.executed_price,
--   logical.trade.fees, logical.trade.commission, logical.trade.tax, logical.trade.quantity,
--   type.trade_number, type.trade_owning_account_reference, type.trade_placed_at,
--   type.trade_owning_account_effective_from, type.trade_owning_customer_reference,
--   type.trade_first_seen_late, type.trade_status, type.trade_executed_price,
--   type.trade_fees, type.trade_commission, type.trade_tax, type.trade_quantity,
--   handoff.raw.trade_cdc.t_id->logical.trade.trade_number,
--   handoff.raw.trade_cdc.t_ca_id->logical.trade.owning_account_number,
--   handoff.raw.trade_cdc.t_dts->logical.trade.placed_at,
--   handoff.logical.account.effective_from->logical.trade.owning_account_effective_from,
--   handoff.logical.account.owning_customer_number->logical.trade.owning_customer_number,
--   handoff.raw.trade_cdc.t_st_id->logical.trade.status,
--   handoff.raw.trade_cdc.t_trade_price->logical.trade.executed_price,
--   handoff.raw.trade_cdc.t_chrg->logical.trade.fees,
--   handoff.raw.trade_cdc.t_comm->logical.trade.commission,
--   handoff.raw.trade_cdc.t_tax->logical.trade.tax,
--   handoff.raw.trade_cdc.t_qty->logical.trade.quantity
--
-- reads: raw.trade_cdc, governed.account
--
-- Strategy: strategy_for_incremental_by_identity (native MERGE INTO). Create
-- governed.trade if absent; MERGE a computed source over the whole feed;
-- WHEN MATCHED UPDATE SET touches only the six mutable outcome columns; the
-- five frozen columns (owning_account_number, placed_at,
-- owning_account_effective_from, owning_customer_number, first_seen_late) are
-- written only on INSERT, from the trade's first-encountered report.
--
-- selector first_encounter_only (report_order = batch_date, cdc_dsn ascending):
-- owning_account_number <- t_ca_id, placed_at <- t_dts, both from the trade's
-- earliest report.
-- selector as_of_event_time: owning_account_effective_from <- the governed.account
-- statement of owning_account_number whose effective_from is latest at or
-- before placed_at.
-- selector same_statement_as_owning_account_reference: owning_customer_number
-- <- owning_customer_number on that exact same governed.account statement
-- (same account_number, same effective_from), never a fresh as-of lookup.
-- first_seen_late (computed_within_entity): true when the first-encountered
-- report's t_st_id is not PNDG (trade_code_meanings.status_order's first
-- status), false when it is PNDG.
-- selector latest_change (report_order descending, cdc_flag I or U only, per
-- inv.trade_outcome_updates_in_place; D rows excluded, provisional pending
-- L1.hole.deletions): status, executed_price, fees, commission, tax, quantity
-- all come from the same latest I/U report.

CREATE TABLE IF NOT EXISTS governed.trade (
    trade_number BIGINT,
    owning_account_number BIGINT,
    placed_at TIMESTAMP,
    owning_account_effective_from TIMESTAMP,
    owning_customer_number BIGINT,
    first_seen_late BOOLEAN,
    status VARCHAR,
    executed_price DECIMAL(8,2),
    fees DECIMAL(10,2),
    commission DECIMAL(10,2),
    tax DECIMAL(10,2),
    quantity BIGINT
);

MERGE INTO governed.trade AS tgt
USING (
    WITH first_report AS (
        SELECT t_id, t_dts, t_ca_id, t_st_id
        FROM raw.trade_cdc
        QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
    ),
    latest_outcome AS (
        SELECT t_id, t_st_id, t_trade_price, t_chrg, t_comm, t_tax, t_qty
        FROM raw.trade_cdc
        WHERE cdc_flag IN ('I', 'U')
        QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date DESC, cdc_dsn DESC) = 1
    ),
    owning_account_pin AS (
        SELECT
            fr.t_id AS trade_number,
            acct.effective_from AS owning_account_effective_from,
            acct.owning_customer_number AS owning_customer_number
        FROM first_report fr
        LEFT JOIN governed.account acct
          ON acct.account_number = fr.t_ca_id
         AND acct.effective_from <= fr.t_dts
        QUALIFY ROW_NUMBER() OVER (PARTITION BY fr.t_id ORDER BY acct.effective_from DESC NULLS LAST) = 1
    )
    SELECT
        fr.t_id AS trade_number,
        fr.t_ca_id AS owning_account_number,
        fr.t_dts AS placed_at,
        pin.owning_account_effective_from,
        pin.owning_customer_number,
        (fr.t_st_id <> 'PNDG') AS first_seen_late,
        lo.t_st_id AS status,
        lo.t_trade_price AS executed_price,
        lo.t_chrg AS fees,
        lo.t_comm AS commission,
        lo.t_tax AS tax,
        lo.t_qty AS quantity
    FROM first_report fr
    JOIN latest_outcome lo ON lo.t_id = fr.t_id
    LEFT JOIN owning_account_pin pin ON pin.trade_number = fr.t_id
) AS src
ON tgt.trade_number = src.trade_number
WHEN MATCHED THEN UPDATE SET
    status = src.status,
    executed_price = src.executed_price,
    fees = src.fees,
    commission = src.commission,
    tax = src.tax,
    quantity = src.quantity
WHEN NOT MATCHED THEN INSERT (
    trade_number, owning_account_number, placed_at, owning_account_effective_from,
    owning_customer_number, first_seen_late, status, executed_price, fees, commission, tax, quantity
) VALUES (
    src.trade_number, src.owning_account_number, src.placed_at, src.owning_account_effective_from,
    src.owning_customer_number, src.first_seen_late, src.status, src.executed_price, src.fees,
    src.commission, src.tax, src.quantity
);
