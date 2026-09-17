-- logical.trade: incremental_by_identity entity, one row per trade_number.
-- Sources: raw.trade_cdc (Batch1 initial encounters, cdc_flag I, cdc_dsn 0;
-- and Batch2+ change records) and raw.trade_history (per-status rows for
-- historical-load trades: th_t_id, th_dts, th_st_id, batch_date; no cdc
-- columns, no account field). Upstream: governed.account and governed.customer
-- (ownership-history, this target), consumed only through the named handoffs.
--
-- derived_from:
--   logical.trade,
--   logical.trade.trade_number, logical.trade.owning_account_number, logical.trade.placed_at,
--   logical.trade.owning_account_effective_from, logical.trade.owning_customer_number,
--   logical.trade.owning_customer_effective_from, logical.trade.first_seen_late,
--   logical.trade.order_type, logical.trade.status, logical.trade.executed_price,
--   logical.trade.fees, logical.trade.commission, logical.trade.tax, logical.trade.quantity,
--   type.trade_number, type.trade_owning_account_reference, type.trade_placed_at,
--   type.trade_owning_account_effective_from, type.trade_owning_customer_reference,
--   type.trade_owning_customer_effective_from, type.trade_first_seen_late,
--   type.trade_order_type, type.trade_status, type.trade_executed_price, type.trade_fees,
--   type.trade_commission, type.trade_tax, type.trade_quantity,
--   handoff.raw.trade_cdc.t_id->logical.trade.trade_number,
--   handoff.raw.trade_cdc.t_ca_id->logical.trade.owning_account_number,
--   handoff.raw.trade_cdc.t_dts->logical.trade.placed_at,
--   handoff.raw.trade_history.th_dts->logical.trade.placed_at,
--   handoff.logical.account.effective_from->logical.trade.owning_account_effective_from,
--   handoff.logical.account.owning_customer_number->logical.trade.owning_customer_number,
--   handoff.logical.customer.effective_from->logical.trade.owning_customer_effective_from,
--   handoff.raw.trade_cdc.t_tt_id->logical.trade.order_type,
--   handoff.raw.trade_cdc.t_st_id->logical.trade.status,
--   handoff.raw.trade_cdc.t_trade_price->logical.trade.executed_price,
--   handoff.raw.trade_cdc.t_chrg->logical.trade.fees,
--   handoff.raw.trade_cdc.t_comm->logical.trade.commission,
--   handoff.raw.trade_cdc.t_tax->logical.trade.tax,
--   handoff.raw.trade_cdc.t_qty->logical.trade.quantity
--
-- reads: raw.trade_cdc, raw.trade_history, governed.account, governed.customer
--
-- Strategy: strategy_for_incremental_by_identity (native MERGE INTO). Create
-- governed.trade if absent; MERGE a computed source over the whole feed;
-- WHEN MATCHED UPDATE SET touches only the six mutable outcome columns; the
-- seven frozen columns (owning_account_number, placed_at,
-- owning_account_effective_from, owning_customer_number,
-- owning_customer_effective_from, first_seen_late, order_type) are written
-- only on INSERT, from the trade's first-encountered report.
--
-- L1.unknown-codes (this cycle, held at the report level): a raw.trade_cdc
-- row carrying any code outside its anchored vocabulary in any of
-- cdc_flag, t_st_id, t_tt_id is held in its entirety -- nothing is derived
-- from it, for any fact, not only the fact tied to the specific bad field.
-- Such rows are excluded from every CTE below via valid_cdc_rows, which
-- requires cdc_flag, t_st_id, and t_tt_id to all be anchored. Since
-- owning_account_number, order_type, and (via first_cdc_report) placed_at
-- are all sourced from a trade's earliest valid_cdc_rows row, a trade whose
-- only raw.trade_cdc report is held has no first_cdc_report row and
-- therefore no source row at all here -- even when a raw.trade_history
-- report for the same trade is itself anchored: identity and placement
-- both rest on raw.trade_cdc (trade_history carries no account or
-- order-type field and, per the anchors, a historical-load trade always
-- has a matching, anchored Batch1 trade_cdc row of its own; a trade whose
-- only trade_cdc report is held is known only through a held report and is
-- not yet known to this job). inv.every_received_trade_persisted does not
-- claim such a trade; inv.unknown_codes_held reports the held record(s)
-- instead.
--
-- selector first_encounter_only, across both anchored report sources
-- (report_order): placed_at <- the earliest raw.trade_history row's th_dts
-- when any exist for the trade (history precedes all raw.trade_cdc rows),
-- else the earliest valid_cdc_rows row's t_dts. owning_account_number <-
-- t_ca_id from the trade's earliest valid_cdc_rows row specifically
-- (raw.trade_history carries no account field, regardless of which source
-- supplies placed_at). order_type <- t_tt_id from that same earliest
-- valid_cdc_rows row when it is one of {TLB, TLS, TMB, TMS}, else no
-- order_type fact is derived (null): nothing is defaulted or inferred.
-- selector as_of_event_time: owning_account_effective_from <- the
-- governed.account statement of owning_account_number whose effective_from is
-- latest at or before placed_at.
-- selector same_statement_as_owning_account_reference: owning_customer_number
-- <- owning_customer_number on that exact same governed.account statement.
-- selector as_of_event_time: owning_customer_effective_from <- the
-- governed.customer statement of owning_customer_number whose effective_from
-- is latest at or before placed_at.
-- first_seen_late (computed_within_entity, L1.placement-moment amended,
-- L1.hole.market-order-seen-pending): null when the first-encountered
-- report is held under L1.unknown-codes (order_type not derived, or the
-- first_status drawn the same way as placed_at is outside the anchored
-- status vocabulary) or when order_type is a market order (TMB, TMS) and
-- that first_status is PNDG (the hole's own case, held for review, not
-- decided). No rank arithmetic reaches either held case. Otherwise: true
-- when first_status is later, in trade_code_meanings.status_order (PNDG,
-- SBMT, CMPT, with terminal CNCL treated as later than any of them), than
-- order_type's first lifecycle event -- PNDG for a limit order (TLB, TLS),
-- SBMT for a market order (TMB, TMS), since an order sent straight to
-- market has no pending stage; false when it carries exactly that event.
-- selector latest_change (report_order descending, cdc_flag I or U and
-- t_st_id anchored only, per inv.trade_outcome_updates_in_place and
-- logical.trade.status's own parallel_assumption; D rows excluded,
-- provisional pending L1.hole.deletions; a later report whose t_st_id is
-- unanchored is not a later report for this selection, so the outcome
-- stands as it last stood): status, executed_price, fees, commission, tax,
-- quantity all come from the same latest qualifying raw.trade_cdc report,
-- when one exists; otherwise all six stay null (nothing derived).

CREATE TABLE IF NOT EXISTS governed.trade (
    trade_number BIGINT,
    owning_account_number BIGINT,
    placed_at TIMESTAMP,
    owning_account_effective_from TIMESTAMP,
    owning_customer_number BIGINT,
    owning_customer_effective_from TIMESTAMP,
    first_seen_late BOOLEAN,
    order_type VARCHAR,
    status VARCHAR,
    executed_price DECIMAL(8,2),
    fees DECIMAL(10,2),
    commission DECIMAL(10,2),
    tax DECIMAL(10,2),
    quantity BIGINT
);

MERGE INTO governed.trade AS tgt
USING (
    WITH valid_cdc_rows AS (
        -- A row carrying any code outside its anchored vocabulary in any of
        -- cdc_flag, t_st_id, t_tt_id is held in its entirety: unusable for
        -- identity, ownership, order type, placement, or outcome.
        SELECT *
        FROM raw.trade_cdc
        WHERE cdc_flag IN ('I', 'U', 'D')
          AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
          AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
    ),
    first_cdc_report AS (
        SELECT t_id, t_dts, t_ca_id, t_st_id, t_tt_id
        FROM valid_cdc_rows
        QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
    ),
    first_history_report AS (
        SELECT th_t_id, th_dts, th_st_id
        FROM raw.trade_history
        QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts) = 1
    ),
    -- The trade's earliest held report, across both anchored sources: its
    -- earliest raw.trade_history row when one exists (history precedes every
    -- raw.trade_cdc row, per report_order), else its earliest valid_cdc_rows
    -- row. A trade with no first_cdc_report row at all (its only raw.trade_cdc
    -- reports are held) never reaches this CTE, regardless of whether a
    -- raw.trade_history report exists for it. owning_account_number and
    -- order_type always come from the earliest valid_cdc_rows row
    -- specifically (already anchored by construction), since raw.trade_history
    -- carries no account or order-type field.
    first_report AS (
        SELECT
            fc.t_id AS trade_number,
            COALESCE(fh.th_dts, fc.t_dts) AS placed_at,
            fc.t_ca_id AS owning_account_number,
            fc.t_tt_id AS order_type,
            COALESCE(fh.th_st_id, fc.t_st_id) AS first_status
        FROM first_cdc_report fc
        LEFT JOIN first_history_report fh ON fh.th_t_id = fc.t_id
    ),
    latest_outcome AS (
        SELECT t_id, t_st_id, t_trade_price, t_chrg, t_comm, t_tax, t_qty
        FROM raw.trade_cdc
        WHERE cdc_flag IN ('I', 'U')
          AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
        QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date DESC, cdc_dsn DESC) = 1
    ),
    owning_account_pin AS (
        SELECT
            fr.trade_number,
            acct.effective_from AS owning_account_effective_from,
            acct.owning_customer_number AS owning_customer_number
        FROM first_report fr
        LEFT JOIN governed.account acct
          ON acct.account_number = fr.owning_account_number
         AND acct.effective_from <= fr.placed_at
        QUALIFY ROW_NUMBER() OVER (PARTITION BY fr.trade_number ORDER BY acct.effective_from DESC NULLS LAST) = 1
    ),
    owning_customer_pin AS (
        SELECT
            fr.trade_number,
            cust.effective_from AS owning_customer_effective_from
        FROM first_report fr
        JOIN owning_account_pin ap ON ap.trade_number = fr.trade_number
        LEFT JOIN governed.customer cust
          ON cust.customer_number = ap.owning_customer_number
         AND cust.effective_from <= fr.placed_at
        QUALIFY ROW_NUMBER() OVER (PARTITION BY fr.trade_number ORDER BY cust.effective_from DESC NULLS LAST) = 1
    )
    SELECT
        fr.trade_number,
        fr.owning_account_number,
        fr.placed_at,
        ap.owning_account_effective_from,
        ap.owning_customer_number,
        cp.owning_customer_effective_from,
        CASE
            -- Held: no order_type fact, or the first-encountered report's
            -- own status is outside the anchored vocabulary.
            WHEN fr.order_type IS NULL THEN NULL
            WHEN fr.first_status NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL') THEN NULL
            -- L1.hole.market-order-seen-pending: a market order whose
            -- first-encountered report is PNDG is held for review, not
            -- decided either way.
            WHEN fr.order_type IN ('TMB', 'TMS') AND fr.first_status = 'PNDG' THEN NULL
            ELSE (
                CASE fr.first_status
                    WHEN 'PNDG' THEN 0 WHEN 'SBMT' THEN 1 WHEN 'CMPT' THEN 2 WHEN 'CNCL' THEN 3
                END
                >
                CASE fr.order_type
                    WHEN 'TLB' THEN 0 WHEN 'TLS' THEN 0
                    WHEN 'TMB' THEN 1 WHEN 'TMS' THEN 1
                END
            )
        END AS first_seen_late,
        fr.order_type,
        lo.t_st_id AS status,
        lo.t_trade_price AS executed_price,
        lo.t_chrg AS fees,
        lo.t_comm AS commission,
        lo.t_tax AS tax,
        lo.t_qty AS quantity
    FROM first_report fr
    LEFT JOIN latest_outcome lo ON lo.t_id = fr.trade_number
    LEFT JOIN owning_account_pin ap ON ap.trade_number = fr.trade_number
    LEFT JOIN owning_customer_pin cp ON cp.trade_number = fr.trade_number
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
    owning_customer_number, owning_customer_effective_from, first_seen_late,
    order_type, status, executed_price, fees, commission, tax, quantity
) VALUES (
    src.trade_number, src.owning_account_number, src.placed_at, src.owning_account_effective_from,
    src.owning_customer_number, src.owning_customer_effective_from, src.first_seen_late,
    src.order_type, src.status, src.executed_price, src.fees, src.commission, src.tax, src.quantity
);
